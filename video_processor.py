"""Video processing module for scene detection, splitting, and GIF conversion."""

import subprocess
import os
import sys
import shutil
import re
import json
from scenedetect import open_video, SceneManager, ContentDetector

from config import config


def find_ffmpeg():
    """Find FFmpeg executable path."""
    # Try to find ffmpeg in PATH
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        return ffmpeg_path

    # Common Windows installation paths
    common_paths = [
        r'C:\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
        os.path.expanduser(r'~\ffmpeg\bin\ffmpeg.exe'),
        os.path.expanduser(r'~\scoop\shims\ffmpeg.exe'),
    ]

    for path in common_paths:
        if os.path.isfile(path):
            return path

    return None


def find_ffprobe():
    """Find FFprobe executable path."""
    # Try to find ffprobe in PATH
    ffprobe_path = shutil.which('ffprobe')
    if ffprobe_path:
        return ffprobe_path

    # Common Windows installation paths
    common_paths = [
        r'C:\ffmpeg\bin\ffprobe.exe',
        r'C:\Program Files\ffmpeg\bin\ffprobe.exe',
        r'C:\Program Files (x86)\ffmpeg\bin\ffprobe.exe',
        os.path.expanduser(r'~\ffmpeg\bin\ffprobe.exe'),
        os.path.expanduser(r'~\scoop\shims\ffprobe.exe'),
    ]

    for path in common_paths:
        if os.path.isfile(path):
            return path

    return None


# Find FFmpeg
FFMPEG_PATH = find_ffmpeg()

# Find FFprobe
FFPROBE_PATH = find_ffprobe()
if FFMPEG_PATH:
    print(f"[VideoProcessor] Found FFmpeg: {FFMPEG_PATH}", flush=True)
else:
    print("[VideoProcessor] WARNING: FFmpeg not found! GIF conversion will fail.", flush=True)
    print("[VideoProcessor] Install FFmpeg: winget install ffmpeg", flush=True)
    print("[VideoProcessor] Then restart your terminal and this app.", flush=True)
    FFMPEG_PATH = 'ffmpeg'  # Fallback, will fail

if FFPROBE_PATH:
    print(f"[VideoProcessor] Found FFprobe: {FFPROBE_PATH}", flush=True)
else:
    print("[VideoProcessor] WARNING: FFprobe not found! Video metadata will be unavailable.", flush=True)
    FFPROBE_PATH = 'ffprobe'  # Fallback, will fail


def log(message):
    """Print log message and flush immediately for real-time output."""
    print(f"[VideoProcessor] {message}", flush=True)


def get_video_metadata(video_path):
    """
    Use FFprobe to get video width, height, duration, and fps.

    Args:
        video_path: Path to the video file

    Returns:
        dict with keys: width, height, duration, fps
        Returns None if metadata extraction fails
    """
    safe_path = sanitize_path(video_path)
    if not safe_path or not os.path.exists(safe_path):
        log("Invalid video path for metadata extraction")
        return None

    try:
        # Get video stream info using FFprobe
        cmd = [
            FFPROBE_PATH,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,r_frame_rate,duration',
            '-show_entries', 'format=duration',
            '-of', 'json',
            safe_path
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            shell=False
        )

        if result.returncode != 0:
            log(f"FFprobe failed: {result.stderr[:100] if result.stderr else 'unknown error'}")
            return None

        data = json.loads(result.stdout)

        # Extract stream info
        streams = data.get('streams', [])
        if not streams:
            log("No video streams found")
            return None

        stream = streams[0]
        width = int(stream.get('width', 0))
        height = int(stream.get('height', 0))

        # Parse frame rate (can be "30/1" or "29.97")
        fps_str = stream.get('r_frame_rate', '30/1')
        if '/' in fps_str:
            num, den = fps_str.split('/')
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(fps_str)

        # Get duration from stream or format
        duration = stream.get('duration')
        if duration is None:
            format_info = data.get('format', {})
            duration = format_info.get('duration')

        if duration is not None:
            duration = float(duration)
        else:
            duration = 0.0

        if width <= 0 or height <= 0:
            log("Invalid video dimensions")
            return None

        log(f"Video metadata: {width}x{height}, {duration:.1f}s, {fps:.2f} fps")

        return {
            'width': width,
            'height': height,
            'duration': duration,
            'fps': round(fps, 2)
        }

    except subprocess.TimeoutExpired:
        log("FFprobe timeout")
        return None
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        log(f"Failed to parse FFprobe output: {str(e)[:50]}")
        return None
    except Exception as e:
        log(f"Metadata extraction error: {str(e)[:50]}")
        return None


def extract_thumbnails(video_path, output_dir, count=4, width=640):
    """
    Extract thumbnail frames at evenly spaced intervals through the video.

    Args:
        video_path: Path to the source video
        output_dir: Directory to save thumbnails
        count: Number of thumbnails to extract (default: 4)
        width: Width of thumbnails in pixels (default: 640)

    Returns:
        List of dicts with keys: path, filename, timestamp
        Returns empty list if extraction fails
    """
    safe_video_path = sanitize_path(video_path)
    safe_output_dir = sanitize_path(output_dir)

    if not safe_video_path or not os.path.exists(safe_video_path):
        log("Invalid video path for thumbnail extraction")
        return []

    if not safe_output_dir:
        log("Invalid output directory for thumbnails")
        return []

    # Ensure output directory exists
    try:
        os.makedirs(safe_output_dir, exist_ok=True)
    except OSError as e:
        log(f"Failed to create thumbnail directory: {str(e)[:50]}")
        return []

    # Get video metadata for duration
    metadata = get_video_metadata(safe_video_path)
    if not metadata or metadata['duration'] <= 0:
        log("Cannot extract thumbnails: invalid video duration")
        return []

    duration = metadata['duration']
    thumbnails = []

    # Calculate timestamps at 0%, 25%, 50%, 75% of duration
    for i in range(count):
        # Avoid extracting at exact end of video
        percentage = i / count
        timestamp = duration * percentage

        # Ensure we don't go beyond video duration
        if timestamp >= duration:
            timestamp = max(0, duration - 0.1)

        thumb_filename = f"thumb_{i}.jpg"
        thumb_path = os.path.join(safe_output_dir, thumb_filename)

        # Extract frame using FFmpeg
        cmd = [
            FFMPEG_PATH,
            '-hide_banner',
            '-loglevel', 'error',
            '-y',
            '-ss', str(timestamp),
            '-i', safe_video_path,
            '-vframes', '1',
            '-vf', f'scale={width}:-1:flags=fast_bilinear',
            '-q:v', '2',  # JPEG quality (2 = high quality)
            thumb_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                shell=False
            )

            if result.returncode == 0 and os.path.exists(thumb_path):
                thumbnails.append({
                    'path': thumb_path,
                    'filename': thumb_filename,
                    'timestamp': round(timestamp, 2)
                })
            else:
                log(f"Failed to extract thumbnail at {timestamp:.1f}s")

        except subprocess.TimeoutExpired:
            log(f"Thumbnail extraction timeout at {timestamp:.1f}s")
        except Exception as e:
            log(f"Thumbnail extraction error: {str(e)[:50]}")

    log(f"Extracted {len(thumbnails)}/{count} thumbnails")
    return thumbnails


def validate_crop_settings(crop, video_width, video_height):
    """
    Validate crop bounds and ensure values are valid for FFmpeg.

    Args:
        crop: dict with keys x, y, w, h (in pixels)
        video_width: Original video width
        video_height: Original video height

    Returns:
        Validated crop dict with even numbers, or None if invalid
    """
    if not crop or not isinstance(crop, dict):
        return None

    try:
        x = int(crop.get('x', 0))
        y = int(crop.get('y', 0))
        w = int(crop.get('w', 0))
        h = int(crop.get('h', 0))
    except (ValueError, TypeError):
        log("Invalid crop parameters")
        return None

    # Minimum crop size (from config)
    min_size = config.MIN_CROP_SIZE

    # Validate crop bounds
    if w < min_size or h < min_size:
        log(f"Crop too small: {w}x{h} (minimum: {min_size}x{min_size})")
        return None

    if x < 0 or y < 0:
        log(f"Crop position negative: x={x}, y={y}")
        return None

    if x + w > video_width or y + h > video_height:
        log(f"Crop exceeds video bounds: {x}+{w}>{video_width} or {y}+{h}>{video_height}")
        return None

    # Ensure even numbers for codec compatibility
    x = x - (x % 2)
    y = y - (y % 2)
    w = w - (w % 2)
    h = h - (h % 2)

    # Re-validate after rounding
    if w < min_size or h < min_size:
        log("Crop too small after rounding to even numbers")
        return None

    return {'x': x, 'y': y, 'w': w, 'h': h}


# =============================================================================
# CONFIGURATION - All settings loaded from config.py / environment variables
# See .env.example for all available options
# =============================================================================

# GIF Output Defaults (users can override via web UI)
DEFAULT_MAX_GIF_DURATION = config.DEFAULT_GIF_DURATION
DEFAULT_SCENE_THRESHOLD = config.DEFAULT_SCENE_THRESHOLD
DEFAULT_GIF_FPS = config.DEFAULT_GIF_FPS
DEFAULT_GIF_WIDTH = config.DEFAULT_GIF_WIDTH

# For backward compatibility
MAX_GIF_DURATION = DEFAULT_MAX_GIF_DURATION
SCENE_THRESHOLD = DEFAULT_SCENE_THRESHOLD
GIF_FPS = DEFAULT_GIF_FPS
GIF_WIDTH = DEFAULT_GIF_WIDTH

# Processing Limits
MAX_CLIPS = config.MAX_CLIPS
MAX_VIDEO_DURATION = config.MAX_VIDEO_DURATION

# Timeouts
FFMPEG_TIMEOUT = config.FFMPEG_TIMEOUT
FFMPEG_MERGE_TIMEOUT = config.FFMPEG_MERGE_TIMEOUT


def sanitize_path(path):
    """Sanitize a file path for use in FFmpeg commands."""
    if not path:
        return None
    # Ensure path doesn't contain null bytes
    if '\x00' in path:
        return None
    # Convert to absolute path and normalize
    return os.path.abspath(path)


def validate_numeric_param(value, min_val, max_val, default):
    """Validate and clamp a numeric parameter."""
    try:
        val = float(value)
        return max(min_val, min(max_val, val))
    except (ValueError, TypeError):
        return default


def detect_scenes(video_path, threshold=SCENE_THRESHOLD):
    """
    Use PySceneDetect to find scene boundaries.

    Args:
        video_path: Path to the video file
        threshold: Sensitivity for scene detection (lower = more sensitive)

    Returns:
        List of (start_time, end_time) tuples in seconds
    """
    # Validate path
    safe_path = sanitize_path(video_path)
    if not safe_path or not os.path.exists(safe_path):
        raise ValueError("Invalid video path")

    # Validate threshold
    threshold = validate_numeric_param(threshold, 10, 60, SCENE_THRESHOLD)

    log(f"Opening video: {os.path.basename(safe_path)}")
    try:
        video = open_video(safe_path)
    except Exception as e:
        log(f"Failed to open video: {e}")
        raise ValueError(f"Could not open video file")

    duration = video.duration.get_seconds()
    log(f"Video duration: {duration:.1f}s")

    # Check video duration limit (0 = no limit)
    if MAX_VIDEO_DURATION > 0 and duration > MAX_VIDEO_DURATION:
        raise ValueError(f"Video too long. Maximum duration is {MAX_VIDEO_DURATION // 60} minutes.")

    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))

    log("Detecting scenes... (this may take a while for long videos)")
    try:
        scene_manager.detect_scenes(video)
    except Exception as e:
        log(f"Scene detection failed: {e}")
        raise ValueError("Scene detection failed")

    scene_list = scene_manager.get_scene_list()

    if not scene_list:
        # No scenes detected - treat entire video as one scene
        log("No scene cuts detected, treating as single scene")
        video = open_video(safe_path)
        duration = video.duration.get_seconds()
        return [(0.0, duration)]

    log(f"Detected {len(scene_list)} scenes")

    # Convert FrameTimecode to seconds
    scenes = []
    for scene in scene_list:
        start = scene[0].get_seconds()
        end = scene[1].get_seconds()
        # Validate scene times
        if start >= 0 and end > start and end <= duration:
            scenes.append((start, end))

    return scenes


def split_long_scenes(scenes, max_duration=MAX_GIF_DURATION):
    """
    Subdivide any scene longer than max_duration into chunks.

    Args:
        scenes: List of (start_time, end_time) tuples
        max_duration: Maximum duration for each chunk

    Returns:
        Refined list of (start_time, end_time) tuples
    """
    # Validate max_duration
    max_duration = validate_numeric_param(max_duration, 1.0, 30.0, MAX_GIF_DURATION)

    refined_scenes = []

    for start, end in scenes:
        # Validate scene times
        if not (isinstance(start, (int, float)) and isinstance(end, (int, float))):
            continue
        if start < 0 or end <= start:
            continue

        duration = end - start

        if duration <= max_duration:
            # Scene is short enough, keep as-is
            refined_scenes.append((start, end))
        else:
            # Split into max_duration chunks
            current = start
            while current < end:
                chunk_end = min(current + max_duration, end)
                refined_scenes.append((current, chunk_end))
                current = chunk_end

                # Safety limit on number of clips (0 = no limit)
                if MAX_CLIPS > 0 and len(refined_scenes) >= MAX_CLIPS:
                    log(f"Warning: Reached maximum clip limit ({MAX_CLIPS})")
                    break

        # Safety limit on number of clips (0 = no limit)
        if MAX_CLIPS > 0 and len(refined_scenes) >= MAX_CLIPS:
            break

    log(f"Split into {len(refined_scenes)} clips (max {max_duration}s each)")
    return refined_scenes


def extract_clip_as_gif(video_path, start, end, output_path, fps=GIF_FPS, width=GIF_WIDTH, crop=None):
    """
    Use FFmpeg to extract a clip and convert it to an optimized GIF.

    Args:
        video_path: Path to the source video
        start: Start time in seconds
        end: End time in seconds
        output_path: Path for the output GIF
        fps: Frames per second for the GIF
        width: Width in pixels (height auto-scaled)
        crop: Optional dict with keys x, y, w, h for cropping (in original video pixels)

    Returns:
        True if successful, False otherwise
    """
    # Validate paths
    safe_video_path = sanitize_path(video_path)
    safe_output_path = sanitize_path(output_path)

    if not safe_video_path or not safe_output_path:
        log("Invalid path provided")
        return False

    if not os.path.exists(safe_video_path):
        log("Video file does not exist")
        return False

    # Validate numeric parameters
    start = validate_numeric_param(start, 0, MAX_VIDEO_DURATION, 0)
    end = validate_numeric_param(end, 0, MAX_VIDEO_DURATION, 5)
    fps = int(validate_numeric_param(fps, 5, 30, GIF_FPS))
    # Width of 0 means "native" (no scaling, use original/crop dimensions)
    native_width = (width == 0)
    if not native_width:
        width = int(validate_numeric_param(width, 240, 1920, GIF_WIDTH))

    if end <= start:
        log("Invalid time range")
        return False

    duration = end - start

    # Build video filter string
    # If crop is provided, apply crop BEFORE scale for better quality
    filter_parts = []

    if crop and isinstance(crop, dict):
        crop_x = crop.get('x', 0)
        crop_y = crop.get('y', 0)
        crop_w = crop.get('w', 0)
        crop_h = crop.get('h', 0)
        if crop_w > 0 and crop_h > 0:
            filter_parts.append(f'crop={crop_w}:{crop_h}:{crop_x}:{crop_y}')

    filter_parts.append(f'fps={fps}')
    if not native_width:
        filter_parts.append(f'scale={width}:-1:flags=lanczos')

    vf_string = ','.join(filter_parts)

    # Two-pass palette approach for high-quality GIFs
    # Pass 1: Generate optimized 256-color palette from actual video frames
    # Pass 2: Create GIF using that palette with Floyd-Steinberg dithering
    # This dramatically reduces banding/graininess compared to single-pass
    palette_path = safe_output_path + '.palette.png'
    success = False

    try:
        # Pass 1: Generate optimized color palette
        palette_cmd = [
            FFMPEG_PATH,
            '-hide_banner',
            '-loglevel', 'error',
            '-y',
            '-ss', str(start),
            '-t', str(duration),
            '-i', safe_video_path,
            '-vf', vf_string + ',palettegen=stats_mode=diff',
            palette_path
        ]

        result1 = subprocess.run(
            palette_cmd,
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT,
            shell=False
        )

        if result1.returncode == 0 and os.path.exists(palette_path):
            # Pass 2: Create GIF using optimized palette
            gif_cmd = [
                FFMPEG_PATH,
                '-hide_banner',
                '-loglevel', 'error',
                '-y',
                '-ss', str(start),
                '-t', str(duration),
                '-i', safe_video_path,
                '-i', palette_path,
                '-lavfi', vf_string + '[x];[x][1:v]paletteuse=dither=floyd_steinberg',
                '-loop', '0',
                safe_output_path
            ]

            result2 = subprocess.run(
                gif_cmd,
                capture_output=True,
                text=True,
                timeout=FFMPEG_TIMEOUT,
                shell=False
            )

            if result2.returncode == 0:
                success = True
            else:
                if result2.stderr.strip():
                    error_msg = result2.stderr.strip()[:200]
                    error_msg = re.sub(r'[A-Za-z]:\\[^\s]+', '[path]', error_msg)
                    error_msg = re.sub(r'/[^\s]+', '[path]', error_msg)
                    log(f"FFmpeg palette pass error: {error_msg}")

        if not success:
            # Fallback: single-pass encoding (lower quality but always works)
            log("Palette method failed, using fallback encoding")
            fallback_cmd = [
                FFMPEG_PATH,
                '-hide_banner',
                '-loglevel', 'error',
                '-y',
                '-ss', str(start),
                '-t', str(duration),
                '-i', safe_video_path,
                '-vf', vf_string,
                '-loop', '0',
                safe_output_path
            ]

            result = subprocess.run(
                fallback_cmd,
                capture_output=True,
                text=True,
                timeout=FFMPEG_TIMEOUT,
                shell=False
            )

            if result.returncode != 0:
                if result.stderr.strip():
                    error_msg = result.stderr.strip()[:200]
                    error_msg = re.sub(r'[A-Za-z]:\\[^\s]+', '[path]', error_msg)
                    error_msg = re.sub(r'/[^\s]+', '[path]', error_msg)
                    log(f"FFmpeg error: {error_msg}")

            success = result.returncode == 0

        return success

    except subprocess.TimeoutExpired:
        log(f"FFmpeg timeout (>{FFMPEG_TIMEOUT}s)")
        return False
    except FileNotFoundError:
        log("FFmpeg not found")
        return False
    except Exception as e:
        error_msg = str(e)[:100]
        error_msg = re.sub(r'[A-Za-z]:\\[^\s]+', '[path]', error_msg)
        error_msg = re.sub(r'/[^\s]+', '[path]', error_msg)
        log(f"FFmpeg exception: {error_msg}")
        return False
    finally:
        # Clean up temporary palette file
        try:
            if os.path.exists(palette_path):
                os.remove(palette_path)
        except OSError:
            pass


def convert_gif_to_grayscale(input_path, output_path):
    """
    Convert a GIF to grayscale using FFmpeg.

    Args:
        input_path: Path to the source GIF
        output_path: Path for the output grayscale GIF

    Returns:
        True if successful, False otherwise
    """
    # Validate paths
    safe_input_path = sanitize_path(input_path)
    safe_output_path = sanitize_path(output_path)

    if not safe_input_path or not safe_output_path:
        log("Invalid path provided for grayscale conversion")
        return False

    if not os.path.exists(safe_input_path):
        log("Source GIF does not exist")
        return False

    log(f"Converting to grayscale: {os.path.basename(safe_input_path)}")

    # FFmpeg command for grayscale conversion
    cmd = [
        FFMPEG_PATH,
        '-hide_banner',
        '-loglevel', 'error',
        '-y',
        '-i', safe_input_path,
        '-vf', 'format=gray',
        '-loop', '0',
        safe_output_path
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=FFMPEG_TIMEOUT,
            shell=False
        )
        if result.returncode != 0:
            if result.stderr.strip():
                error_msg = result.stderr.strip()[:200]
                error_msg = re.sub(r'[A-Za-z]:\\[^\s]+', '[path]', error_msg)
                error_msg = re.sub(r'/[^\s]+', '[path]', error_msg)
                log(f"Grayscale error: {error_msg}")
            return False
        log(f"Grayscale conversion complete: {os.path.basename(safe_output_path)}")
        return True
    except subprocess.TimeoutExpired:
        log(f"Grayscale timeout (>{FFMPEG_TIMEOUT}s)")
        return False
    except FileNotFoundError:
        log("FFmpeg not found")
        return False
    except Exception as e:
        error_msg = str(e)[:100]
        error_msg = re.sub(r'[A-Za-z]:\\[^\s]+', '[path]', error_msg)
        error_msg = re.sub(r'/[^\s]+', '[path]', error_msg)
        log(f"Grayscale exception: {error_msg}")
        return False


def merge_gifs_grid(gif_paths, output_path, columns=2, width=480):
    """
    Concatenate multiple GIFs sequentially (play one after another).

    Args:
        gif_paths: List of paths to GIF files
        output_path: Path for the output merged GIF
        columns: Unused, kept for compatibility
        width: Width to scale all GIFs to (default: 480)

    Returns:
        True if successful, False otherwise
    """
    if not gif_paths:
        return False

    # Validate output path
    safe_output_path = sanitize_path(output_path)
    if not safe_output_path:
        log("Invalid output path")
        return False

    # Validate and sanitize all input paths
    safe_gif_paths = []
    for path in gif_paths:
        safe_path = sanitize_path(path)
        if safe_path and os.path.exists(safe_path):
            safe_gif_paths.append(safe_path)
        else:
            log(f"Skipping invalid GIF path")

    if len(safe_gif_paths) < 2:
        log("Not enough valid GIF files to merge")
        return False

    # Limit number of GIFs that can be merged
    if len(safe_gif_paths) > 20:
        log("Too many GIFs to merge (max 20)")
        safe_gif_paths = safe_gif_paths[:20]

    if len(safe_gif_paths) == 1:
        # Just copy the single GIF
        try:
            shutil.copy(safe_gif_paths[0], safe_output_path)
            return True
        except (IOError, OSError) as e:
            log(f"Failed to copy GIF: {e}")
            return False

    log(f"Concatenating {len(safe_gif_paths)} GIFs...")

    # Validate width parameter
    width = int(validate_numeric_param(width, 240, 1920, 480))

    n = len(safe_gif_paths)

    # Build FFmpeg command for concatenation
    cmd = [FFMPEG_PATH, '-hide_banner', '-loglevel', 'error', '-y']

    # Add all input GIFs
    for path in safe_gif_paths:
        cmd.extend(['-i', path])

    # Build concat filter - scale all to same size first, then concatenate
    filter_parts = []
    scaled_labels = []

    for i in range(n):
        # Scale each GIF to consistent size (user-specified width)
        label = f"[v{i}]"
        filter_parts.append(f"[{i}]scale={width}:-1:flags=lanczos,setsar=1{label}")
        scaled_labels.append(label)

    # Concatenate all scaled videos
    filter_parts.append(f"{''.join(scaled_labels)}concat=n={n}:v=1:a=0[out]")
    filter_complex = ";".join(filter_parts)

    cmd.extend(['-filter_complex', filter_complex, '-map', '[out]', '-loop', '0', safe_output_path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=FFMPEG_MERGE_TIMEOUT,
            shell=False  # Explicitly disable shell
        )
        if result.returncode != 0:
            if result.stderr.strip():
                # Sanitize error message
                error_msg = result.stderr.strip()[:200]
                error_msg = re.sub(r'[A-Za-z]:\\[^\s]+', '[path]', error_msg)
                error_msg = re.sub(r'/[^\s]+', '[path]', error_msg)
                log(f"Merge error: {error_msg}")
        else:
            log("Merge complete!")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        log(f"Merge timeout (>{FFMPEG_MERGE_TIMEOUT}s)")
        return False
    except FileNotFoundError:
        log("FFmpeg not found")
        return False
    except Exception as e:
        # Sanitize error message
        error_msg = str(e)[:100]
        error_msg = re.sub(r'[A-Za-z]:\\[^\s]+', '[path]', error_msg)
        error_msg = re.sub(r'/[^\s]+', '[path]', error_msg)
        log(f"Merge exception: {error_msg}")
        return False


def process_video(video_path, output_dir, progress_callback=None, settings=None):
    """
    Full pipeline: detect scenes, split, and convert to GIFs.

    Args:
        video_path: Path to the input video
        output_dir: Directory for output GIFs
        progress_callback: Optional callback(gif_path, index, total) for progress updates
        settings: Optional dict with keys: max_duration, fps, width, threshold, crop

    Yields:
        Path to each generated GIF as it's created
    """
    # Validate paths
    safe_video_path = sanitize_path(video_path)
    safe_output_dir = sanitize_path(output_dir)

    if not safe_video_path or not os.path.exists(safe_video_path):
        raise ValueError("Invalid video path")

    if not safe_output_dir:
        raise ValueError("Invalid output directory")

    # Parse settings with defaults and validation
    if settings is None:
        settings = {}

    max_duration = validate_numeric_param(
        settings.get('max_duration'),
        1.0, 30.0, DEFAULT_MAX_GIF_DURATION
    )
    fps = int(validate_numeric_param(
        settings.get('fps'),
        5, 30, DEFAULT_GIF_FPS
    ))
    width_val = settings.get('width')
    try:
        width_raw = int(float(width_val)) if width_val is not None else DEFAULT_GIF_WIDTH
    except (ValueError, TypeError):
        width_raw = DEFAULT_GIF_WIDTH
    if width_raw == 0:
        width = 0  # Native mode - no scaling
    else:
        width = int(validate_numeric_param(width_val, 240, 1920, DEFAULT_GIF_WIDTH))
    threshold = int(validate_numeric_param(
        settings.get('threshold'),
        10, 60, DEFAULT_SCENE_THRESHOLD
    ))

    # Get crop settings if provided
    crop = settings.get('crop')
    if crop:
        # Get video metadata to validate crop
        metadata = get_video_metadata(safe_video_path)
        if metadata:
            crop = validate_crop_settings(crop, metadata['width'], metadata['height'])
            if crop:
                log(f"Crop: {crop['w']}x{crop['h']} at ({crop['x']},{crop['y']})")
            else:
                log("Invalid crop settings, using full frame")
        else:
            log("Could not get video metadata for crop validation, using full frame")
            crop = None

    log(f"Settings: max_duration={max_duration}s, fps={fps}, width={width}px, threshold={threshold}")

    # Ensure output directory exists
    try:
        os.makedirs(safe_output_dir, exist_ok=True)
    except OSError as e:
        raise ValueError(f"Could not create output directory")

    # Step 1: Detect scenes
    scenes = detect_scenes(safe_video_path, threshold=threshold)

    # Step 2: Split long scenes
    clips = split_long_scenes(scenes, max_duration=max_duration)

    total_clips = len(clips)
    if total_clips == 0:
        log("No clips to process")
        return

    # Step 3: Convert each clip to GIF
    log(f"Starting GIF conversion for {total_clips} clips...")
    successful_clips = 0

    for idx, (start, end) in enumerate(clips):
        # Generate safe filename
        gif_filename = f"clip_{idx:04d}.gif"
        gif_path = os.path.join(safe_output_dir, gif_filename)

        log(f"Creating GIF {idx + 1}/{total_clips}: {start:.1f}s - {end:.1f}s")
        success = extract_clip_as_gif(safe_video_path, start, end, gif_path, fps=fps, width=width, crop=crop)

        if success and os.path.exists(gif_path):
            try:
                file_size = os.path.getsize(gif_path) / 1024  # KB
                log(f"  -> Done: {gif_filename} ({file_size:.1f} KB)")
            except OSError:
                log(f"  -> Done: {gif_filename}")

            if progress_callback:
                try:
                    progress_callback(gif_path, idx, total_clips)
                except Exception:
                    pass  # Ignore callback errors

            successful_clips += 1
            yield gif_path
        else:
            log(f"  -> FAILED: {gif_filename}")

    log(f"All GIFs created! ({successful_clips}/{total_clips} successful)")
