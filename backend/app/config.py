"""Configuration management for People Counter application."""
import os
from typing import Literal, Union, Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = ConfigDict(
        env_prefix="PC_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Camera settings
    # For webcam: use 0, 1, 2, etc.
    # For IP camera: use RTSP URL like "rtsp://user:pass@ip:port/path"
    camera_index: Union[int, str] = 0
    resize_width: int = 960  # Resize for performance, 0 = no resize
    
    # Dahua IP Camera settings
    dahua_username: str = "admin"
    dahua_password: str = ""
    dahua_ip: str = "192.168.0.200"
    dahua_port: int = 554
    dahua_channel: int = 1
    dahua_subtype: int = 0  # 0=main stream (HD), 1=sub stream (SD)
    
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
    show_debug_window: bool = True
    
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
