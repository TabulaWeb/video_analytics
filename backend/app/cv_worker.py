"""Computer Vision worker: camera capture, detection, tracking, and counting."""
import cv2
import numpy as np
import threading
import time
import asyncio
from typing import Optional, Callable
from queue import Queue

from ultralytics import YOLO

from app.config import settings
from app.counter import LineCrossingCounter
from app.logging_config import get_logger
from app.schemas import CrossingEvent, CurrentStats
from app.utils import Throttler

logger = get_logger(__name__)



class CVWorker:
    """
    Background worker for computer vision processing.
    
    Handles:
    - Camera capture
    - YOLO detection and tracking
    - Line crossing detection
    - Event publishing
    - Debug window rendering
    """
    
    def __init__(self, event_callback: Optional[Callable] = None, frame_callback: Optional[Callable] = None):
        """
        Args:
            event_callback: Function to call when crossing event occurs
            frame_callback: Function to call when frame is ready for streaming
        """
        self.event_callback = event_callback
        self.frame_callback = frame_callback
        
        # Threading control
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Camera and model
        self.cap: Optional[cv2.VideoCapture] = None
        self.model: Optional[YOLO] = None
        self.frame_width = 0
        self.frame_height = 0
        
        # Counter
        self.counter: Optional[LineCrossingCounter] = None
        
        # Status tracking
        self.camera_status = "initializing"
        self.model_loaded = False
        self.fps = 0.0
        self.last_fps_update = time.time()
        self.frame_count = 0
        
        # Cleanup throttler
    
    def start(self):
        """Start the CV worker in a background thread."""
        if self.running:
            return
        
        self.running = True
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop the CV worker and release resources."""
        self.running = False
        self.stop_event.set()
        
        if self.thread:
            self.thread.join(timeout=5.0)
        
        self._release_resources()
    
    def _release_resources(self):
        """Release camera and close windows."""
        if self.cap:
            self.cap.release()
            self.cap = None
        
        if settings.show_debug_window:
            cv2.destroyAllWindows()
    
    def _init_camera(self) -> bool:
        """
        Initialize camera capture.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Set RTSP options for better compatibility with IP cameras
            if isinstance(settings.camera_index, str) and settings.camera_index.startswith('rtsp://'):
                # For RTSP streams, use environment variables to force TCP transport
                import os
                os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;tcp'
                
                # Create VideoCapture with backend specification
                self.cap = cv2.VideoCapture(settings.camera_index, cv2.CAP_FFMPEG)
                
                # Set buffer size to 1 for lower latency
                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            else:
                # For webcams, use default
                self.cap = cv2.VideoCapture(settings.camera_index)
            
            if not self.cap.isOpened():
                logger.error("Failed to open camera: %s", settings.camera_index)
                self.camera_status = "offline"
                return False
            
            # Get frame dimensions
            ret, frame = self.cap.read()
            if not ret:
                logger.error("Failed to read from camera")
                self.camera_status = "offline"
                return False
            
            self.frame_height, self.frame_width = frame.shape[:2]
            
            # Apply resize if configured
            if settings.resize_width > 0 and settings.resize_width != self.frame_width:
                aspect_ratio = self.frame_height / self.frame_width
                self.frame_width = settings.resize_width
                self.frame_height = int(self.frame_width * aspect_ratio)
            
            logger.info("Camera initialized: %sx%s", self.frame_width, self.frame_height)
            self.camera_status = "online"
            return True
            
        except Exception as e:
            logger.exception("Camera initialization error: %s", e)
            self.camera_status = "offline"
            return False
    
    def _init_model(self) -> bool:
        """
        Initialize YOLO model.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Loading YOLO model: %s", settings.model_name)
            self.model = YOLO(settings.model_name)
            self.model_loaded = True
            logger.info("Model loaded successfully")
            return True
            
        except Exception as e:
            logger.exception("Model loading error: %s", e)
            self.model_loaded = False
            return False
    
    def _init_counter(self):
        """Initialize line-crossing counter."""
        # Set line_x to center if not specified
        line_x = settings.line_x if settings.line_x else self.frame_width // 2
        
        self.counter = LineCrossingCounter(
            line_x=line_x,
            hysteresis_px=settings.hysteresis_px,
            direction_in=settings.direction_in
        )
        
        logger.info("Counter initialized: line_x=%s direction=%s", line_x, settings.direction_in)
    
    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Process a single frame: detect, track, count.
        
        Args:
            frame: Input frame
            
        Returns:
            Annotated frame
        """
        # Resize if needed
        if settings.resize_width > 0:
            frame = cv2.resize(frame, (self.frame_width, self.frame_height))
        
        # Run YOLO tracking
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            conf=settings.conf_threshold,
            iou=settings.iou_threshold,
            classes=[0],  # 0 = person in COCO dataset
            verbose=False
        )
        
        # Process detections
        annotated_frame = frame.copy()
        
        if results and results[0].boxes is not None and results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy().astype(int)
            confidences = results[0].boxes.conf.cpu().numpy()
            
            for box, track_id, conf in zip(boxes, track_ids, confidences):
                x1, y1, x2, y2 = box
                
                # Check for crossing (pass frame for Re-ID)
                crossing_direction = self.counter.process_detection(
                    track_id=track_id,
                    bbox=(x1, y1, x2, y2),
                    frame=frame  # Pass frame for Re-ID embedding extraction
                )
                
                # If crossing occurred, trigger callback
                if crossing_direction and self.event_callback:
                    event = CrossingEvent(
                        track_id=track_id,
                        direction=crossing_direction
                    )
                    try:
                        self.event_callback(event)
                    except Exception as e:
                        logger.warning("Event callback error: %s", e)
                
                # Determine color based on crossing event
                if crossing_direction:
                    color = (0, 255, 0) if crossing_direction == "IN" else (0, 0, 255)  # Green for IN, Red for OUT
                else:
                    color = (255, 165, 0)  # Orange for tracking
                
                # Draw bounding box
                cv2.rectangle(
                    annotated_frame,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    color,
                    2
                )
                
                # Draw track ID
                label = f"ID:{track_id}"
                
                if crossing_direction:
                    label += f" ✓{crossing_direction}"
                
                # Draw label background
                (text_width, text_height), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                cv2.rectangle(
                    annotated_frame,
                    (int(x1), int(y1) - text_height - 10),
                    (int(x1) + text_width, int(y1)),
                    (0, 0, 0),
                    -1
                )
                
                # Draw label text
                cv2.putText(
                    annotated_frame,
                    label,
                    (int(x1), int(y1) - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    color,
                    2
                )
        
        
        return annotated_frame
    
    def _draw_ui_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw UI overlay with counters, line, and info."""
        overlay = frame.copy()
        
        # Draw vertical line
        if self.counter and self.counter.line_x:
            line_x = self.counter.line_x
            
            # Main line
            cv2.line(
                overlay,
                (line_x, 0),
                (line_x, self.frame_height),
                (0, 255, 255),  # Cyan
                2
            )
            
            # Direction indicators
            arrow_y = self.frame_height // 2
            arrow_size = 40
            
            # Left side indicator (depends on direction_in setting)
            left_label = "IN" if settings.direction_in == "L->R" else "OUT"
            left_color = (0, 255, 0) if settings.direction_in == "L->R" else (0, 0, 255)
            cv2.arrowedLine(
                overlay,
                (line_x - 60, arrow_y),
                (line_x - 20, arrow_y),
                left_color,
                3,
                tipLength=0.4
            )
            cv2.putText(
                overlay,
                left_label,
                (line_x - 90, arrow_y + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                left_color,
                2
            )
            
            # Right side indicator
            right_label = "OUT" if settings.direction_in == "L->R" else "IN"
            right_color = (0, 0, 255) if settings.direction_in == "L->R" else (0, 255, 0)
            cv2.arrowedLine(
                overlay,
                (line_x + 20, arrow_y),
                (line_x + 60, arrow_y),
                right_color,
                3,
                tipLength=0.4
            )
            cv2.putText(
                overlay,
                right_label,
                (line_x + 70, arrow_y + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                right_color,
                2
            )
        
        # Draw info panel (top-left)
        info_y = 30
        stats = self.counter.get_stats()
        
        info_lines = [
            f"IN: {stats['in_count']}  OUT: {stats['out_count']}",
            f"Active: {stats['active_tracks']}",
            f"FPS: {self.fps:.1f}",
            f"Mode: Line-crossing",
            f"Line: x={self.counter.line_x}" if self.counter else "Line: N/A",
        ]
        
        for i, line in enumerate(info_lines):
            y_pos = info_y + i * 30
            # Background rectangle
            (text_width, text_height), _ = cv2.getTextSize(
                line, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2
            )
            cv2.rectangle(
                overlay,
                (10, y_pos - text_height - 5),
                (20 + text_width, y_pos + 5),
                (0, 0, 0),
                -1
            )
            # Text
            cv2.putText(
                overlay,
                line,
                (15, y_pos),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2
            )
        
        # Controls help (bottom)
        help_text = "Controls: [Q]uit  [R]eset  [A]Left  [D]Right"
        cv2.putText(
            overlay,
            help_text,
            (10, self.frame_height - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )
        
        return overlay
    
    def _handle_keyboard(self) -> bool:
        """
        Handle keyboard input.
        
        Returns:
            False if should quit, True otherwise
        """
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            logger.info("Quit requested")
            return False
        
        elif key == ord('r'):
            logger.info("Resetting counters...")
            self.counter.reset_counts()
        
        elif key == ord('a'):
            # Move line left
            if self.counter and self.counter.line_x:
                new_x = max(10, self.counter.line_x - 10)
                self.counter.update_line_position(new_x)
                logger.debug("Line moved to x=%s", new_x)
        
        elif key == ord('d'):
            # Move line right
            if self.counter and self.counter.line_x:
                new_x = min(self.frame_width - 10, self.counter.line_x + 10)
                self.counter.update_line_position(new_x)
                logger.debug("Line moved to x=%s", new_x)
        
        return True
    
    def _update_fps(self):
        """Update FPS counter."""
        self.frame_count += 1
        elapsed = time.time() - self.last_fps_update
        
        if elapsed >= 1.0:
            self.fps = self.frame_count / elapsed
            self.frame_count = 0
            self.last_fps_update = time.time()
    
    def _run(self):
        """Main worker loop."""
        logger.info("CV Worker starting...")
        
        # Initialize components
        if not self._init_camera():
            logger.warning("CV Worker exiting: camera init failed")
            return
        
        if not self._init_model():
            logger.warning("CV Worker exiting: model init failed")
            return
        
        self._init_counter()
        
        logger.info("CV Worker ready")
        
        # Main processing loop
        while self.running and not self.stop_event.is_set():
            try:
                ret, frame = self.cap.read()
                
                if not ret:
                    logger.warning("Failed to read frame from camera")
                    self.camera_status = "offline"
                    time.sleep(0.1)
                    continue
                
                self.camera_status = "online"
                
                # Process frame
                annotated_frame = self._process_frame(frame)
                
                # Draw UI overlay
                display_frame = self._draw_ui_overlay(annotated_frame)
                
                # Send frame for web streaming
                if self.frame_callback:
                    try:
                        self.frame_callback(display_frame.copy())
                    except Exception as e:
                        logger.debug("Frame callback error: %s", e)
                
                # Show debug window if enabled
                if settings.show_debug_window:
                    cv2.imshow("People Counter", display_frame)
                    
                    if not self._handle_keyboard():
                        break
                
                self._update_fps()
                
            except Exception as e:
                logger.exception("Processing error: %s", e)
                time.sleep(0.1)
        
        logger.info("CV Worker stopped")
        self._release_resources()
    
    def get_status(self) -> CurrentStats:
        """Get current status and statistics."""
        if self.counter:
            stats = self.counter.get_stats()
        else:
            stats = {"in_count": 0, "out_count": 0, "active_tracks": 0}
        
        return CurrentStats(
            in_count=stats["in_count"],
            out_count=stats["out_count"],
            active_tracks=stats["active_tracks"],
            camera_status=self.camera_status,
            model_loaded=self.model_loaded,
            fps=self.fps
        )
    
    def reset_counters(self):
        """Reset in-memory counters."""
        if self.counter:
            self.counter.reset_counts()
