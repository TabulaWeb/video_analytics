"""Tests for line crossing counter logic."""
import pytest
import time
from app.counter import LineCrossingCounter, TrackState


class TestLineCrossingCounter:
    """Test suite for LineCrossingCounter class."""
    
    def test_initialization(self):
        """Test counter initialization."""
        counter = LineCrossingCounter(line_x=500, hysteresis_px=10)
        
        assert counter.line_x == 500
        assert counter.hysteresis_px == 10
        assert counter.in_count == 0
        assert counter.out_count == 0
        assert len(counter.tracks) == 0
    
    def test_left_to_right_crossing_counts_as_in(self):
        """Test that L→R crossing is counted as IN."""
        counter = LineCrossingCounter(line_x=500, hysteresis_px=5)
        
        # Person starts on left side
        result = counter.process_detection(
            track_id=1,
            bbox=(400, 100, 450, 200)  # cx=425, left of line
        )
        assert result is None  # First detection, no crossing
        assert counter.in_count == 0
        assert counter.out_count == 0
        
        # Person moves to right side
        result = counter.process_detection(
            track_id=1,
            bbox=(550, 100, 600, 200)  # cx=575, right of line
        )
        assert result == "IN"
        assert counter.in_count == 1
        assert counter.out_count == 0
    
    def test_right_to_left_crossing_counts_as_out(self):
        """Test that R→L crossing is counted as OUT."""
        counter = LineCrossingCounter(line_x=500, hysteresis_px=5)
        
        # Person starts on right side
        result = counter.process_detection(
            track_id=2,
            bbox=(550, 100, 600, 200)  # cx=575, right of line
        )
        assert result is None
        
        # Person moves to left side
        result = counter.process_detection(
            track_id=2,
            bbox=(400, 100, 450, 200)  # cx=425, left of line
        )
        assert result == "OUT"
        assert counter.in_count == 0
        assert counter.out_count == 1
    
    def test_hysteresis_prevents_counting_near_line(self):
        """Test that crossings very close to line are ignored."""
        counter = LineCrossingCounter(line_x=500, hysteresis_px=10)
        
        # Person on left
        counter.process_detection(track_id=3, bbox=(400, 100, 450, 200))
        
        # Person moves very close to line (within hysteresis)
        result = counter.process_detection(
            track_id=3,
            bbox=(495, 100, 505, 200)  # cx=500, exactly on line
        )
        assert result is None  # Too close to line
        
        # Person moves clearly past hysteresis zone
        result = counter.process_detection(
            track_id=3,
            bbox=(520, 100, 570, 200)  # cx=545, past hysteresis
        )
        assert result == "IN"
    
    def test_deduplication_same_direction(self):
        """Test that same track isn't counted twice in same direction."""
        counter = LineCrossingCounter(line_x=500, hysteresis_px=5)
        
        # First crossing L→R
        counter.process_detection(track_id=4, bbox=(400, 100, 450, 200))
        result = counter.process_detection(track_id=4, bbox=(550, 100, 600, 200))
        assert result == "IN"
        assert counter.in_count == 1
        
        # Person moves back left
        counter.process_detection(track_id=4, bbox=(400, 100, 450, 200))
        
        # Person crosses right again - should NOT count
        result = counter.process_detection(track_id=4, bbox=(550, 100, 600, 200))
        assert result is None  # Already counted as IN
        assert counter.in_count == 1  # Still 1
    
    def test_multiple_tracks_independent(self):
        """Test that multiple tracks are counted independently."""
        counter = LineCrossingCounter(line_x=500, hysteresis_px=5)
        
        # Track 5: L→R
        counter.process_detection(track_id=5, bbox=(400, 100, 450, 200))
        result5 = counter.process_detection(track_id=5, bbox=(550, 100, 600, 200))
        
        # Track 6: L→R
        counter.process_detection(track_id=6, bbox=(420, 150, 470, 250))
        result6 = counter.process_detection(track_id=6, bbox=(560, 150, 610, 250))
        
        # Track 7: R→L
        counter.process_detection(track_id=7, bbox=(580, 200, 630, 300))
        result7 = counter.process_detection(track_id=7, bbox=(420, 200, 470, 300))
        
        assert result5 == "IN"
        assert result6 == "IN"
        assert result7 == "OUT"
        assert counter.in_count == 2
        assert counter.out_count == 1
    
    def test_track_cleanup_removes_old_tracks(self):
        """Test that old tracks are removed after timeout."""
        counter = LineCrossingCounter(
            line_x=500,
            hysteresis_px=5,
            max_age_seconds=0.1  # Very short timeout for testing
        )
        
        # Create a track
        counter.process_detection(track_id=8, bbox=(400, 100, 450, 200))
        assert len(counter.tracks) == 1
        
        # Wait for timeout
        time.sleep(0.15)
        
        # Cleanup should remove the track
        counter.cleanup_old_tracks()
        assert len(counter.tracks) == 0
    
    def test_reset_counts(self):
        """Test that reset clears counters and tracks."""
        counter = LineCrossingCounter(line_x=500, hysteresis_px=5)
        
        # Generate some counts
        counter.process_detection(track_id=9, bbox=(400, 100, 450, 200))
        counter.process_detection(track_id=9, bbox=(550, 100, 600, 200))
        
        assert counter.in_count > 0
        assert len(counter.tracks) > 0
        
        # Reset
        counter.reset_counts()
        
        assert counter.in_count == 0
        assert counter.out_count == 0
        assert len(counter.tracks) == 0
    
    def test_update_line_position(self):
        """Test that updating line position resets track states."""
        counter = LineCrossingCounter(line_x=500, hysteresis_px=5)
        
        # Track crosses line
        counter.process_detection(track_id=10, bbox=(400, 100, 450, 200))
        counter.process_detection(track_id=10, bbox=(550, 100, 600, 200))
        
        # Track is now counted as IN
        assert counter.tracks[10].counted_direction == "IN"
        
        # Move line
        counter.update_line_position(600)
        
        # Track's counted state should be reset
        assert counter.tracks[10].counted_direction is None
    
    def test_get_stats(self):
        """Test stats retrieval."""
        counter = LineCrossingCounter(line_x=500, hysteresis_px=5)
        
        # Create some activity
        counter.process_detection(track_id=11, bbox=(400, 100, 450, 200))
        counter.process_detection(track_id=11, bbox=(550, 100, 600, 200))
        counter.process_detection(track_id=12, bbox=(600, 100, 650, 200))
        
        stats = counter.get_stats()
        
        assert stats["in_count"] == 1
        assert stats["out_count"] == 0
        assert stats["active_tracks"] == 2


class TestTrackState:
    """Test suite for TrackState dataclass."""
    
    def test_track_state_initialization(self):
        """Test TrackState initialization."""
        track = TrackState(
            track_id=1,
            last_center_x=100.0,
            last_center_y=200.0,
            last_side="L"
        )
        
        assert track.track_id == 1
        assert track.last_center_x == 100.0
        assert track.last_center_y == 200.0
        assert track.last_side == "L"
        assert track.counted_direction is None
        assert track.last_seen_ts > 0
    
    def test_update_position(self):
        """Test position update."""
        track = TrackState(
            track_id=1,
            last_center_x=100.0,
            last_center_y=200.0,
            last_side="L"
        )
        
        old_ts = track.last_seen_ts
        time.sleep(0.01)
        
        track.update_position(150.0, 250.0)
        
        assert track.last_center_x == 150.0
        assert track.last_center_y == 250.0
        assert track.last_seen_ts > old_ts


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
