# Contributing to People Counter

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, constructive, and professional in all interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug is already reported in Issues
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment info (OS, Python version, etc.)
   - System check output (`python check_system.py`)

### Suggesting Features

1. Check if the feature is already requested
2. Create an issue describing:
   - Use case and motivation
   - Proposed solution
   - Alternative approaches considered
   - Potential drawbacks

### Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes
4. Add tests if applicable
5. Run tests: `make test`
6. Format code: `make format`
7. Run linter: `make lint`
8. Commit with clear message
9. Push and create PR

## Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/people-counter.git
cd people-counter

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
make install

# Install dev dependencies
pip install pytest pytest-cov black flake8 mypy

# Check system
make check
```

## Code Style

- Follow PEP 8
- Use Black formatter: `make format`
- Max line length: 100 characters
- Type hints encouraged (but not required for now)
- Docstrings for public functions/classes
- Comments for complex logic

## Testing

### Run Tests

```bash
# All tests
make test

# With coverage
make coverage

# Counter logic only
make test-counter
```

### Writing Tests

- Place tests in `tests/` directory
- Name files `test_*.py`
- Use pytest conventions
- Aim for >80% coverage

Example:

```python
def test_feature():
    """Test description."""
    # Arrange
    counter = LineCrossingCounter(line_x=500)
    
    # Act
    result = counter.process_detection(...)
    
    # Assert
    assert result == expected
```

## Project Structure

```
vision/
├── app/               # Main application code
│   ├── config.py     # Configuration
│   ├── counter.py    # Core logic
│   ├── cv_worker.py  # CV processing
│   ├── db.py         # Database
│   ├── main.py       # FastAPI app
│   ├── schemas.py    # Data models
│   ├── utils.py      # Utilities
│   └── static/       # Web files
├── tests/            # Test files
├── docs/             # Documentation (if added)
└── requirements.txt  # Dependencies
```

## Commit Messages

Follow conventional commits:

```
feat: add horizontal line support
fix: prevent double counting on jitter
docs: update README with GPU instructions
test: add tests for track cleanup
refactor: simplify crossing detection logic
perf: optimize frame processing
```

## Documentation

- Update README.md for user-facing changes
- Update ARCHITECTURE.md for technical changes
- Add docstrings for new functions/classes
- Update CHANGELOG.md

## Performance

- Profile before optimizing
- Test with real webcam, not just unit tests
- Measure FPS impact
- Consider memory usage

## Areas for Contribution

### Easy
- Documentation improvements
- Bug fixes
- Test coverage
- Code formatting

### Medium
- New configuration options
- UI improvements
- Additional API endpoints
- Performance optimizations

### Hard
- Multiple line support
- Advanced tracking features
- Video recording
- Multi-camera support

## Questions?

Open an issue with the `question` label or reach out to maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🎯
