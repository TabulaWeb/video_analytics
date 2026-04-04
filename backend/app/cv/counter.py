"""Line-crossing counter using side-tracking with hysteresis.

Instead of requiring a single-frame jump across the hysteresis zone, this
counter remembers which SIDE of the line each track is on and fires a
crossing event when the side flips.  Hysteresis prevents jitter: to go
from 'left' to 'right' the center must pass line_x + margin, and vice
versa.  This handles slow walkers who spend several frames inside the zone.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, Literal, Optional

logger = logging.getLogger(__name__)

Side = Literal["left", "right"]


@dataclass
class TrackState:
    track_id: int
    cx: float
    cy: float
    side: Side


class LineCrossingCounter:
    def __init__(
        self,
        line_x: int = 480,
        hysteresis_px: int = 10,
        direction_in: Literal["L->R", "R->L"] = "L->R",
    ):
        self.line_x = line_x
        self.hysteresis_px = hysteresis_px
        self.direction_in = direction_in
        self.tracks: Dict[int, TrackState] = {}
        self.in_count = 0
        self.out_count = 0
        self._calls = 0
        self._cooldown = 30
        self._last_cross: Dict[int, int] = {}

    @property
    def _margin(self) -> int:
        return max(3, self.hysteresis_px)

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
            self.hysteresis_px = max(3, min(100, hysteresis_px))

    def _initial_side(self, cx: float) -> Side:
        return "left" if cx < self.line_x else "right"

    def process(
        self,
        track_id: int,
        bbox: tuple,
    ) -> Optional[Literal["IN", "OUT"]]:
        x1, y1, x2, y2 = bbox[:4]
        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2
        self._calls += 1

        if track_id not in self.tracks:
            side = self._initial_side(cx)
            self.tracks[track_id] = TrackState(track_id, cx, cy, side)
            logger.debug(
                "NEW track=%d cx=%.1f side=%s line_x=%d dir_in=%s",
                track_id, cx, side, self.line_x, self.direction_in,
            )
            return None

        track = self.tracks[track_id]
        margin = self._margin

        if self._calls - self._last_cross.get(track_id, -999) < self._cooldown:
            track.cx = cx
            track.cy = cy
            return None

        new_side = track.side
        if track.side == "left" and cx >= self.line_x + margin:
            new_side = "right"
        elif track.side == "right" and cx <= self.line_x - margin:
            new_side = "left"

        near_line = abs(cx - self.line_x) < 60
        if near_line:
            logger.debug(
                "track=%d cx=%.1f side=%s->%s | line_x=%d margin=%d dir_in=%s",
                track_id, cx, track.side, new_side,
                self.line_x, margin, self.direction_in,
            )

        result = None
        if new_side != track.side:
            if track.side == "left" and new_side == "right":
                result = "IN" if self.direction_in == "L->R" else "OUT"
            else:
                result = "IN" if self.direction_in == "R->L" else "OUT"

            self._last_cross[track_id] = self._calls
            if result == "IN":
                self.in_count += 1
            else:
                self.out_count += 1

            logger.info(
                "CROSSING track=%d %s | cx=%.1f side %s->%s | line_x=%d dir_in=%s | totals IN=%d OUT=%d",
                track_id, result, cx, track.side, new_side,
                self.line_x, self.direction_in, self.in_count, self.out_count,
            )
            track.side = new_side

        track.cx = cx
        track.cy = cy
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
