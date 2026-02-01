# Contributing to Gifomatic

First off, thank you for considering contributing to Gifomatic! It's people like you that make Gifomatic such a great tool.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Style Guidelines](#style-guidelines)
- [Community](#community)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## Getting Started

### Issues

- **Bug Reports**: If you find a bug, please create an issue with a clear description, steps to reproduce, and your environment details.
- **Feature Requests**: Have an idea? Open an issue to discuss it before implementing.
- **Questions**: Use issues for questions about the codebase or usage.

### Before You Start

1. Check existing issues to avoid duplicates
2. For large changes, open an issue first to discuss
3. Fork the repository and create a branch from `main`

## How Can I Contribute?

### Reporting Bugs

A good bug report includes:

```markdown
**Description**: Clear description of the bug

**Steps to Reproduce**:
1. Go to '...'
2. Click on '...'
3. See error

**Expected Behavior**: What should happen

**Actual Behavior**: What actually happens

**Environment**:
- OS: [e.g., Windows 11, macOS 14, Ubuntu 22.04]
- Python Version: [e.g., 3.11]
- FFmpeg Version: [e.g., 6.0]
- Browser: [e.g., Chrome 120]

**Screenshots**: If applicable
```

### Suggesting Enhancements

Enhancement suggestions are welcome! Include:

- Clear use case description
- Why this would be useful to most users
- Possible implementation approach (optional)

### Code Contributions

Good first issues are labeled `good first issue`. These are great starting points!

Areas where help is appreciated:
- Bug fixes
- Documentation improvements
- Test coverage
- Performance optimizations
- Accessibility improvements
- Internationalization (i18n)

## Development Setup

### Prerequisites

- Python 3.8 or higher
- FFmpeg installed and in PATH
- Git

### Local Setup

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/cob-gifomatic.git
cd cob-gifomatic

# Create virtual environment
python -m venv venv

# Activate (choose your platform)
source venv/Scripts/activate  # Windows Git Bash
venv\Scripts\activate         # Windows CMD
source venv/bin/activate      # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Verify FFmpeg
ffmpeg -version

# Run the application
python app.py
```

### Running with Docker

```bash
docker-compose up --build
```

## Pull Request Process

### Branch Naming

Use descriptive branch names:
- `feature/add-gif-filters`
- `fix/upload-timeout-error`
- `docs/update-readme`
- `refactor/cleanup-processor`

### Commit Messages

Follow conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

Examples:
```
feat(settings): add GIF quality presets
fix(upload): handle large file timeout
docs(readme): add Docker instructions
```

### PR Checklist

Before submitting:

- [ ] Code follows the project's style guidelines
- [ ] Self-reviewed my code
- [ ] Added comments for complex logic
- [ ] Updated documentation if needed
- [ ] Updated CHANGELOG.md
- [ ] No new warnings or errors
- [ ] Tested on multiple browsers (if frontend change)
- [ ] Tested responsive design (if UI change)

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Other (describe)

## How Has This Been Tested?
Describe your testing process

## Screenshots (if applicable)

## Checklist
- [ ] My code follows the style guidelines
- [ ] I have updated the documentation
- [ ] I have updated CHANGELOG.md
```

### Review Process

1. Submit PR to `main` branch
2. Automated checks run (if configured)
3. Maintainer reviews the code
4. Address any feedback
5. PR is merged once approved

## Style Guidelines

### Python

- Follow PEP 8
- Use meaningful variable names
- Add docstrings to functions
- Use type hints where helpful
- Keep functions focused and small

```python
def process_video(video_path: str, output_dir: str, settings: dict = None) -> Generator[str, None, None]:
    """
    Process video and yield GIF paths as they're created.

    Args:
        video_path: Path to the input video file
        output_dir: Directory for output GIFs
        settings: Optional dict with processing settings

    Yields:
        Path to each generated GIF
    """
    pass
```

### JavaScript

- ES6+ syntax
- Meaningful function and variable names
- Comment complex logic
- No external frameworks (vanilla JS only)

```javascript
/**
 * Apply a settings preset to the form controls
 * @param {Event} e - Click event from preset button
 */
function applyPreset(e) {
    const preset = e.target.dataset.preset;
    // ...
}
```

### CSS

- Use existing color variables
- Mobile-first responsive design
- Follow BEM-like naming conventions
- Group related properties

```css
/* Component: Settings Panel */
.settings-section {
    /* Layout */
    width: 100%;
    max-width: 700px;

    /* Visual */
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
}
```

### Documentation

- Keep README.md updated
- Update guide.html for user-facing changes
- Update CHANGELOG.md for all changes
- Use clear, concise language

## Community

### Getting Help

- Open an issue for questions
- Check existing issues and documentation first
- Be respectful and patient

### Recognition

Contributors will be recognized in:
- GitHub contributors list
- CHANGELOG.md for significant contributions

---

Thank you for contributing to Gifomatic!
