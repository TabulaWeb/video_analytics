# 🎯 START HERE - People Counter

Welcome! This document will get you counting people in **5 minutes**.

## What You're Getting

A complete, production-ready system that:
- 📹 Connects to your webcam
- 🤖 Detects people with AI (YOLOv8)
- 📊 Counts people crossing a line
- 🌐 Shows results in real-time web interface
- 💾 Saves all events to database

## Prerequisites

✅ Python 3.8-3.11 installed  
✅ Webcam connected  
✅ 500MB free disk space  
✅ Internet connection (first run only)

## 3-Step Quick Start

### Step 1: Install Dependencies

```bash
cd /Users/alextabula/Desktop/vision
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**Wait time**: 2-3 minutes (downloads ~500MB)

### Step 2: Check System

```bash
python check_system.py
```

Should show:
```
✓ Python 3.10.x
✓ All packages installed
✓ Camera accessible
✓ Port 8000 available
```

### Step 3: Run!

```bash
python run.py
```

**That's it!** You should see:
1. 📺 OpenCV window with camera feed
2. 🌐 Web interface at http://localhost:8000
3. 📊 Real-time counting

## First Test

1. **Stand in front of camera** - You'll see a green box around you
2. **Walk across the yellow line** (left to right)
3. **Watch the IN counter increase** on web interface
4. **Walk back** (right to left)
5. **Watch the OUT counter increase**

## Controls

### Keyboard (in OpenCV window)
- `Q` - Quit
- `R` - Reset counters
- `A` - Move line left
- `D` - Move line right

### Web Interface
- Shows live counters
- Shows recent events
- Click "Reset" to clear

## Troubleshooting

### Camera not working?
```bash
# Try different camera
python run.py --camera 1
```

### Too slow?
```bash
# Use faster settings
export PC_RESIZE_WIDTH=640
python run.py
```

### Port 8000 busy?
```bash
python run.py --port 8080
```

## Next Steps

✅ **Working?** Great! Now read:
- [README.md](README.md) - Full documentation
- [ARCHITECTURE.md](ARCHITECTURE.md) - How it works

❌ **Issues?** Check:
- [QUICKSTART.md](QUICKSTART.md) - Detailed setup
- [README.md](README.md) - Troubleshooting section

## Configuration

Want to customize? Create `.env` file:

```bash
cp .env.example .env
# Edit .env with your favorite editor
```

Common settings:
- `PC_CAMERA_INDEX=0` - Which camera to use
- `PC_LINE_X=480` - Line position (pixels from left)
- `PC_DIRECTION_IN=L->R` - Which direction is "IN"

## Project Structure

```
vision/
├── START_HERE.md          ← You are here
├── QUICKSTART.md          ← 5-min detailed guide
├── README.md              ← Full documentation
├── ARCHITECTURE.md        ← Technical details
│
├── run.py                 ← Run this!
├── check_system.py        ← Check before running
├── requirements.txt       ← Dependencies
│
├── app/                   ← Application code
│   ├── main.py           ← FastAPI app
│   ├── cv_worker.py      ← Camera & AI
│   ├── counter.py        ← Counting logic
│   └── static/           ← Web interface
│
└── tests/                 ← Tests
```

## What's Included

✅ YOLOv8 person detection  
✅ ByteTrack tracking  
✅ Line crossing detection  
✅ Web interface (FastAPI)  
✅ Real-time WebSocket  
✅ SQLite database  
✅ Debug window (OpenCV)  
✅ REST API  
✅ Complete documentation  
✅ Unit tests  
✅ Production-ready  

## Need Help?

1. Run system check: `python check_system.py`
2. Read [QUICKSTART.md](QUICKSTART.md)
3. Check [README.md](README.md) troubleshooting
4. Open GitHub issue

## Quick Reference Card

```
┌─────────────────────────────────────────────┐
│         PEOPLE COUNTER QUICK REF            │
├─────────────────────────────────────────────┤
│ INSTALL:   pip install -r requirements.txt  │
│ CHECK:     python check_system.py           │
│ RUN:       python run.py                    │
│ WEB UI:    http://localhost:8000            │
│ API DOCS:  http://localhost:8000/docs       │
├─────────────────────────────────────────────┤
│ KEYBOARD CONTROLS (OpenCV Window)           │
│   Q - Quit                                  │
│   R - Reset counters                        │
│   A - Move line left                        │
│   D - Move line right                       │
├─────────────────────────────────────────────┤
│ USEFUL COMMANDS                             │
│   make install  - Install dependencies      │
│   make check    - System check              │
│   make run      - Run application           │
│   make test     - Run tests                 │
│   make clean    - Clean up files            │
└─────────────────────────────────────────────┘
```

## Typical Setup Time

- ✅ **Install**: 2-3 minutes
- ✅ **Check**: 10 seconds
- ✅ **First Run**: 30 seconds (downloads model)
- ✅ **Subsequent Runs**: Instant

**Total: ~5 minutes from zero to counting!**

---

## 🎉 Ready to Count?

```bash
python run.py
```

Open http://localhost:8000 and watch the magic! ✨

---

**Questions?** Read [README.md](README.md) for complete documentation.  
**Issues?** Check [QUICKSTART.md](QUICKSTART.md) for detailed setup.  
**Curious?** See [ARCHITECTURE.md](ARCHITECTURE.md) for how it works.

**Happy Counting! 🎯**
