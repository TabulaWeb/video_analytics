#!/bin/bash

# Stop existing backend
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Wait for port to be released
sleep 2

# Start new backend
cd /Users/alextabula/Desktop/vision/backend
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
