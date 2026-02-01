# Changelog

All notable changes to Gifomatic will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Configurable GIF settings via UI (width, FPS, duration, scene sensitivity)
- Quick presets: Small Files, Balanced, HD Quality, Maximum
- Settings-aware caching (different settings create separate cache entries)
- Collapsible settings panel with smooth animations
- CLAUDE.md for AI assistant guidelines
- CHANGELOG.md for tracking changes
- CONTRIBUTING.md for contribution guidelines
- CODE_OF_CONDUCT.md for community standards

### Changed
- Updated User Guide with new settings documentation
- Info cards now show configurable ranges instead of fixed values
- Cache key includes settings hash for proper cache invalidation

## [1.1.0] - 2026-02-01

### Security
- **CRITICAL**: Fixed path traversal vulnerability in `/output/<job_id>/<filename>` endpoint
- **CRITICAL**: Fixed path traversal vulnerability in `/load/<job_id>` endpoint
- **CRITICAL**: Added UUID validation for all job IDs to prevent directory traversal attacks
- **CRITICAL**: Added filename validation to prevent path injection via filenames
- **HIGH**: Added 500MB file size limit (`MAX_CONTENT_LENGTH`) to prevent DoS attacks
- **HIGH**: Fixed XSS vulnerability in JavaScript by using safe DOM manipulation instead of innerHTML
- **HIGH**: Replaced MD5 with SHA-256 for file hashing (cryptographically stronger)
- **HIGH**: Added video file magic byte validation (not just extension checking)
- **MEDIUM**: Added rate limiting (10 requests/minute, 3 uploads/minute per IP)
- **MEDIUM**: Added security headers (CSP, X-Frame-Options, X-Content-Type-Options, etc.)
- **MEDIUM**: Sanitized error messages to prevent information disclosure
- **MEDIUM**: Fixed bare `except` clauses to catch specific exceptions only
- **LOW**: Changed default debug mode to OFF (production default)

### Added
- **Grayscale conversion** - Convert any GIF to black and white with one click
- **Delete GIFs** - Remove unwanted GIFs directly from the interface
- **Centralized configuration** via `config.py` - all settings in one place
- **Environment variable support** - all settings configurable via `.env` file
- `.env.example` template with all default values (not commented out)
- Rate limiting system with configurable thresholds
- Concurrent job limiting (max 5 simultaneous processing jobs)
- Automatic job cleanup (disabled by default, configurable)
- SSE queue cleanup after job completion to prevent memory leaks
- Maximum video duration limit (3 hours default, configurable)
- Maximum clip limit (no limit by default, configurable)
- Maximum merge limit (20 GIFs at once, configurable)
- Configurable FFmpeg timeouts
- Input validation for all numeric parameters
- Thread-safe cache operations with file locking
- Atomic cache file writes to prevent corruption
- URL validation in JavaScript to prevent protocol injection
- Filename validation regex for strict format checking
- Error handlers for 404, 413, 429, 500 status codes

### Changed
- Cache operations now use threading locks for thread safety
- Merge function now accepts configurable width parameter (was hardcoded to 480px)
- All subprocess calls explicitly set `shell=False` for security
- All file paths are validated and sanitized before use
- JavaScript uses `textContent` instead of `innerHTML` for user data
- Job listing limited to 50 most recent jobs
- Improved error handling throughout the codebase
- Default `MAX_VIDEO_DURATION` increased to 3 hours (was 1 hour)
- Default `MAX_CLIPS` set to 0 (no limit, was 500)
- Default `JOB_EXPIRY_HOURS` set to 0 (never expire, was 24 hours)

### Fixed
- Memory leak from unbounded `job_queues` and `job_gifs` dictionaries
- Memory leak from unbounded `video_cache` dictionary
- Memory leak from unbounded `rate_limit_store` dictionary
- Race condition in cache check-then-act operations
- Silent failures when video file deletion fails
- Type errors when settings contain invalid values
- Potential file handle leaks in cache operations

## [1.0.0] - 2026-01-31

### Added
- Initial release of Gifomatic
- Automatic scene detection using PySceneDetect
- Real-time GIF streaming via Server-Sent Events (SSE)
- Video upload with drag-and-drop support
- GIF grid display with responsive layout
- Lightbox gallery view with keyboard navigation
- GIF selection with Select All / Unselect All
- Merge selected GIFs into continuous animation
- Download options: individual, selected, or all
- Tabs for Original GIFs and Merged GIFs
- Previous Jobs section for loading cached results
- File hash caching to avoid reprocessing
- Comprehensive User Guide page
- Docker and Docker Compose support
- Mobile-responsive design

### Supported Formats
- Input: MP4, AVI, MOV, MKV, WebM, FLV, WMV
- Output: GIF (optimized, looping)

---

## Version History Format

### Types of Changes
- **Added** - New features
- **Changed** - Changes in existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Vulnerability fixes

### Versioning
- MAJOR version for incompatible API changes
- MINOR version for backwards-compatible functionality
- PATCH version for backwards-compatible bug fixes
