"""FastAPI application with WebSocket for real-time People Counter."""
import asyncio
from contextlib import asynccontextmanager
from typing import List
import cv2
import queue
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from app.config import settings
from app.schemas import CrossingEvent, CurrentStats, WSMessage, ResetResponse
from app.db import db
from app.cv_worker import CVWorker



# Event queue for communication between CV worker and WebSocket
event_queue: asyncio.Queue = asyncio.Queue()

# Frame queue for video streaming - using threading.Queue for thread-safe access
frame_queue = queue.Queue(maxsize=2)

# CV Worker instance
cv_worker: CVWorker = None

# WebSocket connections
active_connections: List[WebSocket] = []


def on_crossing_event(event: CrossingEvent):
    """
    Callback for CV worker when a crossing event occurs.
    
    This runs in the CV worker thread, so we need to safely
    schedule async operations.
    """
    # Save to database
    event_id = db.insert_event(event)
    event.id = event_id
    
    # Queue for WebSocket broadcast
    try:
        # Put in queue (thread-safe) - schedule the coroutine properly
        loop = asyncio.get_event_loop()
        asyncio.run_coroutine_threadsafe(
            event_queue.put(("event", event)),
            loop
        )
    except RuntimeError:
        # Event loop not available (e.g., during shutdown)
        pass


def on_frame_ready(frame):
    """
    Callback for CV worker when a new frame is ready.
    
    This runs in the CV worker thread.
    """
    try:
        # Using threading.Queue - much simpler!
        # Drop old frame if queue is full
        if frame_queue.full():
            try:
                frame_queue.get_nowait()
            except:
                pass
        
        # Put frame in queue (non-blocking)
        try:
            frame_queue.put_nowait(frame)
        except queue.Full:
            pass  # Frame dropped, not a big deal
    except Exception as e:
        pass  # Ignore errors in frame callback


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle: startup and shutdown."""
    # Startup
    print("🚀 Starting People Counter application...")
    
    global cv_worker
    cv_worker = CVWorker(
        event_callback=on_crossing_event,
        frame_callback=on_frame_ready
    )
    cv_worker.start()
    
    # Start background task to broadcast stats periodically
    stats_task = asyncio.create_task(broadcast_stats_periodically())
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    stats_task.cancel()
    
    if cv_worker:
        cv_worker.stop()
    
    # Close all WebSocket connections
    for connection in active_connections:
        try:
            await connection.close()
        except:
            pass


app = FastAPI(
    title="People Counter",
    description="Real-time people counting with YOLOv8 and ByteTrack",
    version="1.0.0",
    lifespan=lifespan
)


# Mount static files
import os
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface."""
    html_path = os.path.join(static_path, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        return HTMLResponse("""
        <html>
            <head><title>People Counter</title></head>
            <body>
                <h1>People Counter</h1>
                <p>Static files not found. Please ensure app/static/index.html exists.</p>
            </body>
        </html>
        """)


@app.get("/api/stats/current", response_model=CurrentStats)
async def get_current_stats():
    """Get current counter statistics."""
    if cv_worker:
        return cv_worker.get_status()
    else:
        return CurrentStats(camera_status="offline", model_loaded=False)


@app.get("/api/events", response_model=List[CrossingEvent])
async def get_events(limit: int = 50):
    """Get recent crossing events from database."""
    return db.get_recent_events(limit=limit)


@app.post("/api/events/clear")
async def clear_events():
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
async def reset_counters():
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
            new_stats=CurrentStats(camera_status="offline", model_loaded=False)
        )


class CameraSwitchRequest(BaseModel):
    """Request model for camera switching."""
    source: str

@app.post("/api/camera/switch")
async def switch_camera(request: CameraSwitchRequest):
    """
    Switch camera source dynamically.
    
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
                # Wait for client message or event
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                # Handle client messages if needed
            except asyncio.TimeoutError:
                # No message, continue
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
            await asyncio.sleep(2.0)  # Update every 2 seconds
            
            if cv_worker and active_connections:
                stats = cv_worker.get_status()
                message = WSMessage(type="stats", data=stats.model_dump())
                await broadcast_message(message.model_dump())
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Stats broadcast error: {e}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "camera": cv_worker.camera_status if cv_worker else "offline",
        "model_loaded": cv_worker.model_loaded if cv_worker else False
    }


async def generate_frames():
    """Generate video frames for MJPEG streaming."""
    print("🎥 Video stream started")
    frame_count = 0
    
    while True:
        try:
            # Get frame from threading.Queue (run in executor to avoid blocking)
            frame = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: frame_queue.get(timeout=1.0)
            )
            
            frame_count += 1
            if frame_count % 30 == 0:  # Log every 30 frames to reduce spam
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
            # No frame available, wait a bit
            await asyncio.sleep(0.01)
            continue
        except Exception as e:
            print(f"❌ Frame generation error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(0.1)


@app.get("/video_feed")
async def video_feed():
    """Video streaming endpoint."""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False  # Disable reload to avoid issues with CV worker
    )
