"""Centralized logging for the app. Logs go to stderr (visible in docker logs)."""
import logging
import os

# Level from env: PC_LOG_LEVEL or LOG_LEVEL (DEBUG, INFO, WARNING, ERROR)
_LOG_LEVEL = os.environ.get("PC_LOG_LEVEL", os.environ.get("LOG_LEVEL", "INFO")).upper()
LEVEL = getattr(logging, _LOG_LEVEL, logging.INFO)

FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FMT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    """Configure root logger. Call once at app startup."""
    logging.basicConfig(
        level=LEVEL,
        format=FORMAT,
        datefmt=DATE_FMT,
    )
    # Reduce noise from third-party libs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module (e.g. __name__)."""
    return logging.getLogger(name)
