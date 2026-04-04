import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Base, engine, SessionLocal, Camera, Event, CameraLog, User, get_db
from app.api import auth, cameras, events, analytics
from app.cv.worker import CVManager
from app.ws.manager import ws_manager
from app.services import analytics as analytics_svc


cv_manager = CVManager()


def _on_cv_event(camera_id: str, direction: str, track_id: int):
    """Callback from server-side CV worker when a line crossing is detected."""
    db = SessionLocal()
    try:
        db.add(Event(
            camera_id=camera_id,
            direction=direction,
            track_id=track_id,
            timestamp=datetime.now(timezone.utc),
        ))
        cam = db.query(Camera).filter(Camera.id == camera_id).first()
        if cam:
            cam.last_seen_at = datetime.now(timezone.utc)
            cam.status = "online"
        db.commit()
    finally:
        db.close()

    asyncio.get_event_loop().call_soon_threadsafe(
        asyncio.ensure_future,
        ws_manager.broadcast("events", {
            "type": "crossing",
            "camera_id": camera_id,
            "direction": direction,
            "track_id": track_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }),
    )


def _on_cv_status(camera_id: str, status: str, message: str):
    db = SessionLocal()
    try:
        cam = db.query(Camera).filter(Camera.id == camera_id).first()
        if cam:
            cam.status = status
            cam.last_error = message if status == "error" else None
            cam.last_seen_at = datetime.now(timezone.utc)
        if message:
            level = "error" if status == "error" else "info"
            db.add(CameraLog(camera_id=camera_id, level=level, message=message))
        db.commit()
    finally:
        db.close()

    asyncio.get_event_loop().call_soon_threadsafe(
        asyncio.ensure_future,
        ws_manager.broadcast("status", {
            "type": "camera_status",
            "camera_id": camera_id,
            "status": status,
            "message": message,
        }),
    )


def _start_server_cameras():
    """Start CV workers for cameras configured with processing_mode='server'."""
    db = SessionLocal()
    try:
        cams = db.query(Camera).filter(
            Camera.processing_mode == "server",
            Camera.is_active.is_(True),
        ).all()
        for cam in cams:
            source = cam.rtsp_url
            if not source and cam.stream_key:
                source = f"{settings.mediamtx_rtsp}/{cam.stream_key}"
            if source:
                cv_manager.start_camera(
                    camera_id=str(cam.id),
                    source_url=source,
                    on_event=_on_cv_event,
                    on_status=_on_cv_status,
                    line_x=cam.line_x or 480,
                    direction_in=cam.direction_in or "L->R",
                    hysteresis_px=cam.hysteresis_px or 5,
                )
    finally:
        db.close()


async def _analytics_broadcaster():
    """Periodically broadcast analytics snapshot to connected web dashboards."""
    while True:
        await asyncio.sleep(30)
        if ws_manager.analytics_count == 0:
            continue
        db = SessionLocal()
        try:
            snapshot = {
                "type": "analytics",
                "data": {
                    "day": analytics_svc.get_period_stats(db, "day"),
                    "week": analytics_svc.get_period_stats(db, "week"),
                    "month": analytics_svc.get_period_stats(db, "month"),
                    "hourly": analytics_svc.get_hourly_stats(db),
                    "daily_range": analytics_svc.get_daily_stats(
                        db,
                        datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0),
                        datetime.now(timezone.utc),
                    ),
                    "averages": analytics_svc.get_averages(db),
                    "growth_trend": analytics_svc.get_growth_trend(db),
                    "predict_peak": analytics_svc.predict_peak_hour(db),
                },
            }
            await ws_manager.broadcast("analytics", snapshot)
        except Exception:
            pass
        finally:
            db.close()


def _ensure_default_admin():
    """Create default admin user if no users exist."""
    from app.services.auth import hash_password
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            from app.models import User as UserModel
            admin = UserModel(
                email="admin@zaga-game.ru",
                password_hash=hash_password("daniil2009"),
                name="Admin",
                role="admin",
            )
            db.add(admin)
            db.commit()
            print("Default admin created: admin@zaga-game.ru")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_default_admin()
    _start_server_cameras()
    task = asyncio.create_task(_analytics_broadcaster())
    yield
    task.cancel()
    cv_manager.stop_all()


app = FastAPI(title="Zaga Analytics", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cameras.router)
app.include_router(events.router)
app.include_router(analytics.router)


# ── WebSocket endpoints ───────────────────────────────

@app.websocket("/ws/{channel}")
async def websocket_endpoint(ws: WebSocket, channel: str = "analytics"):
    if channel not in ("analytics", "events", "status"):
        await ws.close(code=4000)
        return

    await ws_manager.connect(ws, channel)

    if channel == "analytics":
        db = SessionLocal()
        try:
            snapshot = {
                "type": "analytics",
                "data": {
                    "day": analytics_svc.get_period_stats(db, "day"),
                    "week": analytics_svc.get_period_stats(db, "week"),
                    "month": analytics_svc.get_period_stats(db, "month"),
                    "hourly": analytics_svc.get_hourly_stats(db),
                    "averages": analytics_svc.get_averages(db),
                    "growth_trend": analytics_svc.get_growth_trend(db),
                    "predict_peak": analytics_svc.predict_peak_hour(db),
                },
            }
            await ws.send_text(json.dumps(snapshot, default=str))
        except Exception:
            pass
        finally:
            db.close()

    try:
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "ping":
                    await ws.send_text(json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(ws, channel)


# ── Stream management API ─────────────────────────────

@app.post("/api/streams/{camera_id}/start")
def start_stream_processing(
    camera_id: str,
    db: Session = Depends(get_db),
):
    """Start server-side CV processing for a camera."""
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        return {"error": "Camera not found"}

    source = cam.rtsp_url
    if not source and cam.stream_key:
        source = f"{settings.mediamtx_rtsp}/{cam.stream_key}"
    if not source:
        return {"error": "No stream source configured"}

    cv_manager.start_camera(
        camera_id=str(cam.id),
        source_url=source,
        on_event=_on_cv_event,
        on_status=_on_cv_status,
        line_x=cam.line_x or 480,
        direction_in=cam.direction_in or "L->R",
        hysteresis_px=cam.hysteresis_px or 5,
    )
    return {"status": "started"}


@app.post("/api/streams/{camera_id}/stop")
def stop_stream_processing(camera_id: str):
    cv_manager.stop_camera(camera_id)
    return {"status": "stopped"}


@app.get("/api/streams/status")
def stream_statuses():
    return cv_manager.get_all_statuses()


# ── MediaMTX webhooks ─────────────────────────────────

@app.post("/api/streams/webhook/ready")
def on_stream_ready(path: str = Query(...)):
    """Called by MediaMTX when a publisher starts on a path (runOnReady)."""
    stream_key = path.strip("/")
    db = SessionLocal()
    try:
        cam = db.query(Camera).filter(Camera.stream_key == stream_key).first()
        if not cam:
            return {"ignored": True, "reason": "unknown stream_key"}

        cam.status = "online"
        cam.is_active = True
        cam.last_seen_at = datetime.now(timezone.utc)
        db.add(CameraLog(camera_id=cam.id, level="info", message=f"Stream started: {stream_key}"))
        db.commit()

        source = f"{settings.mediamtx_rtsp}/{stream_key}"
        cv_manager.start_camera(
            camera_id=str(cam.id),
            source_url=source,
            on_event=_on_cv_event,
            on_status=_on_cv_status,
            line_x=cam.line_x or 480,
            direction_in=cam.direction_in or "L->R",
            hysteresis_px=cam.hysteresis_px or 5,
        )
        return {"started": True, "camera_id": str(cam.id)}
    finally:
        db.close()


@app.post("/api/streams/webhook/not-ready")
def on_stream_not_ready(path: str = Query(...)):
    """Called by MediaMTX when a publisher disconnects (runOnNotReady)."""
    stream_key = path.strip("/")
    db = SessionLocal()
    try:
        cam = db.query(Camera).filter(Camera.stream_key == stream_key).first()
        if not cam:
            return {"ignored": True}

        cv_manager.stop_camera(str(cam.id))
        cam.status = "offline"
        cam.is_active = False
        db.add(CameraLog(camera_id=cam.id, level="info", message=f"Stream stopped: {stream_key}"))
        db.commit()
        return {"stopped": True, "camera_id": str(cam.id)}
    finally:
        db.close()


# ── Health ────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "ws_connections": ws_manager.total_connections,
        "cv_workers": len(cv_manager.workers),
    }
