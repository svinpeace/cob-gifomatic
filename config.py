"""
Gifomatic Configuration

All settings can be configured via environment variables.
Copy .env.example to .env and modify as needed.

Usage:
    from config import config
    print(config.MAX_UPLOAD_SIZE)
"""

import os
from pathlib import Path

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"[Config] Loaded .env from {env_path}", flush=True)
except ImportError:
    pass  # python-dotenv not installed, use system env vars only


def get_env_int(key, default):
    """Get integer from environment variable."""
    try:
        return int(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def get_env_float(key, default):
    """Get float from environment variable."""
    try:
        return float(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


def get_env_bool(key, default):
    """Get boolean from environment variable."""
    val = os.environ.get(key, str(default)).lower()
    return val in ('true', '1', 'yes', 'on')


def get_env_str(key, default):
    """Get string from environment variable."""
    return os.environ.get(key, default)


class Config:
    """Central configuration for Gifomatic."""

    # ==========================================================================
    # FLASK SETTINGS
    # ==========================================================================

    # Secret key for session encryption (CHANGE IN PRODUCTION)
    SECRET_KEY = get_env_str('SECRET_KEY', None)  # Auto-generated if None

    # Flask environment: 'development' or 'production'
    FLASK_ENV = get_env_str('FLASK_ENV', 'production')

    # Server host and port
    HOST = get_env_str('HOST', '0.0.0.0')
    PORT = get_env_int('PORT', 5000)

    # ==========================================================================
    # FILE & UPLOAD LIMITS
    # ==========================================================================

    # Maximum upload file size in bytes (default: 5GB)
    MAX_UPLOAD_SIZE = get_env_int('MAX_UPLOAD_SIZE', 5 * 1024 * 1024 * 1024)

    # Allowed video file extensions
    ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', 'wmv'}

    # ==========================================================================
    # RATE LIMITING
    # ==========================================================================

    # Time window for rate limiting in seconds
    RATE_LIMIT_WINDOW = get_env_int('RATE_LIMIT_WINDOW', 60)

    # Maximum API requests per window per IP
    RATE_LIMIT_MAX_REQUESTS = get_env_int('RATE_LIMIT_MAX_REQUESTS', 10)

    # Maximum video uploads per window per IP
    RATE_LIMIT_MAX_UPLOADS = get_env_int('RATE_LIMIT_MAX_UPLOADS', 3)

    # ==========================================================================
    # JOB MANAGEMENT
    # ==========================================================================

    # Maximum simultaneous video processing jobs
    MAX_CONCURRENT_JOBS = get_env_int('MAX_CONCURRENT_JOBS', 5)

    # Hours before jobs are auto-cleaned (0 = never)
    JOB_EXPIRY_HOURS = get_env_int('JOB_EXPIRY_HOURS', 0)

    # Maximum cache entries before oldest are removed
    MAX_JOBS_STORED = get_env_int('MAX_JOBS_STORED', 100)

    # ==========================================================================
    # VIDEO PROCESSING LIMITS
    # ==========================================================================

    # Maximum video duration in seconds (0 = no limit, default: 3 hours)
    MAX_VIDEO_DURATION = get_env_int('MAX_VIDEO_DURATION', 10800)

    # Maximum clips per video (0 = no limit)
    MAX_CLIPS = get_env_int('MAX_CLIPS', 0)

    # Maximum GIFs that can be merged at once
    MAX_MERGE_GIFS = get_env_int('MAX_MERGE_GIFS', 20)

    # ==========================================================================
    # GIF OUTPUT DEFAULTS (users can override via web UI)
    # ==========================================================================

    # Maximum seconds per GIF clip
    DEFAULT_GIF_DURATION = get_env_float('DEFAULT_GIF_DURATION', 5.0)

    # Scene detection sensitivity (lower = more cuts)
    DEFAULT_SCENE_THRESHOLD = get_env_int('DEFAULT_SCENE_THRESHOLD', 30)

    # Frames per second
    DEFAULT_GIF_FPS = get_env_int('DEFAULT_GIF_FPS', 10)

    # Width in pixels (height auto-scaled)
    DEFAULT_GIF_WIDTH = get_env_int('DEFAULT_GIF_WIDTH', 480)

    # ==========================================================================
    # DIRECTORIES
    # ==========================================================================

    # Temporary upload storage
    UPLOAD_FOLDER = get_env_str('UPLOAD_FOLDER', 'uploads')

    # Generated GIFs storage
    OUTPUT_FOLDER = get_env_str('OUTPUT_FOLDER', 'output')

    # Cache file path
    CACHE_FILE = get_env_str('CACHE_FILE', 'cache.json')

    # ==========================================================================
    # TIMEOUTS
    # ==========================================================================

    # FFmpeg timeout per GIF in seconds
    FFMPEG_TIMEOUT = get_env_int('FFMPEG_TIMEOUT', 60)

    # FFmpeg timeout for merge operations in seconds
    FFMPEG_MERGE_TIMEOUT = get_env_int('FFMPEG_MERGE_TIMEOUT', 300)


# Singleton instance
config = Config()


# Print configuration on import if in debug mode
if config.FLASK_ENV == 'development':
    print("[Config] Loaded configuration:", flush=True)
    print(f"  - MAX_UPLOAD_SIZE: {config.MAX_UPLOAD_SIZE // (1024*1024)}MB", flush=True)
    print(f"  - MAX_VIDEO_DURATION: {config.MAX_VIDEO_DURATION}s ({config.MAX_VIDEO_DURATION // 3600}h)", flush=True)
    print(f"  - MAX_CLIPS: {config.MAX_CLIPS or 'unlimited'}", flush=True)
    print(f"  - MAX_CONCURRENT_JOBS: {config.MAX_CONCURRENT_JOBS}", flush=True)
    print(f"  - JOB_EXPIRY_HOURS: {config.JOB_EXPIRY_HOURS or 'never'}", flush=True)
