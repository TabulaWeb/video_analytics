import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.now(timezone.utc)


def new_uuid():
    return uuid.uuid4()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="viewer")  # admin | operator | viewer
    locale = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    rtsp_url = Column(String(512), nullable=True)
    ip = Column(String(45), nullable=True)
    port = Column(Integer, default=554)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    channel = Column(Integer, default=1)
    subtype = Column(Integer, default=0)

    # Processing config per camera
    line_x = Column(Integer, nullable=True)
    direction_in = Column(String(10), default="L->R")
    hysteresis_px = Column(Integer, default=5)

    # Processing mode: "local" = Electron does CV; "server" = backend does CV via stream
    processing_mode = Column(String(20), default="local")

    # Stream path in MediaMTX (for server-side processing)
    stream_key = Column(String(255), nullable=True, unique=True)

    status = Column(String(20), default="offline")  # online | offline | error
    last_error = Column(Text, nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    events = relationship("Event", back_populates="camera", cascade="all, delete-orphan")
    logs = relationship("CameraLog", back_populates="camera", cascade="all, delete-orphan")


class Device(Base):
    """Electron client device registration."""
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name = Column(String(255), nullable=False)
    hardware_id = Column(String(255), unique=True, nullable=False)
    status = Column(String(20), default="offline")
    ip_address = Column(String(45), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_camera_timestamp", "camera_id", "timestamp"),
        Index("ix_events_timestamp", "timestamp"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    direction = Column(String(3), nullable=False)  # IN | OUT
    track_id = Column(Integer, nullable=False)

    camera = relationship("Camera", back_populates="events")


class CameraLog(Base):
    __tablename__ = "camera_logs"
    __table_args__ = (
        Index("ix_camera_logs_camera_ts", "camera_id", "timestamp"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    camera_id = Column(UUID(as_uuid=True), ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(10), nullable=False)  # info | warn | error
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow)

    camera = relationship("Camera", back_populates="logs")
