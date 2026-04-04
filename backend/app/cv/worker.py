"""Server-side CV worker for processing video streams from cameras.

Handles the business requirement: "just stream to the server and let it analyze".

Key design decisions for stream quality:
- Use RTSP TCP transport (no UDP packet loss)
- Process frames without re-encoding (read raw from decoder)
- Adaptive frame skipping for high-latency streams
- Configurable confidence threshold per camera
"""
import os
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Dict, Optional

import cv2
import numpy as np

from app.cv.counter import LineCrossingCounter

_TRACKER_CFG = os.path.join(os.path.dirname(__file__), "bytetrack.yaml")


class CameraWorker:
    """Processes a single camera stream on the server."""

    def __init__(
        self,
        camera_id: str,
        source_url: str,
        line_x: int = 480,
        direction_in: str = "L->R",
        hysteresis_px: int = 5,
        on_event: Optional[Callable] = None,
        on_status: Optional[Callable] = None,
        conf: float = 0.40,
        iou: float = 0.5,
        resize_width: int = 640,
        target_fps: float = 5,
    ):
        self.camera_id = camera_id
        self.source_url = source_url
        self.on_event = on_event
        self.on_status = on_status
        self.conf = conf
        self.iou = iou
        self.resize_width = resize_width
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps if target_fps > 0 else 0

        self.counter = LineCrossingCounter(line_x, hysteresis_px, direction_in)
        self.model = None
        self.cap: Optional[cv2.VideoCapture] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self.fps = 0.0
        self.status = "initializing"
        self.last_frame: Optional[np.ndarray] = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._stop.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self._stop.set()
        if self.thread:
            self.thread.join(timeout=5)
        if self.cap:
            self.cap.release()
            self.cap = None

    def update_config(self, **kw):
        self.counter.update_config(**kw)

    def _open_capture(self) -> bool:
        """Open video capture with TCP transport for RTSP reliability."""
        try:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|analyzeduration;2000000|probesize;1000000"
            self.cap = cv2.VideoCapture(self.source_url, cv2.CAP_FFMPEG)
            if not self.cap.isOpened():
                self._report_status("error", f"Cannot open stream: {self.source_url}")
                return False
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._report_status("online", "Stream opened")
            return True
        except Exception as e:
            self._report_status("error", str(e))
            return False

    def _load_model(self):
        from ultralytics import YOLO
        model_name = os.environ.get("ZAGA_YOLO_MODEL", "yolov8n.pt")
        self.model = YOLO(model_name)

    def _report_status(self, status: str, message: str = ""):
        self.status = status
        if self.on_status:
            self.on_status(self.camera_id, status, message)

    def _run(self):
        try:
            self._load_model()
        except Exception as e:
            self._report_status("error", f"Model load failed: {e}")
            return

        reconnect_delay = 2
        while self.running and not self._stop.is_set():
            if not self._open_capture():
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 30)
                continue
            reconnect_delay = 2

            frame_count = 0
            fps_start = time.time()
            consecutive_failures = 0
            last_process_time = 0.0
            tracker_cfg = _TRACKER_CFG if os.path.isfile(_TRACKER_CFG) else "bytetrack.yaml"

            while self.running and not self._stop.is_set():
                ret, frame = self.cap.read()
                if not ret:
                    consecutive_failures += 1
                    if consecutive_failures > 30:
                        self._report_status("error", "Stream lost — reconnecting")
                        break
                    time.sleep(0.05)
                    continue
                consecutive_failures = 0

                now = time.time()
                if now - last_process_time < self.frame_interval:
                    continue
                last_process_time = now

                if self.resize_width > 0:
                    h, w = frame.shape[:2]
                    if w != self.resize_width:
                        ratio = self.resize_width / w
                        frame = cv2.resize(frame, (self.resize_width, int(h * ratio)))

                results = self.model.track(
                    frame,
                    persist=True,
                    tracker=tracker_cfg,
                    conf=self.conf,
                    iou=self.iou,
                    classes=[0],
                    verbose=False,
                )

                if results and results[0].boxes is not None and results[0].boxes.id is not None:
                    boxes = results[0].boxes.xyxy.cpu().numpy()
                    ids = results[0].boxes.id.cpu().numpy().astype(int)
                    for box, tid in zip(boxes, ids):
                        direction = self.counter.process(tid, tuple(box))
                        if direction and self.on_event:
                            self.on_event(self.camera_id, direction, int(tid))

                self.last_frame = frame
                frame_count += 1
                elapsed = time.time() - fps_start
                if elapsed >= 1.0:
                    self.fps = frame_count / elapsed
                    frame_count = 0
                    fps_start = time.time()

            if self.cap:
                self.cap.release()
                self.cap = None

        self._report_status("offline", "Worker stopped")


class CVManager:
    """Manages multiple CameraWorker instances for server-side processing."""

    def __init__(self):
        self.workers: Dict[str, CameraWorker] = {}

    def start_camera(
        self,
        camera_id: str,
        source_url: str,
        on_event: Optional[Callable] = None,
        on_status: Optional[Callable] = None,
        **config,
    ):
        if camera_id in self.workers:
            self.workers[camera_id].stop()

        worker = CameraWorker(
            camera_id=camera_id,
            source_url=source_url,
            on_event=on_event,
            on_status=on_status,
            **config,
        )
        self.workers[camera_id] = worker
        worker.start()

    def stop_camera(self, camera_id: str):
        worker = self.workers.pop(camera_id, None)
        if worker:
            worker.stop()

    def stop_all(self):
        for w in self.workers.values():
            w.stop()
        self.workers.clear()

    def get_status(self, camera_id: str) -> Optional[dict]:
        w = self.workers.get(camera_id)
        if not w:
            return None
        return {
            "camera_id": camera_id,
            "status": w.status,
            "fps": w.fps,
            **w.counter.stats(),
        }

    def get_all_statuses(self) -> list:
        return [self.get_status(cid) for cid in self.workers]
