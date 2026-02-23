"""FastAPI application with WebSocket for real-time People Counter - Extended Version."""
import asyncio
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List
import cv2
import queue
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uvicorn

from app.config import settings
from app.schemas import (
    CrossingEvent, CurrentStats, WSMessage, ResetResponse,
    Token, LoginRequest, CameraSettingsCreate, CameraSettingsResponse,
    PeriodStats, HourlyStats, PeakHour, ExportRequest, SystemStatus,
    PeakHourAnalytics, WeekdayStats, Averages, GrowthTrend, PeakPrediction
)
from app.db import db
from app.cv_worker import CVWorker
from app.auth import authenticate_user, create_access_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES
from app.models import get_db_engine, create_db_session, init_db, Event as DBEvent, CameraSettings as DBCameraSettings
from app import crud
from app import export as export_module


# ============================================
# Database Setup
# ============================================

engine = get_db_engine(db_url=settings.db_url, db_path=settings.db_path)
SessionLocal = create_db_session(engine)
init_db(engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================
# Global State
# ============================================

# Event queue for communication between CV worker and WebSocket
event_queue: asyncio.Queue = asyncio.Queue()

# Frame queue for video streaming - using threading.Queue for thread-safe access
frame_queue = queue.Queue(maxsize=2)

# CV Worker instance
cv_worker: CVWorker = None

# WebSocket connections
active_connections: List[WebSocket] = []

# Application start time
app_start_time = time.time()


# ============================================
# Callbacks
# ============================================

def on_crossing_event(event: CrossingEvent):
    """
    Callback for CV worker when a crossing event occurs.
    
    This runs in the CV worker thread, so we need to safely
    schedule async operations.
    """
    # Save to database using legacy db module (for backward compatibility)
    event_id = db.insert_event(event)
    event.id = event_id
    
    # Queue for WebSocket broadcast
    try:
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(
            event_queue.put(("event", event)),
            loop
        )
    except RuntimeError:
        pass


def on_frame_ready(frame):
    """
    Callback for CV worker when a new frame is ready.
    
    This runs in the CV worker thread.
    """
    try:
        if frame_queue.full():
            try:
                frame_queue.get_nowait()
            except:
                pass
        
        try:
            frame_queue.put_nowait(frame)
        except queue.Full:
            pass
    except Exception as e:
        pass


# ============================================
# Lifespan
# ============================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown."""
    # Startup
    print("🚀 Starting People Counter application...")
    print("⚠️  Camera will not start automatically - configure via Admin Panel")
    
    # Do NOT start CV worker automatically
    # It will be started from Admin Panel after camera settings are configured
    
    # Start background task to broadcast stats periodically
    stats_task = asyncio.create_task(broadcast_stats_periodically())
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    stats_task.cancel()
    
    global cv_worker
    if cv_worker:
        cv_worker.stop()
    
    # Close all WebSocket connections
    for connection in active_connections:
        try:
            await connection.close()
        except:
            pass


# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="People Counter API",
    description="Real-time people counting with YOLOv8, ByteTrack, and advanced analytics",
    version="2.0.0",
    lifespan=lifespan
)

# CORS: allow origins from env (comma-separated) or default localhost
_cors_default = [
    "http://localhost:3000", "http://localhost:3001", "http://localhost:3002",
    "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3002",
]
_cors_env = os.environ.get("CORS_ORIGINS", "").strip()
cors_origins = [o.strip() for o in _cors_env.split(",") if o.strip()] or _cors_default
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount static files (legacy UI)
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


# ============================================
# Auth Endpoints
# ============================================

@app.post("/api/auth/login", response_model=Token)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token."""
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/api/auth/me")
async def get_current_user_info(current_user = Depends(get_current_active_user)):
    """Get current user information."""
    return {"username": current_user.username, "full_name": current_user.full_name}


# ============================================
# Camera Settings Endpoints
# ============================================

@app.get("/api/camera/settings")
async def get_camera_settings(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Get current camera settings."""
    settings = crud.get_camera_settings(db)
    if not settings:
        # Return default settings if none exist
        return {
            "id": 0,
            "ip": "192.168.0.201",
            "port": 554,
            "username": "admin",
            "channel": 1,
            "subtype": 0,
            "line_x": None,
            "direction_in": "L->R",
            "is_active": False,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    return settings


@app.post("/api/camera/settings", response_model=CameraSettingsResponse)
async def create_camera_settings(
    settings_data: CameraSettingsCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Create or update camera settings and restart camera."""
    global cv_worker
    
    settings_dict = settings_data.model_dump()
    new_settings = crud.create_camera_settings(db, settings_dict)
    
    # Build RTSP URL for IP camera
    rtsp_url = (
        f"rtsp://{new_settings.username}:{new_settings.password}"
        f"@{new_settings.ip}:{new_settings.port}"
        f"/cam/realmonitor?channel={new_settings.channel}&subtype={new_settings.subtype}"
    )
    
    # Check if using MediaMTX proxy
    if new_settings.ip == "localhost" or new_settings.ip == "127.0.0.1":
        rtsp_url = f"rtsp://{new_settings.ip}:{new_settings.port}/dahua"
    
    print(f"🔄 Starting camera with: {rtsp_url.replace(new_settings.password, '***')}")
    
    # Stop existing worker
    if cv_worker:
        cv_worker.stop()
        await asyncio.sleep(1)
    
    # Update config with new settings
    settings.camera_index = rtsp_url
    if new_settings.line_x:
        settings.line_x = new_settings.line_x
    settings.direction_in = new_settings.direction_in
    
    # Start new CV worker
    cv_worker = CVWorker(
        event_callback=on_crossing_event,
        frame_callback=on_frame_ready
    )
    cv_worker.start()
    
    # Wait for initialization and check camera status
    await asyncio.sleep(3)
    
    # Check if camera connected successfully
    if cv_worker.camera_status != "online":
        raise HTTPException(
            status_code=503,
            detail=f"Настройки сохранены, но не удалось подключиться к камере. Проверьте IP адрес ({new_settings.ip}:{new_settings.port}), логин и пароль."
        )
    
    return new_settings


@app.put("/api/camera/settings/{settings_id}", response_model=CameraSettingsResponse)
async def update_camera_settings(
    settings_id: int,
    settings_data: CameraSettingsCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Update camera settings and restart camera."""
    global cv_worker
    
    settings_dict = settings_data.model_dump()
    updated_settings = crud.update_camera_settings(db, settings_id, settings_dict)
    if not updated_settings:
        raise HTTPException(status_code=404, detail="Camera settings not found")
    
    # Build RTSP URL for IP camera
    rtsp_url = (
        f"rtsp://{updated_settings.username}:{updated_settings.password}"
        f"@{updated_settings.ip}:{updated_settings.port}"
        f"/cam/realmonitor?channel={updated_settings.channel}&subtype={updated_settings.subtype}"
    )
    
    # Check if using MediaMTX proxy
    if updated_settings.ip == "localhost" or updated_settings.ip == "127.0.0.1":
        rtsp_url = f"rtsp://{updated_settings.ip}:{updated_settings.port}/dahua"
    
    print(f"🔄 Restarting camera with: {rtsp_url.replace(updated_settings.password, '***')}")
    
    # Stop existing worker
    if cv_worker:
        cv_worker.stop()
        await asyncio.sleep(1)
    
    # Update config with new settings
    settings.camera_index = rtsp_url
    if updated_settings.line_x:
        settings.line_x = updated_settings.line_x
    settings.direction_in = updated_settings.direction_in
    
    # Start new CV worker
    cv_worker = CVWorker(
        event_callback=on_crossing_event,
        frame_callback=on_frame_ready
    )
    cv_worker.start()
    
    # Wait for initialization and check camera status
    await asyncio.sleep(3)
    
    # Check if camera connected successfully
    if cv_worker.camera_status != "online":
        raise HTTPException(
            status_code=503,
            detail=f"Настройки обновлены, но не удалось подключиться к камере. Проверьте IP адрес ({updated_settings.ip}:{updated_settings.port}), логин и пароль."
        )
    
    return updated_settings


# ============================================
# System Status Endpoints
# ============================================

@app.get("/api/system/status", response_model=SystemStatus)
async def get_system_status():
    """Get system status."""
    if cv_worker:
        stats = cv_worker.get_status()
        return SystemStatus(
            camera_online=(stats.camera_status == "online"),
            fps=stats.fps,
            active_tracks=stats.active_tracks,
            model_loaded=stats.model_loaded,
            uptime_seconds=time.time() - app_start_time
        )
    else:
        return SystemStatus(
            camera_online=False,
            fps=0.0,
            active_tracks=0,
            model_loaded=False,
            uptime_seconds=0.0
        )


@app.get("/api/stats/current", response_model=CurrentStats)
async def get_current_stats():
    """Get current counter statistics."""
    if cv_worker:
        return cv_worker.get_status()
    else:
        return CurrentStats(camera_status="offline", model_loaded=False, fps=0.0)


# ============================================
# Events Endpoints
# ============================================

@app.get("/api/events", response_model=List[CrossingEvent])
async def get_events(
    limit: int = 50,
    skip: int = 0,
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(get_db)
):
    """Get crossing events from database."""
    db_events = crud.get_events(db, skip=skip, limit=limit, start_date=start_date, end_date=end_date)
    
    # Convert SQLAlchemy models to Pydantic schemas
    return [
        CrossingEvent(
            id=event.id,
            timestamp=event.timestamp,
            track_id=event.track_id,
            direction=event.direction
        )
        for event in db_events
    ]


@app.post("/api/events/clear")
async def clear_events(current_user = Depends(get_current_active_user)):
    """Clear all events from database."""
    try:
        db.clear_all_events()
        return {
            "success": True,
            "message": "All events cleared successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/reset", response_model=ResetResponse)
async def reset_counters(current_user = Depends(get_current_active_user)):
    """Reset in-memory counters (does not clear database)."""
    if cv_worker:
        cv_worker.reset_counters()
        
        # Broadcast reset to all clients
        stats = cv_worker.get_status()
        message = WSMessage(type="status", data={"message": "Counters reset"})
        await broadcast_message(message.model_dump())
        
        return ResetResponse(
            success=True,
            message="Counters reset successfully",
            new_stats=stats
        )
    else:
        return ResetResponse(
            success=False,
            message="CV worker not running",
            new_stats=CurrentStats(camera_status="offline", model_loaded=False, fps=0.0)
        )


# ============================================
# Analytics Endpoints
# ============================================

@app.get("/api/analytics/day", response_model=PeriodStats)
async def get_day_stats(
    date: datetime = None,
    db: Session = Depends(get_db)
):
    """Get statistics for a specific day."""
    if not date:
        date = datetime.now()
    
    start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)
    
    counts = crud.get_event_counts(db, start_date, end_date)
    
    return PeriodStats(
        period="day",
        start_date=start_date,
        end_date=end_date,
        in_count=counts["IN"],
        out_count=counts["OUT"],
        net_flow=counts["IN"] - counts["OUT"],
        total_events=counts["IN"] + counts["OUT"]
    )


@app.get("/api/analytics/week", response_model=PeriodStats)
async def get_week_stats(
    date: datetime = None,
    db: Session = Depends(get_db)
):
    """Get statistics for a specific week."""
    if not date:
        date = datetime.now()
    
    # Start of week (Monday)
    start_date = date - timedelta(days=date.weekday())
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=7)
    
    counts = crud.get_event_counts(db, start_date, end_date)
    
    return PeriodStats(
        period="week",
        start_date=start_date,
        end_date=end_date,
        in_count=counts["IN"],
        out_count=counts["OUT"],
        net_flow=counts["IN"] - counts["OUT"],
        total_events=counts["IN"] + counts["OUT"]
    )


@app.get("/api/analytics/month", response_model=PeriodStats)
async def get_month_stats(
    date: datetime = None,
    db: Session = Depends(get_db)
):
    """Get statistics for a specific month."""
    if not date:
        date = datetime.now()
    
    start_date = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate next month
    if start_date.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1)
    
    counts = crud.get_event_counts(db, start_date, end_date)
    
    return PeriodStats(
        period="month",
        start_date=start_date,
        end_date=end_date,
        in_count=counts["IN"],
        out_count=counts["OUT"],
        net_flow=counts["IN"] - counts["OUT"],
        total_events=counts["IN"] + counts["OUT"]
    )


@app.get("/api/analytics/hourly", response_model=List[HourlyStats])
async def get_hourly_stats(
    date: datetime = None,
    db: Session = Depends(get_db)
):
    """Get hourly statistics for a specific day."""
    hourly_data = crud.get_hourly_stats(db, date)
    
    return [
        HourlyStats(hour=h["hour"], in_count=h["IN"], out_count=h["OUT"])
        for h in hourly_data
    ]


@app.get("/api/analytics/peak-hours", response_model=List[PeakHour])
async def get_peak_hours(
    start_date: datetime = None,
    end_date: datetime = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get peak hours with most activity."""
    if not start_date:
        start_date = datetime.now() - timedelta(days=7)
    if not end_date:
        end_date = datetime.now()
    
    peak_data = crud.get_peak_hours(db, start_date, end_date, limit)
    
    return [PeakHour(hour=p["hour"], count=p["count"]) for p in peak_data]


@app.get("/api/analytics/daily", response_model=List[dict])
async def get_daily_stats_range(
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(get_db)
):
    """Get daily statistics for a date range."""
    if not start_date or not end_date:
        # Default to full current month (from 1st to last day)
        now = datetime.now()
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Get last day of current month
        if now.month == 12:
            end_date = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
        else:
            next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = next_month - timedelta(seconds=1)
    
    return crud.get_daily_stats(db, start_date, end_date)


@app.get("/api/analytics/monthly", response_model=List[dict])
async def get_monthly_stats_range(
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(get_db)
):
    """Get monthly statistics for a date range."""
    if not start_date or not end_date:
        # Default to full current year (from January to December)
        now = datetime.now()
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    
    return crud.get_monthly_stats(db, start_date, end_date)


@app.get("/api/analytics/peak-hour-avg", response_model=PeakHourAnalytics)
async def get_average_peak_hour(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get average peak hour across multiple days. """
    return crud.get_average_peak_hour(db, days)


@app.get("/api/analytics/weekday-stats", response_model=List[WeekdayStats])
async def get_weekday_statistics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get activity statistics by day of week."""
    return crud.get_weekday_stats(db, days)


@app.get("/api/analytics/averages", response_model=Averages)
async def get_average_metrics(
    db: Session = Depends(get_db)
):
    """Get average visitors per day/week/month."""
    return crud.get_averages(db)


@app.get("/api/analytics/growth-trend", response_model=GrowthTrend)
async def get_growth_trend_analysis(
    db: Session = Depends(get_db)
):
    """Get growth trend comparing current vs previous periods."""
    return crud.get_growth_trend(db)


@app.get("/api/analytics/predict-peak", response_model=PeakPrediction)
async def predict_next_peak(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Predict next peak hour based on historical data."""
    return crud.predict_peak_hour(db, days)


# ============================================
# Export Endpoints
# ============================================

@app.post("/api/export")
async def export_data(
    request: ExportRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_user)
):
    """Export data in requested format."""
    # Get events
    db_events = crud.get_events(
        db,
        skip=0,
        limit=10000,
        start_date=request.start_date,
        end_date=request.end_date
    )
    
    # Convert to dict format
    events = [
        {
            "id": e.id,
            "timestamp": e.timestamp,
            "track_id": e.track_id,
            "direction": e.direction
        }
        for e in db_events
    ]
    
    # Get statistics
    counts = crud.get_event_counts(db, request.start_date, request.end_date)
    stats = {
        "in_count": counts["IN"],
        "out_count": counts["OUT"],
        "total_events": counts["IN"] + counts["OUT"]
    }
    
    # Generate export based on format
    if request.format == "csv":
        data = export_module.export_to_csv(events)
        media_type = "text/csv"
        filename = f"people_counter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    elif request.format == "excel":
        data = export_module.export_to_excel(events, stats)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"people_counter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    elif request.format == "pdf":
        # Get hourly stats if charts requested
        hourly_stats = None
        if request.include_charts:
            hourly_stats_data = crud.get_hourly_stats(db, request.start_date)
            hourly_stats = [{"hour": h["hour"], "IN": h["IN"], "OUT": h["OUT"]} for h in hourly_stats_data]
        
        data = export_module.export_to_pdf(events, stats, hourly_stats)
        media_type = "application/pdf"
        filename = f"people_counter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    else:
        raise HTTPException(status_code=400, detail="Invalid export format")
    
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============================================
# Legacy Endpoints (backward compatibility)
# ============================================

class CameraSwitchRequest(BaseModel):
    """Request model for camera switching."""
    source: str


@app.post("/api/camera/switch")
async def switch_camera(request: CameraSwitchRequest):
    """
    Switch camera source dynamically (legacy endpoint).
    
    Args:
        request.source: 'webcam' for local webcam (0) or 'dahua' for IP camera
    """
    source = request.source
    global cv_worker
    
    try:
        # Determine camera_index based on source
        if source == "webcam":
            new_camera_index = 0
        elif source == "dahua":
            new_camera_index = settings.get_dahua_rtsp_url()
        else:
            return {"success": False, "message": f"Неизвестный источник: {source}"}
        
        print(f"🔄 Switching camera to: {source} ({new_camera_index})")
        
        # Stop current worker
        if cv_worker:
            cv_worker.stop()
        
        # Temporarily override camera_index
        original_camera_index = settings.camera_index
        settings.camera_index = new_camera_index
        
        # Create new worker with new camera
        cv_worker = CVWorker(
            event_callback=on_crossing_event,
            frame_callback=on_frame_ready
        )
        
        # Start new worker
        cv_worker.start()
        
        # Wait a bit for camera to initialize
        await asyncio.sleep(2)
        
        # Check if camera is online
        if cv_worker.camera_status == "online":
            print(f"✓ Camera switched to: {source}")
            return {
                "success": True,
                "message": f"Переключено на: {source}",
                "camera_index": str(new_camera_index) if source == "dahua" else new_camera_index
            }
        else:
            print(f"✗ Failed to switch to: {source}")
            # Restore original camera on failure
            settings.camera_index = original_camera_index
            cv_worker.stop()
            cv_worker = CVWorker(
                event_callback=on_crossing_event,
                frame_callback=on_frame_ready
            )
            cv_worker.start()
            return {
                "success": False,
                "message": f"Не удалось подключиться к {source}. Проверьте настройки камеры."
            }
    
    except Exception as e:
        print(f"✗ Error switching camera: {e}")
        return {"success": False, "message": f"Ошибка: {str(e)}"}


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface (legacy)."""
    html_path = os.path.join(static_path, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        return HTMLResponse("""
        <html>
            <head><title>People Counter API</title></head>
            <body>
                <h1>People Counter API</h1>
                <p>API is running. Access the admin panel at <a href="http://localhost:3000">localhost:3000</a></p>
                <p>API documentation: <a href="/docs">/docs</a></p>
            </body>
        </html>
        """)


# ============================================
# WebSocket Endpoints
# ============================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # Send initial stats
        if cv_worker:
            stats = cv_worker.get_status()
            message = WSMessage(type="stats", data=stats.model_dump())
            await websocket.send_json(message.model_dump())
        
        # Listen for messages (keep connection alive)
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                pass
            
            # Check for events in queue
            try:
                event_type, event_data = event_queue.get_nowait()
                
                if event_type == "event":
                    message = WSMessage(
                        type="event",
                        data=event_data.model_dump()
                    )
                    await broadcast_message(message.model_dump())
                
            except asyncio.QueueEmpty:
                pass
            
            await asyncio.sleep(0.01)
    
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast_message(message: dict):
    """Broadcast message to all connected WebSocket clients."""
    disconnected = []
    
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except:
            disconnected.append(connection)
    
    # Remove disconnected clients
    for connection in disconnected:
        if connection in active_connections:
            active_connections.remove(connection)


async def broadcast_stats_periodically():
    """Periodically broadcast current statistics to all clients."""
    while True:
        try:
            await asyncio.sleep(2.0)
            
            if cv_worker and active_connections:
                stats = cv_worker.get_status()
                message = WSMessage(type="stats", data=stats.model_dump())
                await broadcast_message(message.model_dump())
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Stats broadcast error: {e}")


# ============================================
# Video Streaming
# ============================================

async def generate_frames():
    """Generate video frames for MJPEG streaming."""
    print("🎥 Video stream started")
    frame_count = 0
    
    while True:
        try:
            frame = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: frame_queue.get(timeout=1.0)
            )
            
            frame_count += 1
            if frame_count % 30 == 0:
                print(f"📹 Streaming frame #{frame_count}")
            
            # Encode frame as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                print("❌ Failed to encode frame")
                continue
            
            # Yield frame in multipart format
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        except queue.Empty:
            await asyncio.sleep(0.01)
            continue
        except Exception as e:
            print(f"❌ Frame generation error: {e}")
            await asyncio.sleep(0.1)


@app.get("/video_feed")
async def video_feed():
    """Video streaming endpoint."""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ============================================
# Health Check
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "camera": cv_worker.camera_status if cv_worker else "offline",
        "model_loaded": cv_worker.model_loaded if cv_worker else False,
        "uptime": time.time() - app_start_time
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main_new:app",
        host=settings.host,
        port=settings.port,
        reload=False
    )
