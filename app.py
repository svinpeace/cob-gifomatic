"""Flask application for Video to GIF Splitter."""

import os
import uuid
import threading
import queue
import hashlib
import json
import re
import time
import secrets
from functools import wraps
from flask import Flask, render_template, request, jsonify, Response, send_from_directory, abort

from config import config
from video_processor import process_video, merge_gifs_grid

app = Flask(__name__)

# =============================================================================
# CONFIGURATION - All settings loaded from config.py / environment variables
# See .env.example for all available options
# =============================================================================

# Security Configuration
app.config['SECRET_KEY'] = config.SECRET_KEY or secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH'] = config.MAX_UPLOAD_SIZE

# Rate Limiting
RATE_LIMIT_WINDOW = config.RATE_LIMIT_WINDOW
RATE_LIMIT_MAX_REQUESTS = config.RATE_LIMIT_MAX_REQUESTS
RATE_LIMIT_MAX_UPLOADS = config.RATE_LIMIT_MAX_UPLOADS
rate_limit_store = {}  # IP -> {'count': int, 'upload_count': int, 'reset_time': float}
rate_limit_lock = threading.Lock()


def log(message):
    """Print log message with flush for real-time output."""
    print(f"[App] {message}", flush=True)


# Directories and file settings
UPLOAD_FOLDER = config.UPLOAD_FOLDER
OUTPUT_FOLDER = config.OUTPUT_FOLDER
CACHE_FILE = config.CACHE_FILE
ALLOWED_EXTENSIONS = config.ALLOWED_EXTENSIONS

# Video file magic bytes signatures
VIDEO_SIGNATURES = {
    b'\x00\x00\x00\x1c\x66\x74\x79\x70': 'mp4',  # MP4 ftyp
    b'\x00\x00\x00\x20\x66\x74\x79\x70': 'mp4',  # MP4 ftyp variant
    b'\x00\x00\x00\x18\x66\x74\x79\x70': 'mp4',  # MP4 ftyp variant
    b'\x00\x00\x00\x14\x66\x74\x79\x70': 'mp4',  # MP4 ftyp variant
    b'\x52\x49\x46\x46': 'avi',  # AVI RIFF
    b'\x00\x00\x00\x14\x66\x74\x79\x70\x71\x74': 'mov',  # MOV
    b'\x1a\x45\xdf\xa3': 'mkv',  # MKV/WebM EBML
    b'\x46\x4c\x56\x01': 'flv',  # FLV
    b'\x30\x26\xb2\x75': 'wmv',  # WMV/ASF
}

# Job Management
MAX_CONCURRENT_JOBS = config.MAX_CONCURRENT_JOBS
JOB_EXPIRY_HOURS = config.JOB_EXPIRY_HOURS
MAX_JOBS_STORED = config.MAX_JOBS_STORED

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Store SSE queues for each job with thread safety
job_queues = {}
job_gifs = {}
job_video_paths = {}  # job_id -> video file path (kept for reprocessing)
video_cache = {}
active_jobs = set()  # Track currently processing jobs
cancelled_jobs = set()  # Track jobs that have been cancelled
cache_lock = threading.Lock()
jobs_lock = threading.Lock()


def load_cache():
    """Load cache from disk with error handling."""
    global video_cache
    with cache_lock:
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    video_cache = json.load(f)
                log(f"Loaded cache with {len(video_cache)} entries")
            except (json.JSONDecodeError, IOError) as e:
                log(f"Failed to load cache: {e}")
                video_cache = {}


def save_cache():
    """Save cache to disk atomically."""
    with cache_lock:
        try:
            # Write to temp file first, then rename (atomic on most systems)
            temp_file = CACHE_FILE + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(video_cache, f)
            # Atomic rename
            if os.path.exists(CACHE_FILE):
                os.replace(temp_file, CACHE_FILE)
            else:
                os.rename(temp_file, CACHE_FILE)
        except (IOError, OSError) as e:
            log(f"Failed to save cache: {e}")
            # Clean up temp file if it exists
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass


def compute_file_hash(file_stream):
    """Compute SHA-256 hash of file (first 10MB for speed)."""
    hasher = hashlib.sha256()
    chunk_size = 1024 * 1024  # 1MB
    max_bytes = 10 * 1024 * 1024  # 10MB
    bytes_read = 0

    while bytes_read < max_bytes:
        chunk = file_stream.read(chunk_size)
        if not chunk:
            break
        hasher.update(chunk)
        bytes_read += len(chunk)

    # Reset file stream for later use
    file_stream.seek(0)
    return hasher.hexdigest()


def is_valid_uuid(value):
    """Check if value is a valid UUID."""
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, AttributeError):
        return False


def is_safe_filename(filename):
    """Check if filename is safe (no path traversal)."""
    if not filename:
        return False
    # Check for path separators and traversal patterns
    if any(c in filename for c in ['/', '\\', '\x00']):
        return False
    if '..' in filename:
        return False
    # Must be a valid filename pattern
    if not re.match(r'^[a-zA-Z0-9_\-]+\.(gif|GIF)$', filename):
        return False
    return True


def sanitize_error_message(error):
    """Sanitize error message to avoid information disclosure."""
    error_str = str(error)
    # Remove file paths
    error_str = re.sub(r'[A-Za-z]:\\[^\s]+', '[path]', error_str)
    error_str = re.sub(r'/[^\s]+', '[path]', error_str)
    # Truncate long messages
    if len(error_str) > 200:
        error_str = error_str[:200] + '...'
    return error_str


def validate_video_magic_bytes(file_stream):
    """Validate file by checking magic bytes."""
    file_stream.seek(0)
    header = file_stream.read(16)
    file_stream.seek(0)

    if len(header) < 4:
        return False

    # Check against known video signatures
    for signature in VIDEO_SIGNATURES.keys():
        sig_len = len(signature)
        if header[:sig_len] == signature:
            return True

    # Additional check for MP4/MOV (ftyp can be at different offsets)
    if b'ftyp' in header:
        return True

    return False


def get_cached_gifs(job_id):
    """Get list of GIFs from cached job output folder."""
    if not is_valid_uuid(job_id):
        return None, None

    job_dir = os.path.join(OUTPUT_FOLDER, job_id)

    # Ensure we're not escaping the output folder
    job_dir = os.path.abspath(job_dir)
    output_dir = os.path.abspath(OUTPUT_FOLDER)
    if not job_dir.startswith(output_dir):
        return None, None

    if not os.path.exists(job_dir):
        return None, None

    original_gifs = []
    merged_gifs = []

    try:
        for filename in sorted(os.listdir(job_dir)):
            if filename.endswith('.gif') and is_safe_filename(filename):
                gif_path = os.path.join(job_dir, filename)
                gif_data = {
                    'path': gif_path,
                    'url': f"/output/{job_id}/{filename}",
                    'filename': filename
                }
                if filename.startswith('clip_'):
                    original_gifs.append(gif_data)
                elif filename.startswith('merged_'):
                    merged_gifs.append(gif_data)
    except OSError as e:
        log(f"Error reading job directory: {sanitize_error_message(e)}")
        return None, None

    return original_gifs if original_gifs else None, merged_gifs


def cleanup_old_jobs():
    """Remove jobs older than JOB_EXPIRY_HOURS. Set to 0 to disable cleanup."""
    # Skip cleanup if disabled
    if JOB_EXPIRY_HOURS <= 0:
        log("Job cleanup disabled (JOB_EXPIRY_HOURS = 0)")
        return

    try:
        current_time = time.time()
        expiry_seconds = JOB_EXPIRY_HOURS * 3600

        if not os.path.exists(OUTPUT_FOLDER):
            return

        for job_id in os.listdir(OUTPUT_FOLDER):
            if not is_valid_uuid(job_id):
                continue

            job_dir = os.path.join(OUTPUT_FOLDER, job_id)
            if not os.path.isdir(job_dir):
                continue

            # Check directory modification time
            try:
                mtime = os.path.getmtime(job_dir)
                if current_time - mtime > expiry_seconds:
                    # Remove old job
                    import shutil
                    shutil.rmtree(job_dir, ignore_errors=True)
                    log(f"Cleaned up expired job: {job_id}")

                    # Remove from cache
                    with cache_lock:
                        keys_to_remove = [k for k, v in video_cache.items() if v == job_id]
                        for key in keys_to_remove:
                            del video_cache[key]
                    save_cache()
            except OSError:
                continue
    except Exception as e:
        log(f"Error during cleanup: {sanitize_error_message(e)}")


def cleanup_job_resources(job_id):
    """Clean up resources for a specific job after completion."""
    with jobs_lock:
        # Remove from active jobs
        active_jobs.discard(job_id)

        # Clean up queue after a delay to ensure all messages are consumed
        def delayed_cleanup():
            time.sleep(10)  # Wait for SSE connections to close
            with jobs_lock:
                if job_id in job_queues:
                    del job_queues[job_id]

        cleanup_thread = threading.Thread(target=delayed_cleanup, daemon=True)
        cleanup_thread.start()


def check_rate_limit(ip_address, is_upload=False):
    """Check and update rate limit for an IP address."""
    current_time = time.time()

    with rate_limit_lock:
        if ip_address in rate_limit_store:
            record = rate_limit_store[ip_address]

            # Reset if window has passed
            if current_time > record['reset_time']:
                record['count'] = 0
                record['upload_count'] = 0
                record['reset_time'] = current_time + RATE_LIMIT_WINDOW

            # Check limits
            if record['count'] >= RATE_LIMIT_MAX_REQUESTS:
                return False, "Rate limit exceeded. Please wait before making more requests."

            if is_upload and record['upload_count'] >= RATE_LIMIT_MAX_UPLOADS:
                return False, "Upload limit exceeded. Please wait before uploading more videos."

            # Update counts
            record['count'] += 1
            if is_upload:
                record['upload_count'] += 1
        else:
            rate_limit_store[ip_address] = {
                'count': 1,
                'upload_count': 1 if is_upload else 0,
                'reset_time': current_time + RATE_LIMIT_WINDOW
            }

        # Clean up old entries periodically
        if len(rate_limit_store) > 10000:
            expired = [ip for ip, data in rate_limit_store.items()
                      if current_time > data['reset_time']]
            for ip in expired[:1000]:  # Remove up to 1000 expired entries
                del rate_limit_store[ip]

    return True, None


def rate_limit(upload=False):
    """Decorator for rate limiting routes."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr or '127.0.0.1'
            allowed, message = check_rate_limit(ip, is_upload=upload)
            if not allowed:
                return jsonify({'error': message}), 429
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def add_security_headers(response):
    """Add security headers to response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "frame-ancestors 'self'"
    )
    return response


@app.after_request
def after_request(response):
    """Add security headers to all responses."""
    return add_security_headers(response)


# Load cache on startup
load_cache()

# Run cleanup on startup
cleanup_thread = threading.Thread(target=cleanup_old_jobs, daemon=True)
cleanup_thread.start()


def allowed_file(filename):
    """Check if file extension is allowed."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/guide')
def guide():
    """Serve the user guide page."""
    return render_template('guide.html')


@app.route('/upload', methods=['POST'])
@rate_limit(upload=True)
def upload_video():
    """Handle video upload and start processing."""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400

    file = request.files['video']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Allowed: MP4, AVI, MOV, MKV, WebM, FLV, WMV'}), 400

    # Validate magic bytes
    if not validate_video_magic_bytes(file.stream):
        return jsonify({'error': 'Invalid video file format'}), 400

    # Check concurrent job limit
    with jobs_lock:
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
            return jsonify({'error': 'Server busy. Please try again later.'}), 503

    # Parse and validate settings from form data
    try:
        max_duration = float(request.form.get('max_duration', 5.0))
        fps = int(request.form.get('fps', 10))
        width = int(request.form.get('width', 480))
        threshold = int(request.form.get('threshold', 30))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid settings values'}), 400

    settings = {
        'max_duration': max(1.0, min(30.0, max_duration)),
        'fps': max(5, min(30, fps)),
        'width': max(240, min(1920, width)),
        'threshold': max(10, min(60, threshold))
    }

    log(f"Processing settings: {settings}")

    # Compute file hash to check cache (include settings in hash for different configs)
    file_hash = compute_file_hash(file.stream)
    settings_str = f"{settings['max_duration']}_{settings['fps']}_{settings['width']}_{settings['threshold']}"
    cache_key = f"{file_hash}_{settings_str}"
    log(f"Cache key: {cache_key[:16]}...")

    # Check if already processed with same settings (thread-safe)
    with cache_lock:
        cached_job_id = video_cache.get(cache_key)

    if cached_job_id and is_valid_uuid(cached_job_id):
        original_gifs, merged_gifs = get_cached_gifs(cached_job_id)

        if original_gifs:
            log(f"Cache hit! Using existing job: {cached_job_id} ({len(original_gifs)} GIFs)")

            # Save video file for potential reprocessing
            ext = file.filename.rsplit('.', 1)[1].lower()
            video_filename = f"{cached_job_id}.{ext}"
            video_path = os.path.join(UPLOAD_FOLDER, video_filename)
            try:
                file.save(video_path)
                with jobs_lock:
                    job_video_paths[cached_job_id] = video_path
                log(f"Saved video for reprocessing: {video_filename}")
            except (IOError, OSError) as e:
                log(f"Failed to save video for reprocessing: {sanitize_error_message(e)}")

            with jobs_lock:
                job_gifs[cached_job_id] = original_gifs
            return jsonify({
                'job_id': cached_job_id,
                'cached': True,
                'gifs': [{'url': g['url'], 'filename': g['filename']} for g in original_gifs],
                'merged': [{'url': g['url'], 'filename': g['filename']} for g in (merged_gifs or [])]
            })
        else:
            # Cache entry exists but GIFs are gone, remove from cache
            log(f"Cache stale, removing: {cached_job_id}")
            with cache_lock:
                if cache_key in video_cache:
                    del video_cache[cache_key]
            save_cache()

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Save the uploaded file with safe filename
    ext = file.filename.rsplit('.', 1)[1].lower()
    video_filename = f"{job_id}.{ext}"
    video_path = os.path.join(UPLOAD_FOLDER, video_filename)

    try:
        file.save(video_path)
    except (IOError, OSError) as e:
        log(f"Failed to save uploaded file: {sanitize_error_message(e)}")
        return jsonify({'error': 'Failed to save uploaded file'}), 500

    log(f"Uploaded: {file.filename} -> {video_filename}")

    # Create output directory for this job
    job_output_dir = os.path.join(OUTPUT_FOLDER, job_id)
    try:
        os.makedirs(job_output_dir, exist_ok=True)
    except OSError as e:
        log(f"Failed to create output directory: {sanitize_error_message(e)}")
        # Clean up uploaded file
        try:
            os.remove(video_path)
        except OSError:
            pass
        return jsonify({'error': 'Failed to create output directory'}), 500

    # Initialize SSE queue for this job
    with jobs_lock:
        job_queues[job_id] = queue.Queue()
        job_gifs[job_id] = []
        job_video_paths[job_id] = video_path  # Keep for reprocessing
        active_jobs.add(job_id)

    # Store in cache
    with cache_lock:
        video_cache[cache_key] = job_id

        # Limit cache size
        if len(video_cache) > MAX_JOBS_STORED:
            # Remove oldest entries (first in dict)
            keys_to_remove = list(video_cache.keys())[:len(video_cache) - MAX_JOBS_STORED]
            for key in keys_to_remove:
                del video_cache[key]

    save_cache()

    # Start processing in background thread
    thread = threading.Thread(
        target=process_video_task,
        args=(job_id, video_path, job_output_dir, settings)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'job_id': job_id})


def process_video_task(job_id, video_path, output_dir, settings=None):
    """Background task to process video and send updates via SSE."""
    with jobs_lock:
        q = job_queues.get(job_id)

    if not q:
        return

    log(f"Starting job: {job_id}")
    was_cancelled = False
    try:
        for gif_path in process_video(video_path, output_dir, settings=settings):
            # Check if job was cancelled
            with jobs_lock:
                if job_id in cancelled_jobs:
                    was_cancelled = True
                    log(f"Job cancelled: {job_id}")
                    q.put({'type': 'cancelled', 'message': 'Processing cancelled'})
                    break

            # Get relative path for serving
            gif_filename = os.path.basename(gif_path)

            # Validate filename
            if not is_safe_filename(gif_filename):
                log(f"Invalid GIF filename generated: {gif_filename}")
                continue

            gif_url = f"/output/{job_id}/{gif_filename}"

            # Store in job_gifs (thread-safe)
            with jobs_lock:
                if job_id in job_gifs:
                    job_gifs[job_id].append({
                        'path': gif_path,
                        'url': gif_url,
                        'filename': gif_filename
                    })

            # Send to SSE queue
            q.put({'type': 'gif', 'url': gif_url, 'filename': gif_filename})

        # Signal completion (only if not cancelled)
        if not was_cancelled:
            with jobs_lock:
                total = len(job_gifs.get(job_id, []))
            q.put({'type': 'complete', 'total': total})
            log(f"Job complete: {job_id} ({total} GIFs)")

    except Exception as e:
        log(f"Job error: {job_id} - {sanitize_error_message(e)}")
        q.put({'type': 'error', 'message': 'Video processing failed. Please try a different video or settings.'})

    finally:
        # Remove from cancelled set
        with jobs_lock:
            cancelled_jobs.discard(job_id)

        # Keep video file for potential reprocessing (don't delete)
        # Video will be deleted when job is explicitly deleted or on cleanup

        # Clean up job resources
        cleanup_job_resources(job_id)


@app.route('/stream/<job_id>')
@rate_limit()
def stream(job_id):
    """SSE endpoint for real-time GIF updates."""
    # Validate job_id
    if not is_valid_uuid(job_id):
        return jsonify({'error': 'Invalid job ID'}), 400

    def generate():
        with jobs_lock:
            q = job_queues.get(job_id)

        if not q:
            yield f"data: {{\"type\": \"error\", \"message\": \"Invalid or expired job ID\"}}\n\n"
            return

        while True:
            try:
                # Wait for next message with timeout
                message = q.get(timeout=60)

                # Format as SSE (safe JSON encoding)
                yield f"data: {json.dumps(message)}\n\n"

                # If complete or error, stop streaming
                if message.get('type') in ('complete', 'error'):
                    break

            except queue.Empty:
                # Send keepalive
                yield f"data: {{\"type\": \"keepalive\"}}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/merge', methods=['POST'])
@rate_limit()
def merge():
    """Merge selected GIFs into a grid."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    job_id = data.get('job_id')
    selected = data.get('selected', [])

    # Validate job_id
    if not job_id or not is_valid_uuid(job_id):
        return jsonify({'error': 'Invalid job ID'}), 400

    # Validate selected is a list
    if not isinstance(selected, list):
        return jsonify({'error': 'Invalid selection format'}), 400

    # Validate all filenames
    for filename in selected:
        if not isinstance(filename, str) or not is_safe_filename(filename):
            return jsonify({'error': 'Invalid filename in selection'}), 400

    with jobs_lock:
        if job_id not in job_gifs:
            return jsonify({'error': 'Job not found'}), 404

    if len(selected) < 2:
        return jsonify({'error': 'Select at least 2 GIFs to merge'}), 400

    if len(selected) > config.MAX_MERGE_GIFS:
        return jsonify({'error': f'Maximum {config.MAX_MERGE_GIFS} GIFs can be merged at once'}), 400

    # Get full paths for selected GIFs
    gif_paths = []
    with jobs_lock:
        for gif_info in job_gifs.get(job_id, []):
            if gif_info['filename'] in selected:
                # Verify path is within output folder
                abs_path = os.path.abspath(gif_info['path'])
                abs_output = os.path.abspath(OUTPUT_FOLDER)
                if abs_path.startswith(abs_output) and os.path.exists(abs_path):
                    gif_paths.append(gif_info['path'])

    if len(gif_paths) < 2:
        return jsonify({'error': 'Could not find selected GIFs'}), 400

    # Sort to maintain order
    gif_paths.sort()

    # Generate merged GIF with sequence prefix + random suffix for sorting
    job_dir = os.path.join(OUTPUT_FOLDER, job_id)
    existing_merged = []
    try:
        for f in os.listdir(job_dir):
            if f.startswith('merged_') and f.endswith('.gif') and '_grayscale' not in f:
                # Extract sequence number from merged_N_xxxx.gif
                try:
                    parts = f.replace('merged_', '').replace('.gif', '').split('_')
                    if parts:
                        num = int(parts[0])
                        existing_merged.append(num)
                except ValueError:
                    pass
    except OSError:
        pass

    next_num = max(existing_merged, default=0) + 1
    merge_filename = f"merged_{next_num}_{uuid.uuid4().hex[:8]}.gif"
    merge_path = os.path.join(OUTPUT_FOLDER, job_id, merge_filename)

    # Verify merge path is within output folder
    abs_merge_path = os.path.abspath(merge_path)
    abs_output = os.path.abspath(OUTPUT_FOLDER)
    if not abs_merge_path.startswith(abs_output):
        return jsonify({'error': 'Invalid merge path'}), 400

    # Determine columns (2 for up to 4, 3 for more)
    columns = 2 if len(gif_paths) <= 4 else 3

    # Get width from the first GIF's settings (use job settings if available)
    width = 480  # Default
    with jobs_lock:
        if job_id in job_gifs and job_gifs[job_id]:
            # Try to get width from the original settings
            pass  # For now use default

    success = merge_gifs_grid(gif_paths, merge_path, columns=columns, width=width)

    if success and os.path.exists(merge_path):
        merge_url = f"/output/{job_id}/{merge_filename}"
        return jsonify({'url': merge_url})
    else:
        return jsonify({'error': 'Failed to merge GIFs'}), 500


@app.route('/grayscale', methods=['POST'])
@rate_limit()
def grayscale():
    """Convert a GIF to grayscale."""
    from video_processor import convert_gif_to_grayscale

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    job_id = data.get('job_id')
    filename = data.get('filename')

    # Validate job_id
    if not job_id or not is_valid_uuid(job_id):
        return jsonify({'error': 'Invalid job ID'}), 400

    # Validate filename
    if not filename or not is_safe_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    # Build source path and verify it exists
    source_path = os.path.abspath(os.path.join(OUTPUT_FOLDER, job_id, filename))
    output_base = os.path.abspath(OUTPUT_FOLDER)

    if not source_path.startswith(output_base):
        return jsonify({'error': 'Invalid path'}), 400

    if not os.path.exists(source_path):
        return jsonify({'error': 'File not found'}), 404

    # Generate output filename
    base_name = filename.rsplit('.', 1)[0]
    grayscale_filename = f"{base_name}_grayscale.gif"
    output_path = os.path.join(OUTPUT_FOLDER, job_id, grayscale_filename)

    # Verify output path
    abs_output_path = os.path.abspath(output_path)
    if not abs_output_path.startswith(output_base):
        return jsonify({'error': 'Invalid output path'}), 400

    # Convert to grayscale
    success = convert_gif_to_grayscale(source_path, output_path)

    if success and os.path.exists(output_path):
        grayscale_url = f"/output/{job_id}/{grayscale_filename}"
        return jsonify({'url': grayscale_url, 'filename': grayscale_filename})
    else:
        return jsonify({'error': 'Grayscale conversion failed'}), 500


@app.route('/delete', methods=['POST'])
@rate_limit()
def delete_gif():
    """Delete a GIF file."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    job_id = data.get('job_id')
    filename = data.get('filename')

    # Validate job_id
    if not job_id or not is_valid_uuid(job_id):
        return jsonify({'error': 'Invalid job ID'}), 400

    # Validate filename
    if not filename or not is_safe_filename(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    # Build file path and verify it's within output folder
    file_path = os.path.abspath(os.path.join(OUTPUT_FOLDER, job_id, filename))
    output_base = os.path.abspath(OUTPUT_FOLDER)

    if not file_path.startswith(output_base):
        return jsonify({'error': 'Invalid path'}), 400

    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404

    # Delete the file
    try:
        os.remove(file_path)
        log(f"Deleted GIF: {file_path}")

        # Remove from job_gifs if present
        with jobs_lock:
            if job_id in job_gifs:
                job_gifs[job_id] = [g for g in job_gifs[job_id] if g['filename'] != filename]

        return jsonify({'success': True})
    except OSError as e:
        log(f"Failed to delete GIF: {sanitize_error_message(e)}")
        return jsonify({'error': 'Failed to delete file'}), 500


@app.route('/cancel/<job_id>', methods=['POST'])
@rate_limit()
def cancel_job(job_id):
    """Cancel a running job."""
    # Validate job_id
    if not is_valid_uuid(job_id):
        return jsonify({'error': 'Invalid job ID'}), 400

    with jobs_lock:
        if job_id not in active_jobs:
            return jsonify({'error': 'Job not active'}), 404

        # Mark job as cancelled
        cancelled_jobs.add(job_id)
        log(f"Cancelling job: {job_id}")

    return jsonify({'success': True, 'message': 'Job cancellation requested'})


@app.route('/reprocess', methods=['POST'])
@rate_limit()
def reprocess_job():
    """Reprocess a job with new settings - deletes existing GIFs first."""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    job_id = data.get('job_id')

    # Validate job_id
    if not job_id or not is_valid_uuid(job_id):
        return jsonify({'error': 'Invalid job ID'}), 400

    # Check if video file still exists
    with jobs_lock:
        video_path = job_video_paths.get(job_id)

    if not video_path or not os.path.exists(video_path):
        return jsonify({'error': 'Video file not found. Please re-upload.'}), 404

    # Check concurrent job limit
    with jobs_lock:
        if len(active_jobs) >= MAX_CONCURRENT_JOBS:
            return jsonify({'error': 'Server busy. Please try again later.'}), 503

    # Parse and validate settings from request
    try:
        max_duration = float(data.get('max_duration', 5.0))
        fps = int(data.get('fps', 10))
        width = int(data.get('width', 480))
        threshold = int(data.get('threshold', 30))
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid settings values'}), 400

    settings = {
        'max_duration': max(1.0, min(30.0, max_duration)),
        'fps': max(5, min(30, fps)),
        'width': max(240, min(1920, width)),
        'threshold': max(10, min(60, threshold))
    }

    log(f"Reprocessing job {job_id} with settings: {settings}")

    # Delete all existing GIFs in the job folder
    job_output_dir = os.path.join(OUTPUT_FOLDER, job_id)
    if os.path.exists(job_output_dir):
        try:
            for filename in os.listdir(job_output_dir):
                if filename.endswith('.gif'):
                    file_path = os.path.join(job_output_dir, filename)
                    os.remove(file_path)
                    log(f"Deleted GIF for reprocess: {filename}")
        except OSError as e:
            log(f"Error cleaning GIFs for reprocess: {sanitize_error_message(e)}")

    # Clear job_gifs for this job
    with jobs_lock:
        job_gifs[job_id] = []
        job_queues[job_id] = queue.Queue()
        active_jobs.add(job_id)

    # Start processing in background thread
    thread = threading.Thread(
        target=process_video_task,
        args=(job_id, video_path, job_output_dir, settings)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'job_id': job_id, 'message': 'Reprocessing started'})


@app.route('/output/<job_id>/<filename>')
def serve_gif(job_id, filename):
    """Serve generated GIF files."""
    # Validate job_id is a valid UUID
    if not is_valid_uuid(job_id):
        abort(404)

    # Validate filename is safe
    if not is_safe_filename(filename):
        abort(404)

    # Build path and verify it's within output folder
    directory = os.path.abspath(os.path.join(OUTPUT_FOLDER, job_id))
    output_base = os.path.abspath(OUTPUT_FOLDER)

    if not directory.startswith(output_base):
        abort(404)

    if not os.path.isdir(directory):
        abort(404)

    # Verify file exists and is within directory
    file_path = os.path.abspath(os.path.join(directory, filename))
    if not file_path.startswith(directory):
        abort(404)

    return send_from_directory(directory, filename)


@app.route('/jobs')
def list_jobs():
    """List all existing processed jobs."""
    jobs = []
    if os.path.exists(OUTPUT_FOLDER):
        try:
            for job_id in os.listdir(OUTPUT_FOLDER):
                # Validate job_id format
                if not is_valid_uuid(job_id):
                    continue

                job_dir = os.path.join(OUTPUT_FOLDER, job_id)
                if os.path.isdir(job_dir):
                    try:
                        gifs = [f for f in os.listdir(job_dir)
                               if f.endswith('.gif') and f.startswith('clip_') and is_safe_filename(f)]
                        if gifs:
                            jobs.append({
                                'job_id': job_id,
                                'gif_count': len(gifs)
                            })
                    except OSError:
                        continue

                # Limit number of jobs returned
                if len(jobs) >= 50:
                    break
        except OSError as e:
            log(f"Error listing jobs: {sanitize_error_message(e)}")

    return jsonify({'jobs': jobs})


@app.route('/load/<job_id>')
def load_job(job_id):
    """Load an existing job's GIFs."""
    # Validate job_id
    if not is_valid_uuid(job_id):
        return jsonify({'error': 'Invalid job ID'}), 400

    original_gifs, merged_gifs = get_cached_gifs(job_id)
    if original_gifs:
        with jobs_lock:
            job_gifs[job_id] = original_gifs
        log(f"Loaded existing job: {job_id} ({len(original_gifs)} GIFs)")
        return jsonify({
            'job_id': job_id,
            'gifs': [{'url': g['url'], 'filename': g['filename']} for g in original_gifs],
            'merged': [{'url': g['url'], 'filename': g['filename']} for g in (merged_gifs or [])]
        })
    return jsonify({'error': 'Job not found'}), 404


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error."""
    max_size_gb = config.MAX_UPLOAD_SIZE / (1024 * 1024 * 1024)
    return jsonify({'error': f'File too large. Maximum size is {max_size_gb:.0f}GB.'}), 413


@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Handle rate limit error."""
    return jsonify({'error': 'Too many requests. Please wait before trying again.'}), 429


@app.errorhandler(404)
def not_found(error):
    """Handle 404 error."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 error."""
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    debug_mode = config.FLASK_ENV == 'development'
    if debug_mode:
        log("WARNING: Running in debug mode. Do not use in production!")
    app.run(debug=debug_mode, threaded=True, host=config.HOST, port=config.PORT)
