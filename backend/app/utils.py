"""Utility functions for the application."""
import time
from datetime import datetime
from typing import Callable, Any


class Throttler:
    """Rate limiter to prevent excessive function calls."""
    
    def __init__(self, interval: float):
        """
        Args:
            interval: Minimum time between calls in seconds
        """
        self.interval = interval
        self.last_call = 0.0
    
    def can_call(self) -> bool:
        """Check if enough time has passed since last call."""
        now = time.time()
        if now - self.last_call >= self.interval:
            self.last_call = now
            return True
        return False
    
    def reset(self):
        """Reset the throttler."""
        self.last_call = 0.0


def get_timestamp() -> datetime:
    """Get current timestamp."""
    return datetime.now()


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}min"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"
