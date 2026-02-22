"""
SQLAlchemy models for People Counter database.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool

Base = declarative_base()


class CameraSettings(Base):
    """Camera configuration settings."""
    __tablename__ = "camera_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False)
    port = Column(Integer, default=554)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)  # TODO: Encrypt
    channel = Column(Integer, default=1)
    subtype = Column(Integer, default=0)
    
    # Line settings
    line_x = Column(Integer, nullable=True)
    direction_in = Column(String, default="L->R")  # "L->R" or "R->L"
    
    # Active flag
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Event(Base):
    """Counting event record."""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    track_id = Column(Integer, nullable=False)
    direction = Column(String, nullable=False)  # "IN" or "OUT"
    
    def __repr__(self):
        return f"<Event(id={self.id}, timestamp={self.timestamp}, track_id={self.track_id}, direction={self.direction})>"


# Database setup
def get_db_engine(db_url: str = None, db_path: str = "people_counter.db"):
    """Create database engine with proper configuration for PostgreSQL or SQLite."""
    
    # Use PostgreSQL if db_url is provided, otherwise fallback to SQLite
    if db_url and db_url.startswith("postgresql://"):
        print(f"🐘 Using PostgreSQL database")
        engine = create_engine(
            db_url,
            poolclass=QueuePool,  # Connection pooling for PostgreSQL
            pool_size=10,         # Number of connections to keep
            max_overflow=20,      # Max extra connections
            pool_pre_ping=True,   # Verify connections before using
            pool_recycle=3600,    # Recycle connections after 1 hour
            echo=False
        )
    else:
        print(f"📂 Using SQLite database: {db_path}")
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={
                "check_same_thread": False,
                "timeout": 60,
                "isolation_level": None
            },
            poolclass=NullPool,
            echo=False
        )
        
        # Enable WAL mode for SQLite only
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=60000")
            cursor.execute("PRAGMA cache_size=10000")
            cursor.close()
    
    return engine


def create_db_session(engine):
    """Create database session factory."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal


def init_db(engine):
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
