"""Core counting logic: track management and line crossing detection."""
import time
from typing import Dict, Literal, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class TrackState:
    """State information for a tracked person."""
    track_id: int
    last_center_x: float  # Center X of bbox (50% point)
    last_center_y: float
    
    def update_position(self, cx: float, cy: float):
        """Update position and timestamp."""
        self.last_center_x = cx
        self.last_center_y = cy


class LineCrossingCounter:
    """
    Simple crossing counter - counts every line crossing.
    
    The counter tracks people crossing a vertical line using CENTER of bbox (50% point):
    - L→R (Left to Right): IN (configurable) - center must cross from left to right
    - R→L (Right to Left): OUT - center must cross from right to left
    
    Counting logic:
    - For L→R: Previous center on left (cx < line_x), current center on right (cx > line_x + hysteresis)
    - For R→L: Previous center on right (cx > line_x), current center on left (cx < line_x - hysteresis)
    - EVERY crossing is counted, no memory of previous crossings
    
    Features:
    - 50% bbox crossing: balanced accuracy
    - Hysteresis: prevents jitter around line
    - No memory: same person can be counted multiple times
    """
    
    def __init__(
        self,
        line_x: int = None,
        hysteresis_px: int = 5,
        direction_in: Literal["L->R", "R->L"] = "L->R"
    ):
        """
        Args:
            line_x: X coordinate of vertical line (None = center of frame)
            hysteresis_px: Anti-jitter threshold around line
            direction_in: Which direction counts as IN ("L->R" or "R->L")
        """
        self.line_x = line_x
        self.hysteresis_px = hysteresis_px
        self.direction_in = direction_in
        
        self.tracks: Dict[int, TrackState] = {}
        self.in_count = 0
        self.out_count = 0
        # Cooldown: don't count same track again for N process_detection calls (avoids double-count when lenient)
        self._process_calls = 0
        self._last_cross_at_call: Dict[int, int] = {}
        self._cooldown_calls = 20
    
    def update_line_position(self, new_x: int):
        """Update line position."""
        self.line_x = new_x

    def update_direction_in(self, direction_in: Literal["L->R", "R->L"]):
        """Update which direction counts as IN (e.g. switch if only OUT was counting)."""
        self.direction_in = direction_in

    def update_hysteresis(self, hysteresis_px: int):
        """Update how far past the line (px) a person must cross to count. Larger = less sensitive."""
        self.hysteresis_px = max(1, min(100, hysteresis_px))
    
    def _check_crossing(
        self,
        track_id: int,
        track: TrackState,
        cx: float
    ) -> Optional[Literal["IN", "OUT"]]:
        """
        Check if center crossed the line. Uses a small margin (1–5 px) so crossings
        are not missed at low FPS or with fast movement. Cooldown per track is
        enforced in process_detection.
        """
        # Small dead zone so we clearly crossed (not just wobble); cap so high hysteresis doesn't block
        margin = max(1, min(5, self.hysteresis_px // 2))
        # Left to right: was left of line, now right of line
        if track.last_center_x <= self.line_x - margin and cx >= self.line_x + margin:
            return "IN" if self.direction_in == "L->R" else "OUT"
        # Right to left: was right of line, now left of line
        if track.last_center_x >= self.line_x + margin and cx <= self.line_x - margin:
            return "OUT" if self.direction_in == "L->R" else "IN"
        return None
    
    def process_detection(
        self,
        track_id: int,
        bbox: Tuple[float, float, float, float],
        frame: Optional[np.ndarray] = None
    ) -> Optional[Literal["IN", "OUT"]]:
        """
        Process a detection and check for line crossing.
        
        Args:
            track_id: Unique tracker ID
            bbox: Bounding box (x1, y1, x2, y2)
            frame: Full frame image (optional, for compatibility)
            
        Returns:
            "IN", "OUT" if line crossing detected, None otherwise
        """
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        
        self._process_calls += 1
        
        # New track: init and skip (need at least 2 frames with same ID to detect crossing)
        if track_id not in self.tracks:
            self.tracks[track_id] = TrackState(
                track_id=track_id,
                last_center_x=cx,
                last_center_y=cy
            )
            return None
        
        track = self.tracks[track_id]
        # Cooldown: avoid double-count when person wobbles at the line
        if self._process_calls - self._last_cross_at_call.get(track_id, -999) < self._cooldown_calls:
            track.update_position(cx, cy)
            return None
        
        crossing_event = self._check_crossing(track_id, track, cx)
        
        if crossing_event:
            self._last_cross_at_call[track_id] = self._process_calls
            if crossing_event == "IN":
                self.in_count += 1
            else:
                self.out_count += 1
            logger.info(
                "Line crossing: direction=%s track_id=%s line_x=%s position %.0f -> %.0f (total IN=%s OUT=%s)",
                crossing_event, track_id, self.line_x, track.last_center_x, cx,
                self.in_count, self.out_count
            )
        
        track.update_position(cx, cy)
        return crossing_event
    
    
    def reset_counts(self):
        """Reset counters and clear track states."""
        self.in_count = 0
        self.out_count = 0
        self.tracks.clear()
        print("🔄 Counts reset")
    
    def get_stats(self) -> dict:
        """Get current statistics."""
        return {
            "in_count": self.in_count,
            "out_count": self.out_count,
            "active_tracks": len(self.tracks)
        }
    


# Simple self-check
if __name__ == "__main__":
    print("Running LineCrossingCounter self-check...")
    
    counter = LineCrossingCounter(line_x=500, hysteresis_px=10)
    
    # Simulate track moving L->R (should be IN)
    print("\n1. Track moving L->R (should count as IN):")
    result = counter.process_detection(track_id=1, bbox=(400, 100, 450, 200))
    print(f"   Position 1 (x=425): {result}")
    
    result = counter.process_detection(track_id=1, bbox=(550, 100, 600, 200))
    print(f"   Position 2 (x=575): {result}")
    print(f"   Stats: {counter.get_stats()}")
    
    # Simulate track moving R->L (should be OUT)
    print("\n2. Track moving R->L (should count as OUT):")
    result = counter.process_detection(track_id=2, bbox=(600, 150, 650, 250))
    print(f"   Position 1 (x=625): {result}")
    
    result = counter.process_detection(track_id=2, bbox=(400, 150, 450, 250))
    print(f"   Position 2 (x=425): {result}")
    print(f"   Stats: {counter.get_stats()}")
    
    # Test deduplication (same track crosses again)
    print("\n3. Same track crosses again (should NOT count):")
    result = counter.process_detection(track_id=2, bbox=(600, 150, 650, 250))
    print(f"   Position 3 (x=625): {result}")
    print(f"   Stats: {counter.get_stats()}")
    
    print("\n✓ Self-check complete!")
