from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models import Event, Camera, User, get_db
from app.schemas import EventBatch, EventOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/batch", status_code=201)
def ingest_batch(
    body: EventBatch,
    db: Session = Depends(get_db),
):
    """Receive a batch of counting events from Electron clients.
    No auth required here — Electron authenticates via device token / API key.
    In production, add device-level auth.
    """
    camera_ids = set()
    for ev in body.events:
        camera_ids.add(ev.camera_id)

    now = datetime.now(timezone.utc)
    for cid in camera_ids:
        cam = db.query(Camera).filter(Camera.id == cid).first()
        if cam:
            cam.status = "online"
            cam.last_seen_at = now
        else:
            db.add(Camera(id=cid, name=f"Camera {str(cid)[:8]}", status="online", last_seen_at=now))
    db.flush()

    objects = []
    for ev in body.events:
        objects.append(Event(
            camera_id=ev.camera_id,
            direction=ev.direction,
            track_id=ev.track_id,
            timestamp=ev.timestamp or now,
        ))
    db.bulk_save_objects(objects)
    db.commit()
    return {"ingested": len(objects)}


@router.get("", response_model=List[EventOut])
def list_events(
    camera_id: Optional[UUID] = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(Event)
    if camera_id:
        q = q.filter(Event.camera_id == camera_id)
    return q.order_by(Event.timestamp.desc()).offset(offset).limit(limit).all()
