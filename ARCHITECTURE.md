# People Counter - Architecture Documentation

## System Overview

The People Counter is a real-time computer vision application that tracks people crossing a vertical line using webcam input. The system combines deep learning (YOLOv8), multi-object tracking (ByteTrack), and web technologies (FastAPI + WebSocket) to provide a production-ready counting solution.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Web Browser                          │
│  ┌────────────┐  ┌─────────────┐  ┌──────────────────────┐ │
│  │ index.html │  │  main.js    │  │  WebSocket Client    │ │
│  └────────────┘  └─────────────┘  └──────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/WS
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ main.py: REST API + WebSocket Server                   │ │
│  │  - GET /api/stats/current                              │ │
│  │  - GET /api/events                                     │ │
│  │  - POST /api/reset                                     │ │
│  │  - WS /ws (real-time updates)                          │ │
│  └─────────────────┬──────────────────────────────────────┘ │
│                    │                                          │
│  ┌─────────────────▼──────────────────────────────────────┐ │
│  │ Event Queue (asyncio.Queue)                            │ │
│  │  - Thread-safe communication bridge                    │ │
│  └─────────────────┬──────────────────────────────────────┘ │
└────────────────────┼──────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────────┐ ┌─────────┐ ┌──────────┐
│  cv_worker   │ │   db    │ │ schemas  │
│  (Thread)    │ │ (SQLite)│ │ (Models) │
└──────────────┘ └─────────┘ └──────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│  Computer Vision Pipeline                │
│  ┌────────────────────────────────────┐ │
│  │ 1. Camera Capture (OpenCV)         │ │
│  │    cv2.VideoCapture()              │ │
│  └────────────┬───────────────────────┘ │
│               │                          │
│  ┌────────────▼───────────────────────┐ │
│  │ 2. YOLO Detection + Tracking       │ │
│  │    model.track(tracker=bytetrack)  │ │
│  └────────────┬───────────────────────┘ │
│               │                          │
│  ┌────────────▼───────────────────────┐ │
│  │ 3. Line Crossing Counter           │ │
│  │    counter.process_detection()     │ │
│  └────────────┬───────────────────────┘ │
│               │                          │
│  ┌────────────▼───────────────────────┐ │
│  │ 4. Event Publishing                │ │
│  │    callback(event)                 │ │
│  └────────────┬───────────────────────┘ │
│               │                          │
│  ┌────────────▼───────────────────────┐ │
│  │ 5. Debug Window (Optional)         │ │
│  │    cv2.imshow() + keyboard input   │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

## Component Details

### 1. CV Worker (`cv_worker.py`)

**Purpose**: Background thread that handles all computer vision processing.

**Key Responsibilities**:
- Camera initialization and frame capture
- YOLO model loading and inference
- Tracking with ByteTrack
- Line crossing detection
- Debug window rendering
- Event publishing to FastAPI

**Threading Model**:
- Runs in a separate daemon thread
- Uses `threading.Event` for graceful shutdown
- Thread-safe event callback using `asyncio.run_coroutine_threadsafe()`

**Performance Considerations**:
- Frame resizing for speed
- FPS monitoring
- Periodic track cleanup (throttled)

### 2. Counter Logic (`counter.py`)

**Purpose**: Pure logic for tracking people and detecting line crossings.

**Core Algorithm**:

```python
def process_detection(track_id, bbox):
    cx, cy = center_of(bbox)
    side = "L" if cx < line_x else "R"
    
    if track_id is new:
        create_track(track_id, cx, cy, side)
        return None
    
    old_side = track.last_side
    
    if side != old_side:  # Side changed
        if abs(cx - line_x) > hysteresis:  # Far enough from line
            if track.counted_direction != direction:  # Not yet counted
                direction = map_crossing(old_side, side)
                track.counted_direction = direction
                increment_counter(direction)
                return direction
    
    track.update(cx, cy, side)
    return None
```

**State Management**:
- `TrackState` dataclass for each tracked person
- Fields: `track_id`, `last_center_x/y`, `last_side`, `counted_direction`, `last_seen_ts`
- Tracks expire after `max_age_seconds`

**Deduplication Strategy**:
1. Once a track is counted in a direction, it won't be counted again
2. Until the track expires (not seen for `max_age_seconds`)
3. Then if the person returns, they can be counted again

### 3. Database (`db.py`)

**Purpose**: Persistent storage of crossing events.

**Schema**:

```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    track_id INTEGER NOT NULL,
    direction TEXT CHECK(direction IN ('IN', 'OUT'))
);

CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
```

**Threading Safety**:
- Uses `threading.Lock` for write operations
- Connection per operation (SQLite limitation)
- Context manager for automatic connection cleanup

**API**:
- `insert_event(event)`: Store new crossing
- `get_recent_events(limit)`: Fetch N most recent
- `get_stats_today()`: Aggregate counts for today
- `clear_all_events()`: Reset database (use with caution)

### 4. FastAPI Application (`main.py`)

**Purpose**: Web server with REST API and WebSocket support.

**Lifecycle Management**:

```python
@asynccontextmanager
async def lifespan(app):
    # Startup
    cv_worker.start()
    stats_task = create_task(broadcast_stats())
    yield
    # Shutdown
    stats_task.cancel()
    cv_worker.stop()
```

**WebSocket Protocol**:

Messages are JSON with `type` and `data` fields:

```typescript
type WSMessage = 
    | { type: "stats", data: CurrentStats }
    | { type: "event", data: CrossingEvent }
    | { type: "status", data: { message: string } }
```

**Communication Flow**:

```
CV Worker Thread          Event Queue          FastAPI (async)
      │                       │                        │
      ├─ event detected ─────>│                        │
      │                       │<─── queue.get() ───────┤
      │                       ├─────────────────────────>│
      │                       │                        ├─ broadcast to WS clients
```

### 5. Configuration (`config.py`)

**Purpose**: Centralized configuration with environment variable support.

**Features**:
- Pydantic Settings for validation
- Environment variable prefix: `PC_`
- Type checking and default values
- Auto-conversion (e.g., string "true" → bool)

**Example**:

```python
class Settings(BaseSettings):
    camera_index: int = 0
    model_name: str = "yolov8n.pt"
    conf_threshold: float = 0.45
    
    class Config:
        env_prefix = "PC_"
```

### 6. Web Frontend

**Files**:
- `static/index.html`: UI structure
- `static/main.js`: WebSocket client and DOM updates

**Features**:
- Real-time counter updates
- Live event feed with animations
- System status indicators
- Reset button
- Auto-reconnect on disconnect

**WebSocket Client Flow**:

```javascript
ws.onopen = () => {
    loadInitialEvents();  // REST API
};

ws.onmessage = (msg) => {
    const {type, data} = JSON.parse(msg.data);
    
    if (type === "stats") {
        updateCounters(data);
    } else if (type === "event") {
        addEventToList(data);
    }
};

ws.onclose = () => {
    setTimeout(connect, 3000);  // Auto-reconnect
};
```

## Data Flow

### Crossing Event Flow

```
1. Camera captures frame
   ↓
2. YOLOv8 detects person + ByteTrack assigns ID
   ↓
3. Counter checks if crossed line
   ↓
4. If crossed: Generate CrossingEvent
   ↓
5. Save to database (db.insert_event)
   ↓
6. Queue event for WebSocket (event_queue.put)
   ↓
7. FastAPI reads from queue
   ↓
8. Broadcast to all connected WebSocket clients
   ↓
9. Browser updates UI
```

### Stats Update Flow

```
Every 2 seconds:
1. FastAPI task wakes up
   ↓
2. cv_worker.get_status() called
   ↓
3. Counter stats retrieved
   ↓
4. Broadcast to all WebSocket clients
   ↓
5. Browser updates counters/status
```

## Threading Model

The application uses a hybrid threading/async model:

```
Main Thread (FastAPI/asyncio)
├─ HTTP request handlers (async)
├─ WebSocket connections (async)
├─ Periodic stats broadcaster (async task)
└─ Event queue reader (async)

Background Thread (CV Worker)
├─ Camera capture loop (sync)
├─ YOLO inference (sync)
├─ OpenCV rendering (sync)
└─ Event callback (schedules async operation)
```

**Thread Safety**:
- Event queue is asyncio.Queue (thread-safe)
- Database uses threading.Lock
- CV worker state accessed via get_status() (no shared mutable state)

## Performance Characteristics

### Latency

- **Camera to Detection**: ~30-100ms (depends on model)
- **Detection to WebSocket**: ~10-50ms (queue + broadcast)
- **Total end-to-end**: ~50-150ms

### Throughput

- **FPS**: 20-60 depending on:
  - Model size (n/s/m/l/x)
  - Frame resolution
  - CPU/GPU capability
  - Number of people in frame

### Memory Usage

- **Base**: ~500MB (Python + OpenCV + PyTorch)
- **YOLO model**: 6MB (n) to 100MB+ (x)
- **Per track**: ~200 bytes
- **Database**: Grows ~100 bytes per event

## Error Handling

### Camera Failures

```python
if not cap.isOpened():
    camera_status = "offline"
    # Web UI shows offline indicator
    # Continue running, retry possible
```

### Model Loading Failures

```python
try:
    model = YOLO(model_name)
except:
    model_loaded = False
    # API returns error status
    # Application continues (without CV)
```

### WebSocket Disconnects

```javascript
ws.onclose = () => {
    setTimeout(connect, 3000);  // Auto-reconnect
};
```

### Track Loss

- Tracks expire after `max_age_seconds`
- Can be counted again when redetected
- Prevents memory leak from lost tracks

## Security Considerations

### Current Implementation (Prototype)

- No authentication
- No HTTPS
- No input validation on reset endpoint
- Database not encrypted

### Production Recommendations

1. **Add Authentication**:
   - JWT tokens for API access
   - WebSocket authentication
   
2. **Enable HTTPS**:
   - Use reverse proxy (nginx) with SSL
   - Let's Encrypt certificates

3. **Input Validation**:
   - Rate limiting on POST endpoints
   - CORS configuration

4. **Database Security**:
   - User permissions
   - Audit logging
   - Encryption at rest

## Testing Strategy

### Unit Tests

- `test_counter.py`: Pure logic testing
  - Crossing detection
  - Deduplication
  - Hysteresis
  - Track cleanup

### Integration Tests (TODO)

- Database operations
- WebSocket protocol
- API endpoints

### Manual Testing

- Debug window for visual verification
- Multiple people scenarios
- Edge cases (occlusion, fast movement)

## Deployment

### Development

```bash
python run.py --reload
```

### Production

```bash
gunicorn app.main:app \
    -w 1 \
    -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
```

**Important**: Use only 1 worker to avoid multiple CV worker instances.

### Systemd Service

See `README.md` for systemd configuration.

## Future Enhancements

### Potential Features

1. **Multiple Lines**: Support horizontal lines, polygons
2. **Dwell Time**: Track how long people stay in zones
3. **Heatmaps**: Visualize movement patterns
4. **Video Recording**: Save clips of crossing events
5. **Multi-Camera**: Aggregate from multiple sources
6. **Cloud Integration**: Push data to cloud analytics
7. **Alerts**: Notifications on thresholds
8. **Dashboard**: Historical data visualization

### Performance Optimizations

1. **TensorRT**: GPU optimization for inference
2. **Frame Skipping**: Process every Nth frame
3. **ROI Processing**: Only detect in region of interest
4. **Batch Processing**: Process multiple frames at once
5. **Edge Deployment**: Optimize for Raspberry Pi, Jetson

### Code Quality

1. **Type Hints**: Full type coverage
2. **Documentation**: Sphinx docs
3. **CI/CD**: Automated testing and deployment
4. **Code Coverage**: >90% test coverage
5. **Linting**: Strict linting rules

## Troubleshooting

### Common Issues

1. **Camera not opening**:
   - Check device index
   - Verify permissions
   - Test with other apps

2. **Low FPS**:
   - Use smaller model
   - Reduce resolution
   - Enable GPU

3. **False counts**:
   - Adjust confidence threshold
   - Increase hysteresis
   - Improve lighting

4. **Missed counts**:
   - Lower confidence threshold
   - Increase track timeout
   - Better camera angle

### Debug Tools

1. **Debug Window**: Visual verification
2. **Logs**: Console output shows FPS, errors
3. **Health Endpoint**: `/health` for monitoring
4. **Database Queries**: Direct SQLite inspection

## References

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [ByteTrack Paper](https://arxiv.org/abs/2110.06864)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenCV Documentation](https://docs.opencv.org/)

---

**Last Updated**: February 2026
