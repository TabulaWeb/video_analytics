# Quick Start Guide

Get People Counter running in 5 minutes.

## Step 1: Install Python

You need Python 3.8-3.11 (3.10 recommended).

**Check your version:**
```bash
python3 --version
```

If you don't have Python or have the wrong version:
- **macOS**: `brew install python@3.10`
- **Ubuntu**: `sudo apt install python3.10 python3.10-venv`
- **Windows**: Download from [python.org](https://www.python.org/downloads/)

## Step 2: Create Virtual Environment

```bash
cd /path/to/vision

# Create virtual environment
python3 -m venv .venv

# Activate it
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate     # Windows
```

## Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This will install:
- YOLOv8 (Ultralytics)
- OpenCV
- FastAPI
- And other dependencies (~500MB)

## Step 4: Check System

```bash
python check_system.py
```

This verifies:
- Python version
- All packages installed
- Camera accessible
- GPU available (optional)

## Step 5: Run the Application

```bash
python run.py
```

You should see:
```
People Counter - Starting...
========================================
Host: 0.0.0.0:8000
Camera: 0
Model: yolov8n.pt
Debug window: True
========================================

🌐 Web interface: http://0.0.0.0:8000

✓ Camera initialized: 960x540
Loading YOLO model: yolov8n.pt...
✓ Model loaded successfully
✓ Counter initialized: line_x=480
✓ CV Worker ready
```

## Step 6: Open Web Interface

Open your browser and go to:

```
http://localhost:8000
```

You should see:
- Real-time IN/OUT counters
- System status (camera, model)
- Live event feed

## Step 7: Test It!

1. **Debug Window**: OpenCV window shows camera feed
   - Yellow vertical line = counting line
   - Green/red boxes = detected people
   - Numbers = track IDs

2. **Walk across the line**:
   - Left → Right = IN (green arrow)
   - Right → Left = OUT (red arrow)

3. **Watch the web interface**:
   - Counters update in real-time
   - Events appear in the feed

## Keyboard Controls (Debug Window)

- `Q` - Quit application
- `R` - Reset counters
- `A` - Move line left
- `D` - Move line right

## Common Issues

### Camera not working?

```bash
# Try different camera index
python run.py --camera 1
```

Or set environment variable:
```bash
export PC_CAMERA_INDEX=1
python run.py
```

### Too slow?

Use smaller model:
```bash
python run.py --model yolov8n.pt
```

Or disable debug window:
```bash
python run.py --no-debug-window
```

### Port already in use?

```bash
python run.py --port 8080
```

## Configuration

Create `.env` file:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Camera
PC_CAMERA_INDEX=0
PC_RESIZE_WIDTH=960

# Model
PC_MODEL_NAME=yolov8n.pt
PC_CONF_THRESHOLD=0.45

# Line position
PC_LINE_X=480

# Direction (customize based on your setup)
PC_DIRECTION_IN=L->R  # or R->L
```

## Next Steps

- Read [README.md](README.md) for full documentation
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- Explore API at http://localhost:8000/docs
- Customize configuration in `.env`

## Troubleshooting

### No camera detected

**macOS**: 
- System Preferences → Security & Privacy → Camera
- Allow Terminal/Python

**Linux**:
```bash
ls -l /dev/video*
# Add your user to video group
sudo usermod -a -G video $USER
```

**Windows**:
- Check Camera app works
- Try different camera index

### Model download fails

Download manually:
```bash
wget https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt
mkdir -p ~/.cache/torch/hub/ultralytics
mv yolov8n.pt ~/.cache/torch/hub/ultralytics/
```

### WebSocket not connecting

- Check firewall
- Try http://127.0.0.1:8000 instead of localhost
- Check browser console (F12) for errors

## Getting Help

1. Run system check: `python check_system.py`
2. Check logs in terminal
3. Open issue on GitHub
4. Read full documentation in README.md

---

**Happy Counting! 🎯**
