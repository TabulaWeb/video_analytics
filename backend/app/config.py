from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_prefix="ZAGA_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_url: str = "postgresql://zaga:zaga@localhost:5432/zaga_analytics"
    secret_key: str = "change-me-in-production-please"
    access_token_expire_minutes: int = 1440  # 24h

    # CV processing
    yolo_model: str = "yolov8n.pt"
    yolo_conf: float = 0.45
    yolo_iou: float = 0.5
    resize_width: int = 960

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "*"

    # MediaMTX (optional, for proxied streams)
    mediamtx_api: str = "http://localhost:9997"
    mediamtx_rtsp: str = "rtsp://localhost:8554"
    mediamtx_hls: str = "http://localhost:8888"


settings = Settings()
