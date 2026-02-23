"""Pydantic schemas for API and WebSocket messages."""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field


# ============================================
# Auth Schemas
# ============================================

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Login credentials."""
    username: str
    password: str


# ============================================
# Camera Settings Schemas
# ============================================

class CameraSettingsCreate(BaseModel):
    """Camera settings creation."""
    ip: str
    port: int = 554
    username: str
    password: str = ""  # Default to empty string, required for new settings
    channel: int = 1
    subtype: int = 0
    line_x: Optional[int] = None
    direction_in: Literal["L->R", "R->L"] = "L->R"


class CameraSettingsResponse(BaseModel):
    """Camera settings response."""
    id: int
    ip: str
    port: int
    username: str
    channel: int
    subtype: int
    line_x: Optional[int]
    direction_in: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class CameraSettingsSaveResponse(CameraSettingsResponse):
    """Response after save/update: settings + connection status (200 even if camera unreachable)."""
    camera_connected: bool = True
    message: Optional[str] = None


# ============================================
# Event Schemas
# ============================================

class CrossingEvent(BaseModel):
    """Event when a person crosses the line."""
    id: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    track_id: int
    direction: Literal["IN", "OUT"]
    
    class Config:
        from_attributes = True


# ============================================
# Stats Schemas
# ============================================

class CurrentStats(BaseModel):
    """Current counter statistics."""
    in_count: int = 0
    out_count: int = 0
    active_tracks: int = 0
    camera_status: Literal["online", "offline", "initializing"] = "initializing"
    model_loaded: bool = False
    fps: float = 0.0


class PeriodStats(BaseModel):
    """Statistics for a time period."""
    period: str  # "day", "week", "month"
    start_date: datetime
    end_date: datetime
    in_count: int
    out_count: int
    net_flow: int
    total_events: int


class HourlyStats(BaseModel):
    """Hourly statistics."""
    hour: int
    in_count: int = 0
    out_count: int = 0


class PeakHour(BaseModel):
    """Peak hour data."""
    hour: str
    count: int


# ============================================
# Export Schemas
# ============================================

class ExportRequest(BaseModel):
    """Export data request."""
    format: Literal["csv", "excel", "pdf"]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    include_charts: bool = False


# ============================================
# WebSocket Schemas
# ============================================

class WSMessage(BaseModel):
    """WebSocket message format."""
    type: Literal["stats", "event", "status"]
    data: dict


# ============================================
# Misc Schemas
# ============================================

class ResetResponse(BaseModel):
    """Response for reset endpoint."""
    success: bool
    message: str
    new_stats: CurrentStats


class SystemStatus(BaseModel):
    """System status response."""
    camera_online: bool
    fps: float
    active_tracks: int
    model_loaded: bool
    uptime_seconds: float


# ============================================
# Advanced Analytics Schemas
# ============================================

class PeakHourAnalytics(BaseModel):
    """Average peak hour analytics."""
    peak_hour: Optional[int]
    avg_count: float
    total_count: int


class WeekdayStats(BaseModel):
    """Statistics by day of week."""
    weekday: str
    IN: int
    OUT: int
    total: int


class Averages(BaseModel):
    """Average visitors metrics."""
    avg_per_day: float
    avg_per_week: float
    avg_per_month: float


class GrowthTrend(BaseModel):
    """Growth trend comparison."""
    week_change_percent: float
    month_change_percent: float
    trend: Literal["up", "down", "stable"]


class PeakPrediction(BaseModel):
    """Peak hour prediction."""
    predicted_hour: Optional[int]
    hours_until: int
    expected_count: float
    confidence: float
