"""Database management for People Counter."""
import sqlite3
import threading
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager

from app.schemas import CrossingEvent
from app.config import settings


class Database:
    """SQLite database handler for storing crossing events."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()
    
    @contextmanager
    def get_connection(self):
        """Thread-safe connection context manager."""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Events table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    track_id INTEGER NOT NULL,
                    direction TEXT NOT NULL CHECK(direction IN ('IN', 'OUT'))
                )
            """)
            
            # Index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_timestamp 
                ON events(timestamp DESC)
            """)
            
            conn.commit()
    
    def insert_event(self, event: CrossingEvent) -> int:
        """
        Insert a crossing event into the database.
        
        Args:
            event: The crossing event to store
            
        Returns:
            The ID of the inserted event
        """
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO events (timestamp, track_id, direction) VALUES (?, ?, ?)",
                    (event.timestamp.isoformat(), event.track_id, event.direction)
                )
                conn.commit()
                return cursor.lastrowid
    
    def get_recent_events(self, limit: int = 50) -> List[CrossingEvent]:
        """
        Get most recent crossing events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of crossing events, newest first
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            
            return [
                CrossingEvent(
                    id=row["id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    track_id=row["track_id"],
                    direction=row["direction"]
                )
                for row in rows
            ]
    
    def get_stats_today(self) -> tuple[int, int]:
        """
        Get IN/OUT counts for today.
        
        Returns:
            Tuple of (in_count, out_count)
        """
        today = datetime.now().date().isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT COUNT(*) FROM events WHERE direction = 'IN' AND date(timestamp) = ?",
                (today,)
            )
            in_count = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM events WHERE direction = 'OUT' AND date(timestamp) = ?",
                (today,)
            )
            out_count = cursor.fetchone()[0]
            
            return in_count, out_count
    
    def clear_all_events(self):
        """Clear all events (use with caution)."""
        with self.lock:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM events")
                conn.commit()


# Global database instance
db = Database(settings.db_path)
