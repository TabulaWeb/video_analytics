# Changelog

All notable changes to the People Counter project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-12

### Added
- Initial release of People Counter
- YOLOv8 person detection with configurable models (n/s/m/l/x)
- ByteTrack multi-object tracking
- Vertical line crossing detection with hysteresis
- Deduplication logic to prevent double counting
- SQLite database for event storage
- FastAPI REST API with endpoints:
  - GET `/api/stats/current` - Current statistics
  - GET `/api/events` - Recent crossing events
  - POST `/api/reset` - Reset counters
- WebSocket support for real-time updates
- Web interface with:
  - Real-time IN/OUT counters
  - Live event feed
  - System status indicators
  - Reset functionality
- OpenCV debug window with:
  - Live video feed with annotations
  - Bounding boxes and track IDs
  - Line visualization with direction arrows
  - Keyboard controls (Q/R/A/D)
- Configuration via environment variables (PC_* prefix)
- Automatic track cleanup for stale tracks
- Comprehensive documentation:
  - README.md with full usage guide
  - ARCHITECTURE.md with technical details
  - QUICKSTART.md for new users
- Test suite for counter logic
- System check script (check_system.py)
- Convenient launcher (run.py)
- Cross-platform support (macOS, Linux, Windows)
- Example configuration (.env.example)
- Makefile for common tasks
- MIT License

### Features
- Real-time person detection and tracking
- Configurable counting line position
- Direction mapping (L→R = IN, R→L = OUT)
- Hysteresis to prevent jitter-based false counts
- FPS monitoring and performance stats
- Thread-safe database operations
- Auto-reconnecting WebSocket clients
- Graceful shutdown handling

### Performance
- 20-60 FPS on modern hardware (depending on model and settings)
- ~50-150ms end-to-end latency (camera to WebSocket)
- Memory efficient track management
- Optimized database queries with indexes

### Documentation
- Full API documentation at `/docs` (OpenAPI/Swagger)
- Comprehensive README with troubleshooting
- Architecture documentation
- Quick start guide
- Inline code comments
- Example configurations

### Dependencies
- Python 3.8-3.11
- ultralytics (YOLOv8)
- opencv-python
- numpy
- fastapi
- uvicorn
- websockets
- pydantic
- pydantic-settings

## [Unreleased]

### Planned
- Multiple line support (horizontal, diagonal, polygons)
- Dwell time tracking
- Heatmap visualization
- Video recording of events
- Multi-camera support
- Cloud integration
- Alert system for thresholds
- Historical data dashboard
- TensorRT optimization
- Docker support
- Raspberry Pi / Jetson support

---

## Types of changes
- `Added` for new features.
- `Changed` for changes in existing functionality.
- `Deprecated` for soon-to-be removed features.
- `Removed` for now removed features.
- `Fixed` for any bug fixes.
- `Security` in case of vulnerabilities.
