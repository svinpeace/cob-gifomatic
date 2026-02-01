# Gifomatic

**Gifomatic by COB** - A powerful web application that automatically splits videos into GIFs using intelligent scene detection. Upload a video, and the app will detect scene changes, split the video into clips, and convert each clip to a GIF in real-time.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**[User Guide](/guide)** | **[Contributing](CONTRIBUTING.md)** | **[Changelog](CHANGELOG.md)** | **[Code of Conduct](CODE_OF_CONDUCT.md)**

## Features

- **Automatic Scene Detection** - Uses PySceneDetect to intelligently detect scene changes
- **Configurable Quality** - Adjust width (320-1920px), FPS (5-30), duration (1-30s), and scene sensitivity
- **Quick Presets** - Choose from Small, Balanced, HD, or Maximum quality presets
- **Real-time Processing** - Watch GIFs appear in real-time as they're generated via Server-Sent Events (SSE)
- **Gallery View** - Click any GIF to view it in a fullscreen lightbox with navigation
- **Batch Selection** - Select multiple GIFs with Select All / Unselect All options
- **Merge GIFs** - Concatenate selected GIFs into a single continuous GIF
- **Grayscale Conversion** - Convert any GIF to black and white with one click
- **Delete GIFs** - Remove unwanted GIFs directly from the interface
- **Download Options** - Download individual GIFs, selected GIFs, or all at once
- **Smart Caching** - Previously processed videos are cached (settings-aware)
- **Responsive Design** - Works on desktop and mobile devices
- **Environment Configuration** - All settings configurable via `.env` file
- **User Guide** - Built-in comprehensive tutorial and documentation

## Supported Formats

### Video Input Formats
- MP4 (.mp4)
- AVI (.avi)
- MOV (.mov)
- MKV (.mkv)
- WebM (.webm)
- FLV (.flv)
- WMV (.wmv)

### Output Format
- GIF (.gif) - Optimized with 10 FPS, 480px width

## Limitations

Default limits (all configurable - see [Configuration](#via-code---server-limits)):

| Limit | Default | Configurable In |
|-------|---------|-----------------|
| Maximum File Size | 5GB | `.env` / `config.py` |
| Maximum Video Duration | 3 hours | `video_processor.py` |
| Maximum Clips Per Video | No limit | `video_processor.py` |
| Maximum GIFs Per Merge | 20 | `app.py` |
| Concurrent Jobs | 5 | `app.py` |
| Rate Limits | 10 req/min, 3 uploads/min | `app.py` |
| Job Retention | Never (manual cleanup) | `app.py` |

**Other considerations:**
- **Processing Time**: Depends on video length, quality settings, and system resources
- **GIF File Size**: Higher quality settings (resolution, FPS) create significantly larger files
- **Memory Usage**: Large videos with many clips consume more RAM during processing

## Prerequisites

### FFmpeg Installation

FFmpeg is required for video processing and GIF conversion.

#### Windows

**Option 1 - Using winget (Recommended):**
```bash
winget install ffmpeg
```

**Option 2 - Using Chocolatey:**
```bash
choco install ffmpeg
```

**Option 3 - Manual Installation:**
1. Download from [ffmpeg.org](https://ffmpeg.org/download.html) or [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)
2. Extract to `C:\ffmpeg`
3. Add `C:\ffmpeg\bin` to your system PATH
4. Restart your terminal

#### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install ffmpeg
```

#### Linux (Fedora)
```bash
sudo dnf install ffmpeg
```

#### Linux (Arch)
```bash
sudo pacman -S ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

#### Verify Installation
```bash
ffmpeg -version
```

## Installation & Setup

### Option 1: Using Virtual Environment (Recommended)

#### Windows (Git Bash)
```bash
# Clone the repository
git clone https://github.com/anthropics/cob-gifomatic.git
cd cob-gifomatic

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

#### Windows (Command Prompt)
```cmd
# Clone the repository
git clone https://github.com/anthropics/cob-gifomatic.git
cd cob-gifomatic

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

#### Linux / macOS
```bash
# Clone the repository
git clone https://github.com/anthropics/cob-gifomatic.git
cd cob-gifomatic

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Option 2: Using Docker

#### Using Docker Compose (Recommended)
```bash
# Clone the repository
git clone https://github.com/anthropics/cob-gifomatic.git
cd cob-gifomatic

# Build and run
docker-compose up --build

# Run in detached mode
docker-compose up -d --build
```

#### Using Docker directly
```bash
# Build the image
docker build -t gifomatic .

# Run the container
docker run -p 5000:5000 -v $(pwd)/output:/app/output gifomatic
```

### Access the Application

Open your browser and navigate to:
```
http://localhost:5000
```

## Usage

1. **Upload a Video** - Click "Choose a video file" or drag and drop a video
2. **Wait for Processing** - The app will detect scenes and generate GIFs in real-time
3. **Browse GIFs** - View all generated GIFs in the "Original GIFs" tab
4. **Preview** - Click on any GIF to open it in the lightbox gallery
5. **Select GIFs** - Click on GIF cards to select them (or use Select All)
6. **Merge** - Select 2 or more GIFs and click "Merge Selected" to concatenate them
7. **Download** - Download individual GIFs, selected GIFs, or all at once
8. **View Merged** - Switch to "Merged GIFs" tab to see and download merged results

For detailed instructions, visit the **User Guide** page in the application.

## Configuration

All configuration is centralized in `config.py` and can be overridden via environment variables or a `.env` file.

### Quick Start

```bash
# Copy the example config
cp .env.example .env

# Edit as needed
nano .env  # or use your preferred editor

# Run the app (it will load .env automatically)
python app.py
```

### Via Web Interface

Use the **GIF Settings** panel in the web interface to configure:

| Setting | Range | Default | Description |
|---------|-------|---------|-------------|
| Max Duration | 1-30 sec | 5 sec | Maximum GIF length (longer scenes are split) |
| GIF Width | 320-1920 px | 480 px | Output width (height auto-scales) |
| Frame Rate | 5-30 FPS | 10 FPS | Higher = smoother, larger files |
| Scene Sensitivity | 10-60 | 30 | Lower = more scene cuts detected |

**Quick Presets:**
- **Small Files**: 320px, 5 FPS, 3s - Minimal file size
- **Balanced**: 480px, 10 FPS, 5s - Good quality/size ratio (default)
- **HD Quality**: 720px, 15 FPS, 5s - High quality
- **Maximum**: 1080px, 24 FPS, 10s - Best quality, largest files

### Via Environment Variables / .env File

All settings can be configured via environment variables. Create a `.env` file from the example:

```bash
cp .env.example .env
```

#### GIF Output Defaults

```bash
# Maximum seconds per GIF clip (default: 5.0)
DEFAULT_GIF_DURATION=5.0

# Scene detection sensitivity, lower = more cuts (default: 30)
DEFAULT_SCENE_THRESHOLD=30

# Frames per second (default: 10)
DEFAULT_GIF_FPS=10

# Width in pixels (default: 480)
DEFAULT_GIF_WIDTH=480
```

#### File & Upload Limits

```bash
# Maximum upload file size in bytes (default: 5GB)
MAX_UPLOAD_SIZE=5368709120

# For 10GB limit:
MAX_UPLOAD_SIZE=10737418240
```

#### Rate Limiting

```bash
# Time window in seconds (default: 60)
RATE_LIMIT_WINDOW=60

# Max requests per window per IP (default: 10)
RATE_LIMIT_MAX_REQUESTS=10

# Max uploads per window per IP (default: 3)
RATE_LIMIT_MAX_UPLOADS=3

# To effectively disable rate limiting:
RATE_LIMIT_MAX_REQUESTS=99999
RATE_LIMIT_MAX_UPLOADS=99999
```

#### Job Management

```bash
# Max simultaneous processing jobs (default: 5)
MAX_CONCURRENT_JOBS=5

# Hours before auto-cleanup, 0 = never (default: 0)
JOB_EXPIRY_HOURS=0

# To enable auto-cleanup after 24 hours:
JOB_EXPIRY_HOURS=24

# Max cache entries (default: 100)
MAX_JOBS_STORED=100
```

#### Video Processing Limits

```bash
# Max video duration in seconds, 0 = no limit (default: 10800 = 3 hours)
MAX_VIDEO_DURATION=10800

# Max clips per video, 0 = no limit (default: 0)
MAX_CLIPS=0

# Max GIFs per merge (default: 20)
MAX_MERGE_GIFS=20

# To remove all limits:
MAX_VIDEO_DURATION=0
MAX_CLIPS=0
```

#### Timeouts

```bash
# FFmpeg timeout per GIF in seconds (default: 60)
FFMPEG_TIMEOUT=60

# FFmpeg timeout for merge in seconds (default: 300)
FFMPEG_MERGE_TIMEOUT=300
```

#### Server Settings

```bash
# Secret key (REQUIRED for production - generate a random one)
SECRET_KEY=your-secret-key-here

# Flask environment: 'production' or 'development'
FLASK_ENV=production

# Host and port
HOST=0.0.0.0
PORT=5000
```

### Configuration Summary Table

All settings are environment variables (can be set in `.env` file):

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `SECRET_KEY` | auto-generated | Session encryption key (set for production) |
| `FLASK_ENV` | production | 'development' enables debug mode |
| `HOST` | 0.0.0.0 | Server bind address |
| `PORT` | 5000 | Server port |
| `MAX_UPLOAD_SIZE` | 5368709120 (5GB) | Maximum upload file size in bytes |
| `RATE_LIMIT_WINDOW` | 60 | Rate limit window in seconds |
| `RATE_LIMIT_MAX_REQUESTS` | 10 | Max API requests per window per IP |
| `RATE_LIMIT_MAX_UPLOADS` | 3 | Max uploads per window per IP |
| `MAX_CONCURRENT_JOBS` | 5 | Simultaneous processing jobs |
| `JOB_EXPIRY_HOURS` | 0 | Hours before auto-cleanup (0 = never) |
| `MAX_JOBS_STORED` | 100 | Maximum cache entries |
| `MAX_VIDEO_DURATION` | 10800 (3hr) | Max video length in seconds (0 = no limit) |
| `MAX_CLIPS` | 0 | Max clips per video (0 = no limit) |
| `MAX_MERGE_GIFS` | 20 | Max GIFs per merge operation |
| `DEFAULT_GIF_DURATION` | 5.0 | Default max seconds per GIF |
| `DEFAULT_GIF_FPS` | 10 | Default frames per second |
| `DEFAULT_GIF_WIDTH` | 480 | Default width in pixels |
| `DEFAULT_SCENE_THRESHOLD` | 30 | Default scene detection sensitivity |
| `FFMPEG_TIMEOUT` | 60 | FFmpeg timeout per GIF (seconds) |
| `FFMPEG_MERGE_TIMEOUT` | 300 | FFmpeg merge timeout (seconds) |

> **Note:** Setting `MAX_VIDEO_DURATION`, `MAX_CLIPS`, or `JOB_EXPIRY_HOURS` to `0` disables that limit.

## Project Structure

```
cob-gifomatic/
├── app.py                 # Flask application and routes
├── video_processor.py     # Video processing and GIF conversion
├── config.py              # Centralized configuration
├── .env.example           # Example environment variables
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose configuration
├── .gitignore           # Git ignore rules
├── .dockerignore        # Docker ignore rules
├── LICENSE              # MIT License
├── README.md            # This file
├── CHANGELOG.md         # Version history and changes
├── CONTRIBUTING.md      # Contribution guidelines
├── CODE_OF_CONDUCT.md   # Community standards
├── CLAUDE.md            # AI assistant guidelines
├── static/
│   ├── style.css        # Main styles
│   ├── guide.css        # User guide styles
│   └── app.js           # Frontend JavaScript
├── templates/
│   ├── index.html       # Main application page
│   └── guide.html       # User guide page
├── uploads/             # Temporary video uploads (gitignored)
│   └── .gitkeep         # Keeps empty folder in git
└── output/              # Generated GIFs (gitignored)
    └── .gitkeep         # Keeps empty folder in git
```

**Note:** User files (`uploads/*`, `output/*`, `cache.json`, `.env`) are gitignored and never committed.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application page |
| `/guide` | GET | User guide and documentation |
| `/upload` | POST | Upload video and start processing |
| `/stream/<job_id>` | GET | SSE endpoint for real-time updates |
| `/merge` | POST | Merge selected GIFs |
| `/grayscale` | POST | Convert a GIF to grayscale |
| `/delete` | POST | Delete a GIF file |
| `/jobs` | GET | List all processed jobs |
| `/load/<job_id>` | GET | Load existing job's GIFs |
| `/output/<job_id>/<filename>` | GET | Serve generated GIF files |

## Technologies Used

- **Backend**: Python, Flask
- **Video Processing**: FFmpeg, PySceneDetect
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Real-time Updates**: Server-Sent Events (SSE)

## Troubleshooting

### FFmpeg not found
- Ensure FFmpeg is installed and in your system PATH
- Restart your terminal after installation
- Run `ffmpeg -version` to verify

### GIFs not generating
- Check terminal for error messages
- Ensure video format is supported
- Try a smaller video file first

### Slow processing
- Processing speed depends on video length and system resources
- Consider reducing video resolution before uploading
- SSD storage improves performance

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) first.

### Quick Start

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Make your changes
4. Update `CHANGELOG.md` with your changes
5. Commit your changes (`git commit -m 'feat: add amazing feature'`)
6. Push to the branch (`git push origin feature/AmazingFeature`)
7. Open a Pull Request

### Branch Protection (Recommended for Teams)

If you're forking this for a team project, enable branch protection on GitHub:

```
Settings > Branches > Add rule > "main"
```

Recommended settings:
- [x] Require pull request reviews before merging
- [x] Require status checks to pass before merging
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

This prevents accidental pushes to main and ensures code review.

### For AI Assistants

See [CLAUDE.md](CLAUDE.md) for guidelines on working with this codebase.

## Privacy & Security

**Your data stays local.** Gifomatic processes everything on your machine:

- Videos are deleted immediately after processing
- GIFs are stored locally in `output/` folder
- No data is sent to external servers
- Cache is file-based (`cache.json`), not cloud-synced

**Files that are never committed to git:**
- `uploads/*` - User uploaded videos
- `output/*` - Generated GIFs
- `cache.json` - Processing cache
- All video formats (*.mp4, *.avi, etc.)
- All image formats in root directory

See `.gitignore` and `.dockerignore` for complete exclusion lists.

### Security Features

Gifomatic includes comprehensive security measures:

| Feature | Description |
|---------|-------------|
| **Path Traversal Protection** | All file paths validated against directory escape attempts |
| **UUID Validation** | Job IDs must be valid UUIDs to prevent injection |
| **File Type Validation** | Magic byte checking in addition to extension validation |
| **XSS Prevention** | All user input escaped; DOM manipulation uses safe methods |
| **Rate Limiting** | 10 requests/minute, 3 uploads/minute per IP address |
| **File Size Limit** | Maximum 500MB upload size to prevent DoS |
| **Concurrent Job Limit** | Maximum 5 simultaneous processing jobs |
| **Security Headers** | CSP, X-Frame-Options, X-Content-Type-Options enabled |
| **Error Sanitization** | Error messages don't reveal internal paths or system info |
| **Automatic Cleanup** | Jobs automatically deleted after 24 hours |

### Production Deployment

For production deployments:

1. **Set a secret key** via environment variable:
   ```bash
   export SECRET_KEY="your-secure-random-key-here"
   ```

2. **Use HTTPS** - Deploy behind a reverse proxy (nginx, Caddy) with TLS

3. **Set production mode**:
   ```bash
   export FLASK_ENV=production
   ```

4. **Consider authentication** if exposing publicly (not included by default)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**SV**

Organization: [Call O Buzz Services](https://callobuzz.com)

---

Made with love by COB
