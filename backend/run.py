import logging
import os

import uvicorn
from app.config import settings

if __name__ == "__main__":
    log_level = os.environ.get("ZAGA_LOG_LEVEL", "DEBUG").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.DEBUG),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    is_dev = os.environ.get("ZAGA_ENV", "dev") == "dev"
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=is_dev,
    )
