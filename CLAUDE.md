# CLAUDE.md - AI Assistant Guidelines for Gifomatic

This file provides context and guidelines for AI assistants (like Claude) working on this codebase.

## Project Overview

**Gifomatic** is a Flask-based web application that converts videos to GIFs using intelligent scene detection. It uses PySceneDetect for scene analysis and FFmpeg for video processing.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.8+, Flask 3.0+ |
| Video Processing | FFmpeg (system), PySceneDetect |
| Frontend | Vanilla JavaScript, CSS3 |
| Real-time Updates | Server-Sent Events (SSE) |
| Containerization | Docker, Docker Compose |

## Project Structure

```
cob-gifomatic/
├── app.py                 # Flask routes and SSE handling
├── video_processor.py     # Core video/GIF processing logic
├── config.py              # Centralized configuration (env vars)
├── .env.example           # Example environment variables
├── requirements.txt       # Python dependencies
├── static/
│   ├── style.css         # Main styles
│   ├── guide.css         # User guide styles
│   └── app.js            # Frontend JavaScript
├── templates/
│   ├── index.html        # Main application page
│   └── guide.html        # User guide page
├── uploads/              # Temporary video storage (gitignored)
├── output/               # Generated GIFs (gitignored)
└── cache.json            # Video hash cache (gitignored)
```

## Key Files to Understand

### `app.py`
- Flask application with routes: `/`, `/guide`, `/upload`, `/stream/<job_id>`, `/merge`, `/jobs`, `/load/<job_id>`
- Handles file uploads, caching, and SSE streaming
- Settings are parsed from form data and passed to processor

### `video_processor.py`
- `detect_scenes()` - Uses PySceneDetect ContentDetector
- `split_long_scenes()` - Splits scenes exceeding max duration
- `extract_clip_as_gif()` - FFmpeg conversion to GIF
- `merge_gifs_grid()` - Concatenates multiple GIFs sequentially
- `process_video()` - Main pipeline, accepts settings dict

### `static/app.js`
- Handles form submission with settings
- SSE event handling for real-time GIF display
- Selection, merging, downloading logic
- Lightbox gallery functionality

## Configuration

All configuration is centralized in `config.py` and loaded from environment variables or `.env` file.

### `config.py`
- Central configuration singleton
- All settings loaded from environment variables
- Sensible defaults for all values
- Used by both `app.py` and `video_processor.py`

### Changing Settings
1. Copy `.env.example` to `.env`
2. Uncomment and modify desired settings
3. Restart the application

### User-configurable settings (via UI):
- `max_duration`: 1-30 seconds (default: 5)
- `width`: 320-1920 pixels (default: 480)
- `fps`: 5-30 (default: 10)
- `threshold`: 10-60 scene sensitivity (default: 30)

### Server settings (via .env):
- See `.env.example` for all available options
- Includes rate limits, file size limits, timeouts, etc.

## Common Tasks

### Adding a New Configuration Option
1. Add the setting to `config.py` with a default value
2. Add documentation to `.env.example`
3. Use `config.SETTING_NAME` in `app.py` or `video_processor.py`
4. Update `README.md` configuration table

### Adding a New Route
1. Add route in `app.py`
2. Create template in `templates/` if needed
3. Add navigation link in both `index.html` and `guide.html`
4. Update `README.md` API endpoints table

### Modifying GIF Processing
1. Edit `video_processor.py`
2. If adding new settings, update:
   - `config.py` (add config option)
   - `.env.example` (document the option)
   - `index.html` (add UI control if user-facing)
   - `app.js` (send with form data if user-facing)
   - `guide.html` (document the setting)

### Updating Styles
- Main app styles: `static/style.css`
- Guide page styles: `static/guide.css`
- Follow existing patterns (CSS variables, responsive breakpoints)

## Testing Locally

```bash
# Create and activate venv
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
# or: venv\Scripts\activate   # Windows CMD
# or: source venv/bin/activate # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Ensure FFmpeg is installed
ffmpeg -version

# Run the app
python app.py
# Visit http://localhost:5000
```

## Code Style Guidelines

- Python: Follow PEP 8, use type hints where helpful
- JavaScript: ES6+, no frameworks (vanilla JS only)
- CSS: Use existing color variables and patterns
- Always add `flush=True` to print statements for real-time logging
- Use the `log()` helper function for consistent logging

## Important Notes

1. **FFmpeg Required**: The app will not work without FFmpeg installed on the system
2. **Caching is Settings-Aware**: Same video + different settings = different cache entries
3. **No Database**: All state is file-based (cache.json, output folders)
4. **SSE for Real-time**: GIFs stream to client as they're created
5. **Videos are Deleted**: Source videos are removed after processing, only GIFs kept

## When Making Changes

1. Update `CHANGELOG.md` with your changes
2. Update `README.md` if adding features or changing behavior
3. Update `guide.html` for user-facing documentation
4. Test with various video formats and settings
5. Ensure responsive design still works on mobile

## Don't Forget

- Keep the footer attribution to COB/SV intact
- Maintain MIT license compliance
- Test Docker build if modifying dependencies
- Update version numbers when releasing

## IMPORTANT: Configuration Changes

**When adding or modifying ANY configuration option, ALL of these files MUST be updated:**

1. **`config.py`** - Add the setting with default value
2. **`.env.example`** - Add the setting with default value and description
3. **`README.md`** - Update the Configuration Summary Table and relevant sections
4. **`templates/guide.html`** - Update user documentation if user-facing

**Checklist for new config options:**
- [ ] Added to `config.py` with `get_env_*()` helper
- [ ] Added to `.env.example` with default value (NOT commented out)
- [ ] Added to README.md Configuration Summary Table
- [ ] Added to README.md relevant configuration section
- [ ] Updated guide.html if it affects user-facing features
- [ ] Updated CHANGELOG.md

**Files that should NEVER be committed:**
- `.env` - Contains actual configuration/secrets
- `cache.json` - User data
- `uploads/*` - User uploaded files
- `output/*` - Generated GIFs
