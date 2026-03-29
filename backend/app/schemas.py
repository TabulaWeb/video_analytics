from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────

class AuthRegister(BaseModel):
    email: str
    password: str = Field(min_length=6)
    name: str

class AuthLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserOut(BaseModel):
    id: UUID
    email: str
    name: str
    role: str
    locale: str
    is_active: bool

    class Config:
        from_attributes = True


# ── Camera ────────────────────────────────────────────

class CameraCreate(BaseModel):
    name: str
    ip: Optional[str] = None
    port: int = 554
    username: Optional[str] = None
    password: Optional[str] = None
    channel: int = 1
    subtype: int = 0
    rtsp_url: Optional[str] = None
    line_x: Optional[int] = None
    direction_in: str = "L->R"
    hysteresis_px: int = 5
    processing_mode: str = "local"

class CameraUpdate(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    channel: Optional[int] = None
    subtype: Optional[int] = None
    rtsp_url: Optional[str] = None
    line_x: Optional[int] = None
    direction_in: Optional[str] = None
    hysteresis_px: Optional[int] = None
    processing_mode: Optional[str] = None
    is_active: Optional[bool] = None

class CameraOut(BaseModel):
    id: UUID
    name: str
    ip: Optional[str]
    port: int
    channel: int
    subtype: int
    rtsp_url: Optional[str]
    line_x: Optional[int]
    direction_in: str
    hysteresis_px: int
    processing_mode: str
    stream_key: Optional[str]
    status: str
    last_error: Optional[str]
    last_seen_at: Optional[datetime]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Events ────────────────────────────────────────────

class EventIn(BaseModel):
    camera_id: UUID
    direction: str
    track_id: int
    timestamp: Optional[datetime] = None

class EventBatch(BaseModel):
    events: List[EventIn]

class EventOut(BaseModel):
    id: int
    camera_id: UUID
    direction: str
    track_id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# ── Analytics ─────────────────────────────────────────

class PeriodStats(BaseModel):
    period: str
    start_date: str
    end_date: str
    in_count: int
    out_count: int
    net_flow: int
    total_events: int

class HourlyStats(BaseModel):
    hour: int
    in_count: int
    out_count: int

class DailyStats(BaseModel):
    date: str
    IN: int
    OUT: int

class MonthlyStats(BaseModel):
    month: str
    IN: int
    OUT: int

class WeekdayStats(BaseModel):
    weekday: str
    IN: int
    OUT: int
    total: int

class Averages(BaseModel):
    avg_per_day: float
    avg_per_week: float
    avg_per_month: float

class GrowthTrend(BaseModel):
    week_change_percent: float
    month_change_percent: float
    trend: str

class PeakPrediction(BaseModel):
    predicted_hour: Optional[int]
    hours_until: int
    expected_count: float
    confidence: float


# ── Device ────────────────────────────────────────────

class DeviceRegister(BaseModel):
    name: str
    hardware_id: str

class DeviceOut(BaseModel):
    id: UUID
    name: str
    hardware_id: str
    status: str
    ip_address: Optional[str]
    last_seen_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Camera Log ────────────────────────────────────────

class CameraLogOut(BaseModel):
    id: int
    camera_id: UUID
    level: str
    message: str
    timestamp: datetime

    class Config:
        from_attributes = True
