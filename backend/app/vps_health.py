"""VPS stream health-check: HLS playlist and WebRTC endpoint. No camera access in vps mode."""
import asyncio
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional, Tuple

from app.config import settings
from app.logging_config import get_logger
from app.schemas import VpsStreamStatus

logger = get_logger(__name__)


# Exponential backoff (seconds)
VPS_CHECK_INTERVAL_BASE = 1.0
VPS_CHECK_INTERVAL_MAX = 60.0
VPS_CHECK_TIMEOUT = 5.0

_cached_status: Optional[VpsStreamStatus] = None
_last_check_time: float = 0
_backoff_interval: float = VPS_CHECK_INTERVAL_BASE


def _http_get(url: str, timeout: float = VPS_CHECK_TIMEOUT) -> Tuple[int, str, bytes]:
    """Sync GET; returns (status_code, content_type, body)."""
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "PeopleCounter-VPS-Health/1.0")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ct = r.headers.get("Content-Type", "")
        body = r.read()
        return (r.status, ct, body)


async def check_hls_url(url: Optional[str]) -> bool:
    """GET HLS playlist; return True if 200 and looks like m3u8."""
    if not url:
        return False
    try:
        loop = asyncio.get_event_loop()
        status, ct, body = await loop.run_in_executor(None, lambda: _http_get(url))
        if status != 200:
            logger.warning("VPS HLS check failed: url=%s status=%s", url, status)
            return False
        ct_lower = (ct or "").lower()
        text = (body or b"").decode("utf-8", errors="ignore").strip()
        if "mpegurl" in ct_lower or "m3u8" in ct_lower or text.startswith("#EXTM3U"):
            return True
        logger.warning("VPS HLS check: url=%s response is not m3u8", url)
        return False
    except Exception as e:
        logger.warning("VPS HLS check error: url=%s error=%s", url, e)
        return False


async def check_webrtc_url(url: Optional[str]) -> bool:
    """GET WebRTC endpoint (e.g. MediaMTX); 200 or 404 often means endpoint is up."""
    if not url:
        return False
    try:
        loop = asyncio.get_event_loop()
        status, _, _ = await loop.run_in_executor(None, lambda: _http_get(url))
        return status in (200, 404)
    except urllib.error.HTTPError as e:
        ok = e.code in (200, 404)
        if not ok:
            logger.warning("VPS WebRTC check failed: url=%s code=%s", url, e.code)
        return ok
    except Exception as e:
        logger.warning("VPS WebRTC check error: url=%s error=%s", url, e)
        return False


async def get_vps_status() -> VpsStreamStatus:
    """Check VPS HLS and WebRTC; apply exponential backoff on failure."""
    global _cached_status, _last_check_time, _backoff_interval

    hls_url = getattr(settings, "vps_hls_url", None) or None
    webrtc_url = getattr(settings, "vps_webrtc_url", None) or None

    if not hls_url and not webrtc_url:
        logger.debug("VPS status: no HLS/WebRTC URLs configured")
        return VpsStreamStatus(
            status="offline",
            hls_ok=False,
            webrtc_ok=False,
            last_check_utc=datetime.now(timezone.utc).isoformat(),
        )

    hls_ok, webrtc_ok = False, False
    try:
        hls_ok = await check_hls_url(hls_url)
        webrtc_ok = await check_webrtc_url(webrtc_url)
    except Exception as e:
        logger.warning("VPS status check error: %s", e)

    if hls_ok or webrtc_ok:
        reset_backoff()
        status = "live"
        logger.debug("VPS status: live (hls_ok=%s webrtc_ok=%s)", hls_ok, webrtc_ok)
    else:
        increase_backoff()
        status = "offline"
        logger.warning("VPS status: offline (hls_ok=%s webrtc_ok=%s)", hls_ok, webrtc_ok)

    _cached_status = VpsStreamStatus(
        status=status,
        hls_ok=hls_ok,
        webrtc_ok=webrtc_ok,
        last_check_utc=datetime.now(timezone.utc).isoformat(),
    )
    _last_check_time = time.time()
    return _cached_status


def get_backoff_interval() -> float:
    """Return current backoff interval for next check."""
    return min(_backoff_interval, VPS_CHECK_INTERVAL_MAX)


def increase_backoff():
    """Exponential backoff after failed check."""
    global _backoff_interval
    _backoff_interval = min(_backoff_interval * 2, VPS_CHECK_INTERVAL_MAX)


def reset_backoff():
    """Reset backoff after success."""
    global _backoff_interval
    _backoff_interval = VPS_CHECK_INTERVAL_BASE
