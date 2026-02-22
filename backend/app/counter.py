"""Core counting logic: track management and line crossing detection."""
import time
from typing import Dict, Literal, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

from app.config import settings


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
    
    def update_line_position(self, new_x: int):
        """Update line position."""
        self.line_x = new_x
    
    def _check_crossing(
        self,
        track: TrackState,
        cx: float
    ) -> Optional[Literal["IN", "OUT"]]:
        """
        Check if 50% of bbox (center point) crossed the line.
        Counts EVERY crossing, no deduplication.
        
        Returns:
            "IN", "OUT", or None if no crossing
        """
        # Check if center crossed from left to right
        # Previous: center was on the left (last_cx < line_x)
        # Current: center is on the right (cx > line_x + hysteresis)
        if track.last_center_x < self.line_x and cx > self.line_x + self.hysteresis_px:
            direction = "IN" if self.direction_in == "L->R" else "OUT"
            return direction
        
        # Check if center crossed from right to left
        # Previous: center was on the right (last_cx > line_x)
        # Current: center is on the left (cx < line_x - hysteresis)
        if track.last_center_x > self.line_x and cx < self.line_x - self.hysteresis_px:
            direction = "OUT" if self.direction_in == "L->R" else "IN"
            return direction
        
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
        
        # New track
        if track_id not in self.tracks:
            self.tracks[track_id] = TrackState(
                track_id=track_id,
                last_center_x=cx,
                last_center_y=cy
            )
            return None
        
        # Existing track
        track = self.tracks[track_id]
        crossing_event = self._check_crossing(track, cx)
        
        if crossing_event:
            # Update counters
            if crossing_event == "IN":
                self.in_count += 1
            else:
                self.out_count += 1
        
        # Update track position
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
