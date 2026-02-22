# People Counter - Real-time Person Tracking & Counting

A production-ready system for counting people using webcam, YOLOv8 detection, ByteTrack tracking, and Person Re-Identification (Re-ID).

## Features

- **Real-time Detection**: YOLOv8 person detection with configurable confidence threshold
- **Robust Tracking**: ByteTrack algorithm for consistent person tracking across frames
- **🆕 Person Re-Identification (Re-ID)**: Remember people even after they leave and return (prevents double-counting!)
- **Distance-based Counting**: Count IN when approaching, OUT when moving away from camera
- **Deduplication**: Each person counted only once per direction using Re-ID + track state
- **Web Interface**: Real-time dashboard with WebSocket updates + Re-ID person management
- **Database Logging**: SQLite storage for all crossing events + persistent Re-ID database
- **Debug Window**: OpenCV visualization with person_id display

## System Requirements

- Python 3.8-3.11 (tested on 3.10)
- Webcam or USB camera
- Minimum 4GB RAM (8GB recommended for larger YOLO models)
- CPU or GPU (CUDA-capable GPU recommended for real-time performance)

### Tested Platforms
- macOS (M1/M2/Intel)
- Ubuntu 20.04+
- Windows 10/11

## Installation

### 1. Clone or download this repository

```bash
cd /path/to/vision
```

### 2. Create virtual environment

```bash
python3.10 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

The first run will automatically download the YOLOv8n model (~6MB).

### 4. Verify installation

```bash
python -m app.counter
```

You should see: `✓ Self-check complete!`

## Quick Start

### Run the application

**With Re-ID enabled (recommended):**

```bash
python run.py --no-debug-window
```

Or with custom settings:

```bash
OPENCV_AVFOUNDATION_SKIP_AUTH=1 \
PC_ENABLE_REID=true \
PC_MAX_AGE_SECONDS=30.0 \
python run.py --no-debug-window
```

**Without Re-ID (legacy mode):**

```bash
PC_ENABLE_REID=false python run.py --no-debug-window
```

### Access the web interface

Open your browser and navigate to:

```
http://localhost:8000
```

You'll see:
- Real-time video feed from camera
- Current IN/OUT counters
- Recent crossing events
- 👤 **Known Persons button** (appears when people are detected with Re-ID enabled)

You should see:
- Real-time IN/OUT counters
- Camera and model status
- Live event feed
- Debug window (OpenCV) showing camera feed with annotations

## Configuration

Configure via environment variables with `PC_` prefix or create a `.env` file:

```bash
# Camera settings
export PC_CAMERA_INDEX=0          # Camera device index
export PC_RESIZE_WIDTH=960        # Resize width (0 = no resize)

# Model settings
export PC_MODEL_NAME="yolov8n.pt" # yolov8n/s/m/l/x
export PC_CONF_THRESHOLD=0.45     # Detection confidence
export PC_IOU_THRESHOLD=0.5       # NMS IoU threshold

# Line crossing settings
export PC_LINE_X=480              # Line X position (null = center)
export PC_HYSTERESIS_PX=5         # Anti-jitter threshold
export PC_DIRECTION_IN="L->R"     # or "R->L"

# Distance-based counting
export PC_AREA_CHANGE_THRESHOLD=0.15  # 15% bbox area change to count movement

# Track management
export PC_MAX_AGE_SECONDS=30.0     # Track timeout (30 sec recommended for Re-ID)
export PC_TRACK_CLEANUP_INTERVAL=1.0

# 🆕 Re-ID (Person Re-Identification) settings
export PC_ENABLE_REID=true              # Enable person re-identification
export PC_REID_SIMILARITY_THRESHOLD=0.65  # Match threshold (0.0-1.0)
export PC_REID_MAX_PERSONS=100          # Max persons to remember
export PC_REID_DB_PATH="data/reid_db.pkl"  # Re-ID database path
export PC_REID_UPDATE_EMBEDDINGS=true   # Update embeddings over time

# Database
export PC_DB_PATH="people_counter.db"

# Web server
export PC_HOST="0.0.0.0"
export PC_PORT=8000

# Debug
export PC_SHOW_DEBUG_WINDOW=false  # Set to false for production/headless
```

### Example `.env` file:

```bash
# Create .env file in project root
cat > .env << 'EOF'
OPENCV_AVFOUNDATION_SKIP_AUTH=1
PC_SHOW_DEBUG_WINDOW=false
PC_CAMERA_INDEX=0
PC_CONF_THRESHOLD=0.45
PC_AREA_CHANGE_THRESHOLD=0.15
PC_MAX_AGE_SECONDS=30.0

# Re-ID enabled for long-term memory
PC_ENABLE_REID=true
PC_REID_SIMILARITY_THRESHOLD=0.65
PC_REID_MAX_PERSONS=100
EOF
```

## Debug Window Controls

When `PC_SHOW_DEBUG_WINDOW=true`, an OpenCV window displays with keyboard controls:

- **Q**: Quit application
- **R**: Reset in-memory counters
- **A**: Move line left (10px)
- **D**: Move line right (10px)

## Web API Endpoints

### GET `/api/stats/current`

Returns current statistics:

```json
{
  "in_count": 15,
  "out_count": 12,
  "active_tracks": 3,
  "camera_status": "online",
  "model_loaded": true
}
```

### GET `/api/events?limit=50`

Returns recent crossing events:

```json
[
  {
    "id": 123,
    "timestamp": "2026-02-12T14:30:45.123456",
    "track_id": 42,
    "direction": "IN"
  }
]
```

### POST `/api/reset`

Reset in-memory counters (database events and Re-ID database are preserved):

```json
{
  "success": true,
  "message": "Counters reset successfully (Re-ID database preserved)",
  "new_stats": { ... }
}
```

### 🆕 Re-ID Endpoints

#### GET `/api/reid/persons`

List all known persons:

```json
{
  "count": 3,
  "similarity_threshold": 0.65,
  "persons": [
    {
      "person_id": "P0001",
      "first_seen": 1708012345.678,
      "last_seen": 1708012567.890,
      "appearance_count": 5,
      "track_ids": [42, 87, 123],
      "has_thumbnail": false
    }
  ]
}
```

#### GET `/api/reid/persons/{person_id}`

Get specific person info:

```json
{
  "person_id": "P0001",
  "first_seen": 1708012345.678,
  "last_seen": 1708012567.890,
  "appearance_count": 5,
  "track_ids": [42, 87, 123]
}
```

#### POST `/api/reid/clear`

Clear all known persons from Re-ID database:

```json
{
  "success": true,
  "message": "Re-ID database cleared successfully"
}
```

#### POST `/api/reid/cleanup?max_age_days=7`

Remove persons not seen in N days:

```json
{
  "success": true,
  "removed_count": 3,
  "message": "Removed 3 persons not seen in 7 days"
}
```

### WebSocket `/ws`

Real-time updates with three message types:

#### Stats Update
```json
{
  "type": "stats",
  "data": {
    "in_count": 10,
    "out_count": 8,
    "active_tracks": 2,
    "camera_status": "online",
    "model_loaded": true
  }
}
```

#### Crossing Event
```json
{
  "type": "event",
  "data": {
    "id": 123,
    "timestamp": "2026-02-12T14:30:45.123456",
    "track_id": 42,
    "direction": "IN"
  }
}
```

#### Status Message
```json
{
  "type": "status",
  "data": {
    "message": "Counters reset"
  }
}
```

## How It Works

### Line Crossing Logic

1. **Vertical Line**: A vertical line at `x = line_x` divides the frame
2. **Center Tracking**: Each person's center point `(cx, cy)` is tracked
3. **Side Detection**: Determine if person is left (L) or right (R) of line
4. **Crossing Detection**: When side changes (L→R or R→L), check:
   - Distance from line > `hysteresis_px` (prevents jitter)
   - Direction not already counted for this track
5. **Direction Mapping**:
   - `L→R` = IN (configurable)
   - `R→L` = OUT

### Deduplication Strategy

- Each track maintains state: `counted_direction` (None/IN/OUT)
- Once counted in a direction, won't count again until track is lost
- Tracks expire after `max_age_seconds` without detection
- When track expires, the person can be counted again if they return

### Track Lifecycle

```
Person enters frame → Detection → Track assigned (ID)
                                       ↓
                                 Track state created
                                       ↓
                            Person crosses line (L→R)
                                       ↓
                              Counted as IN, state saved
                                       ↓
                       Person crosses again (jitter/back)
                                       ↓
                            NOT counted (deduplication)
                                       ↓
                              Person leaves frame
                                       ↓
                   Track not seen for max_age_seconds
                                       ↓
                                Track deleted
```

## Performance Optimization

### Model Selection

- **yolov8n.pt**: Fastest, suitable for CPU (~30 FPS on modern CPU)
- **yolov8s.pt**: Balanced speed/accuracy
- **yolov8m.pt**: Better accuracy, needs GPU for real-time
- **yolov8l.pt** / **yolov8x.pt**: Best accuracy, GPU required

### Frame Resize

Reduce frame size for better performance:

```bash
export PC_RESIZE_WIDTH=640  # Lower resolution = faster
```

### GPU Acceleration

Install CUDA-enabled PyTorch (if you have NVIDIA GPU):

```bash
pip uninstall torch torchvision
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

YOLOv8 will automatically use GPU if available.

### Confidence Threshold

Lower confidence = more detections but more false positives:

```bash
export PC_CONF_THRESHOLD=0.35  # Lower for crowded scenes
```

## Troubleshooting

### Camera not opening

```
❌ Failed to open camera 0
```

**Solutions:**
- Check camera index: try `PC_CAMERA_INDEX=1` or `2`
- Verify camera permissions (macOS: System Preferences → Security & Privacy → Camera)
- Test camera with: `ffplay /dev/video0` (Linux) or Photo Booth (macOS)
- On Linux, check: `ls -l /dev/video*`

### Model download fails

```
❌ Model loading error
```

**Solutions:**
- Check internet connection
- Manually download: https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
- Place in `~/.cache/torch/hub/ultralytics_yolov8n/`

### Low FPS / Lag

**Solutions:**
- Use smaller model: `PC_MODEL_NAME="yolov8n.pt"`
- Reduce frame size: `PC_RESIZE_WIDTH=640`
- Lower confidence: `PC_CONF_THRESHOLD=0.5`
- Use GPU (install CUDA PyTorch)
- Close debug window: `PC_SHOW_DEBUG_WINDOW=false`

### WebSocket disconnects

**Solutions:**
- Check firewall settings
- Use `--host 0.0.0.0` to allow external connections
- Check browser console for errors

### Double counting / Missed counts

**Solutions:**
- Adjust hysteresis: `PC_HYSTERESIS_PX=10` (higher = stricter)
- Increase track timeout: `PC_MAX_AGE_SECONDS=3.0`
- Improve lighting conditions
- Position camera to reduce occlusions

## Development

### Run tests

```bash
pytest tests/ -v
```

Or test counter logic:

```bash
python -m app.counter
```

### Project Structure

```
vision/
├── app/
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── counter.py         # Core counting logic + Re-ID integration
│   ├── cv_worker.py       # Camera & YOLO processing
│   ├── db.py              # Database operations
│   ├── reid.py            # 🆕 Person Re-Identification module
│   ├── main.py            # FastAPI application + Re-ID endpoints
│   ├── schemas.py         # Pydantic models
│   ├── utils.py           # Utility functions
│   └── static/
│       ├── index.html     # Web UI + Re-ID panel
│       └── main.js        # WebSocket client + Re-ID management
├── data/
│   └── reid_db.pkl        # 🆕 Re-ID persistent database
├── requirements.txt
├── run.py                 # Convenient launcher script
├── README.md
├── REID_GUIDE.md          # 🆕 Complete Re-ID documentation
├── REID_SUMMARY.md        # 🆕 Re-ID implementation summary
├── DISTANCE_BASED_COUNTING.md  # Distance-based counting docs
└── people_counter.db      # SQLite database (created on first run)
```

## Production Deployment

### Using Gunicorn (Linux/macOS)

```bash
pip install gunicorn
gunicorn app.main:app -w 1 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

**Note:** Use only 1 worker (`-w 1`) to avoid multiple CV worker instances.

### Using systemd (Linux)

Create `/etc/systemd/system/people-counter.service`:

```ini
[Unit]
Description=People Counter Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/vision
Environment="PATH=/path/to/vision/.venv/bin"
ExecStart=/path/to/vision/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable people-counter
sudo systemctl start people-counter
```

### Docker (Optional)

See `Dockerfile` example (TODO: add Dockerfile if needed).

## 🆕 Person Re-Identification (Re-ID)

### What is Re-ID?

Re-ID allows the system to **remember people** even after they leave and return to the camera view. This prevents double-counting when someone temporarily leaves the frame.

### How It Works

```
Without Re-ID:
Person enters → track_id=42 → IN++
Person leaves (2 sec timeout)
Person returns → track_id=87 (NEW) → IN++ again ❌
Result: Double counting!

With Re-ID:
Person enters → track_id=42, person_id=P0001 → IN++
Person leaves (track lost)
Person returns → track_id=87 (new)
→ Re-ID recognizes: "This is P0001!" ✅
→ Already counted → Skip!
Result: Correct counting!
```

### Features

- **Visual Fingerprinting**: Extracts appearance features (color, shape, posture)
- **Persistent Memory**: Database survives restarts
- **Configurable Threshold**: Adjust matching sensitivity (default: 0.65)
- **Web UI Integration**: View/manage known persons
- **API Access**: Full REST API for Re-ID management

### Usage

1. **Enable Re-ID** (enabled by default):
   ```bash
   PC_ENABLE_REID=true python run.py --no-debug-window
   ```

2. **View known persons**:
   - Web UI: Click "👤 Known Persons" button
   - API: `curl http://localhost:8000/api/reid/persons`

3. **Adjust sensitivity** if needed:
   ```bash
   # More strict (fewer false matches)
   PC_REID_SIMILARITY_THRESHOLD=0.75
   
   # More permissive (better recognition in varying conditions)
   PC_REID_SIMILARITY_THRESHOLD=0.55
   ```

### Documentation

- 📖 **`REID_GUIDE.md`** - Complete guide with testing scenarios, API docs, troubleshooting
- 📖 **`REID_SUMMARY.md`** - Implementation summary and technical details
- 📖 **`TRACKING_EXPLAINED.md`** - Comparison of tracking methods

### Limitations

- Works best with consistent appearance (same session/day)
- May not recognize across drastic clothing changes
- Optimal in controlled indoor lighting
- Accuracy: ~85-90% (lighting dependent)

### When to Use

✅ **Use Re-ID when:**
- Need accurate counting with people temporarily leaving view
- Indoor environment with stable lighting
- People stay in area for extended periods
- Double-counting is a concern

❌ **May not need Re-ID when:**
- One-time pass-through counting (e.g., turnstile)
- Very brief appearances (< 2 seconds)
- Outdoor with highly variable lighting

## License

MIT License - Feel free to use in commercial projects.

## Credits

- **YOLOv8**: [Ultralytics](https://github.com/ultralytics/ultralytics)
- **ByteTrack**: [ByteTrack Paper](https://arxiv.org/abs/2110.06864)
- **FastAPI**: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- **Re-ID**: Lightweight implementation using OpenCV + numpy (no deep learning dependencies)

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Happy Counting! 🎯**
