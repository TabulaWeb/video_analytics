"""Simple centroid-distance tracker for close-up camera scenarios.

ByteTrack relies on IoU (bounding-box overlap) to match detections across
frames.  When a person fills most of the frame (close-up entrance camera),
the bbox shifts so much between frames that IoU drops below any reasonable
threshold.

This tracker matches detections by Euclidean distance between centroids,
which remains small even when the bbox shape changes dramatically.
"""
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class CentroidTracker:
    """Match detections across frames using centroid distance."""

    def __init__(self, max_distance: float = 150, max_lost: int = 20):
        self._next_id = 1
        self._centers: Dict[int, np.ndarray] = {}
        self._lost: Dict[int, int] = {}
        self.max_distance = max_distance
        self.max_lost = max_lost

    def update(
        self, boxes: np.ndarray
    ) -> List[Tuple[int, Tuple[float, float, float, float]]]:
        """Match new detections to existing tracks.

        Args:
            boxes: Nx4 array [[x1, y1, x2, y2], ...].

        Returns:
            List of (track_id, (x1, y1, x2, y2)) for every matched +
            newly-created track.
        """
        if len(boxes) == 0:
            self._age_lost()
            return []

        det_centers = np.array([
            [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2] for b in boxes
        ])

        if not self._centers:
            return self._register_all(boxes, det_centers)

        track_ids = list(self._centers.keys())
        track_pts = np.array([self._centers[t] for t in track_ids])

        dist = np.linalg.norm(
            track_pts[:, None, :] - det_centers[None, :, :], axis=2
        )

        matched_t: set = set()
        matched_d: set = set()
        results: List[Tuple[int, Tuple[float, float, float, float]]] = []

        order = np.argsort(dist, axis=None)
        for flat_idx in order:
            ti, di = np.unravel_index(flat_idx, dist.shape)
            if dist[ti, di] > self.max_distance:
                break
            if ti in matched_t or di in matched_d:
                continue

            tid = track_ids[int(ti)]
            self._centers[tid] = det_centers[int(di)]
            self._lost[tid] = 0
            results.append((tid, tuple(boxes[int(di)])))
            matched_t.add(ti)
            matched_d.add(di)

        for di in range(len(boxes)):
            if di not in matched_d:
                tid = self._next_id
                self._next_id += 1
                self._centers[tid] = det_centers[di]
                self._lost[tid] = 0
                results.append((tid, tuple(boxes[di])))

        for ti in range(len(track_ids)):
            if ti not in matched_t:
                tid = track_ids[ti]
                self._lost[tid] = self._lost.get(tid, 0) + 1
                if self._lost[tid] > self.max_lost:
                    del self._centers[tid]
                    del self._lost[tid]

        return results

    def _register_all(
        self, boxes: np.ndarray, centers: np.ndarray
    ) -> List[Tuple[int, Tuple[float, float, float, float]]]:
        results = []
        for i in range(len(boxes)):
            tid = self._next_id
            self._next_id += 1
            self._centers[tid] = centers[i]
            self._lost[tid] = 0
            results.append((tid, tuple(boxes[i])))
        return results

    def _age_lost(self):
        for tid in list(self._lost):
            self._lost[tid] += 1
            if self._lost[tid] > self.max_lost:
                self._centers.pop(tid, None)
                self._lost.pop(tid, None)
