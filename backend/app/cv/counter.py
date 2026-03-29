"""Line-crossing counter with per-track cooldown to prevent double-counts."""
import time
from dataclasses import dataclass
from typing import Dict, Literal, Optional, Tuple

import numpy as np


@dataclass
class TrackState:
    track_id: int
    last_cx: float
    last_cy: float

    def update(self, cx: float, cy: float):
        self.last_cx = cx
        self.last_cy = cy


class LineCrossingCounter:
    def __init__(
        self,
        line_x: int = 480,
        hysteresis_px: int = 5,
        direction_in: Literal["L->R", "R->L"] = "L->R",
    ):
        self.line_x = line_x
        self.hysteresis_px = hysteresis_px
        self.direction_in = direction_in
        self.tracks: Dict[int, TrackState] = {}
        self.in_count = 0
        self.out_count = 0
        self._calls = 0
        self._last_cross: Dict[int, int] = {}
        self._cooldown = 20

    def update_config(
        self,
        line_x: Optional[int] = None,
        direction_in: Optional[str] = None,
        hysteresis_px: Optional[int] = None,
    ):
        if line_x is not None:
            self.line_x = line_x
        if direction_in and direction_in in ("L->R", "R->L"):
            self.direction_in = direction_in
        if hysteresis_px is not None:
            self.hysteresis_px = max(1, min(100, hysteresis_px))

    def process(
        self,
        track_id: int,
        bbox: Tuple[float, float, float, float],
    ) -> Optional[Literal["IN", "OUT"]]:
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        self._calls += 1

        if track_id not in self.tracks:
            self.tracks[track_id] = TrackState(track_id, cx, cy)
            return None

        track = self.tracks[track_id]

        if self._calls - self._last_cross.get(track_id, -999) < self._cooldown:
            track.update(cx, cy)
            return None

        margin = max(1, min(5, self.hysteresis_px // 2))
        result = None

        if track.last_cx <= self.line_x - margin and cx >= self.line_x + margin:
            result = "IN" if self.direction_in == "L->R" else "OUT"
        elif track.last_cx >= self.line_x + margin and cx <= self.line_x - margin:
            result = "OUT" if self.direction_in == "L->R" else "IN"

        if result:
            self._last_cross[track_id] = self._calls
            if result == "IN":
                self.in_count += 1
            else:
                self.out_count += 1

        track.update(cx, cy)
        return result

    def reset(self):
        self.in_count = 0
        self.out_count = 0
        self.tracks.clear()
        self._last_cross.clear()

    def stats(self) -> dict:
        return {
            "in_count": self.in_count,
            "out_count": self.out_count,
            "active_tracks": len(self.tracks),
        }
