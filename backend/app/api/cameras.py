import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import Camera, CameraLog, User, get_db
from app.schemas import CameraCreate, CameraUpdate, CameraOut, CameraLogOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/cameras", tags=["cameras"])


@router.get("", response_model=List[CameraOut])
def list_cameras(
    active_only: bool = False,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    q = db.query(Camera)
    if active_only:
        q = q.filter(Camera.is_active.is_(True))
    return q.order_by(Camera.created_at).all()


@router.post("", response_model=CameraOut, status_code=201)
def create_camera(
    body: CameraCreate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cam = Camera(**body.model_dump())
    cam.stream_key = f"cam_{uuid.uuid4().hex[:12]}"
    db.add(cam)
    db.commit()
    db.refresh(cam)
    return cam


@router.get("/{camera_id}", response_model=CameraOut)
def get_camera(
    camera_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    return cam


@router.put("/{camera_id}", response_model=CameraOut)
def update_camera(
    camera_id: uuid.UUID,
    body: CameraUpdate,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")

    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "password" and not value:
            continue
        setattr(cam, key, value)

    db.commit()
    db.refresh(cam)
    return cam


@router.delete("/{camera_id}", status_code=204)
def delete_camera(
    camera_id: uuid.UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    cam = db.query(Camera).filter(Camera.id == camera_id).first()
    if not cam:
        raise HTTPException(status_code=404, detail="Camera not found")
    db.delete(cam)
    db.commit()


@router.get("/{camera_id}/logs", response_model=List[CameraLogOut])
def get_camera_logs(
    camera_id: uuid.UUID,
    limit: int = 50,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return (
        db.query(CameraLog)
        .filter(CameraLog.camera_id == camera_id)
        .order_by(CameraLog.timestamp.desc())
        .limit(limit)
        .all()
    )
