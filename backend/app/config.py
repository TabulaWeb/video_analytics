"""Configuration management for People Counter application."""
import os
from typing import Literal, Union, Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict, Field, AliasChoices


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(
        env_prefix="PC_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # --- Stream mode: local (camera/RTSP) or vps (HLS/WebRTC from VPS) ---
    stream_mode: Literal["local", "vps"] = Field(default="local", validation_alias=AliasChoices("STREAM_MODE", "PC_STREAM_MODE"))
    
    # Camera settings (used when stream_mode=local)
    # For webcam: use 0, 1, 2, etc.
    # For IP camera: use RTSP URL like "rtsp://user:pass@ip:port/path"
    camera_index: Union[int, str] = 0
    resize_width: int = 960  # Resize for performance, 0 = no resize
    
    # Dahua IP Camera settings (local mode; no hardcoded IP in code — can override via ENV)
    dahua_username: str = "admin"
    dahua_password: str = ""
    dahua_ip: str = "192.168.0.200"
    dahua_port: int = 554
    dahua_channel: int = 1
    dahua_subtype: int = 0  # 0=main stream (HD), 1=sub stream (SD)
    
    # VPS stream (used when stream_mode=vps). Camera pushes RTMP to VPS; we only consume HLS/WebRTC.
    vps_hls_url: Optional[str] = Field(None, validation_alias=AliasChoices("VPS_HLS_URL", "PC_VPS_HLS_URL"))
    vps_webrtc_url: Optional[str] = Field(None, validation_alias=AliasChoices("VPS_WEBRTC_URL", "PC_VPS_WEBRTC_URL"))
    stream_preferred_protocol: Literal["webrtc", "hls"] = Field("webrtc", validation_alias=AliasChoices("STREAM_PREFERRED_PROTOCOL", "PC_STREAM_PREFERRED_PROTOCOL"))
    # Run line-counting from HLS in VPS mode. Default false to avoid OOM on small VPS; set true if you have ~2GB+ RAM.
    vps_analysis_enabled: bool = Field(False, validation_alias=AliasChoices("VPS_ANALYSIS_ENABLED", "PC_VPS_ANALYSIS_ENABLED"))
    
    # YOLO model settings
    model_name: str = "yolov8n.pt"  # yolov8n/s/m/l/x
    conf_threshold: float = 0.45
    iou_threshold: float = 0.5
    
    # Line crossing settings
    line_x: Optional[int] = None  # X position of vertical line (None = center)
    hysteresis_px: int = 5  # Anti-jitter threshold around line
    direction_in: Literal["L->R", "R->L"] = "L->R"  # Which direction is IN
    
    # Database
    db_url: Optional[str] = None  # PostgreSQL URL (e.g., postgresql://user:pass@host:port/db)
    db_path: str = "people_counter.db"  # SQLite path (fallback if db_url not set)
    
    # Web server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Debug window
    show_debug_window: bool = False  # True needs DISPLAY (no headless/Docker)
    
    def get_dahua_rtsp_url(self) -> str:
        """Build RTSP URL for Dahua camera from settings."""
        # If using localhost (MediaMTX proxy), use simple path
        if self.dahua_ip == "localhost" or self.dahua_ip == "127.0.0.1":
            url = f"rtsp://{self.dahua_ip}:{self.dahua_port}/dahua"
            print(f"📹 Generated RTSP URL (via MediaMTX): {url}")
        else:
            # Direct camera connection
            url = (
                f"rtsp://{self.dahua_username}:{self.dahua_password}"
                f"@{self.dahua_ip}:{self.dahua_port}"
                f"/cam/realmonitor?channel={self.dahua_channel}&subtype={self.dahua_subtype}"
            )
            # For debugging - show URL with masked password
            masked_url = url.replace(self.dahua_password, "***") if self.dahua_password else url
            print(f"📹 Generated RTSP URL (direct): {masked_url}")
        
        return url


# Global settings instance
settings = Settings()
