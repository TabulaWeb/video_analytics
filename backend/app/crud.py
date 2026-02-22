"""
CRUD operations for People Counter database.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, cast, Date, String, extract
from sqlalchemy.orm import Session

from .models import CameraSettings, Event


# ============================================
# Camera Settings CRUD
# ============================================

def get_camera_settings(db: Session) -> Optional[CameraSettings]:
    """Get active camera settings."""
    return db.query(CameraSettings).filter(CameraSettings.is_active == True).first()


def create_camera_settings(db: Session, settings: Dict) -> CameraSettings:
    """Create new camera settings."""
    # Deactivate all existing settings
    db.query(CameraSettings).update({"is_active": False})
    
    # Create new settings
    db_settings = CameraSettings(**settings, is_active=True)
    db.add(db_settings)
    db.commit()
    db.refresh(db_settings)
    return db_settings


def update_camera_settings(db: Session, settings_id: int, settings: Dict) -> Optional[CameraSettings]:
    """Update camera settings."""
    db_settings = db.query(CameraSettings).filter(CameraSettings.id == settings_id).first()
    if not db_settings:
        return None
    
    for key, value in settings.items():
        # Skip empty password - keep existing password
        if key == 'password' and (value is None or value == ''):
            continue
        setattr(db_settings, key, value)
    
    db_settings.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_settings)
    return db_settings


# ============================================
# Events CRUD
# ============================================

def create_event(db: Session, track_id: int, direction: str) -> Event:
    """Create new event."""
    db_event = Event(track_id=track_id, direction=direction)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_events(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Event]:
    """Get events with optional date filtering."""
    query = db.query(Event)
    
    if start_date:
        query = query.filter(Event.timestamp >= start_date)
    if end_date:
        query = query.filter(Event.timestamp <= end_date)
    
    return query.order_by(Event.timestamp.desc()).offset(skip).limit(limit).all()


def get_event_counts(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, int]:
    """Get event counts by direction."""
    query = db.query(Event.direction, func.count(Event.id).label("count"))
    
    if start_date:
        query = query.filter(Event.timestamp >= start_date)
    if end_date:
        query = query.filter(Event.timestamp <= end_date)
    
    results = query.group_by(Event.direction).all()
    
    counts = {"IN": 0, "OUT": 0}
    for direction, count in results:
        counts[direction] = count
    
    return counts


# ============================================
# Analytics
# ============================================

def get_hourly_stats(db: Session, date: Optional[datetime] = None) -> List[Dict]:
    """Get hourly statistics for a given date."""
    if not date:
        date = datetime.now()
    
    start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    
    # Query events grouped by hour (PostgreSQL compatible)
    results = db.query(
        extract('hour', Event.timestamp).label('hour'),
        Event.direction,
        func.count(Event.id).label('count')
    ).filter(
        Event.timestamp >= start_of_day,
        Event.timestamp < end_of_day
    ).group_by('hour', Event.direction).all()
    
    # Format results
    hourly_data = {}
    for hour, direction, count in results:
        hour_int = int(hour)
        if hour_int not in hourly_data:
            hourly_data[hour_int] = {"hour": hour_int, "IN": 0, "OUT": 0}
        hourly_data[hour_int][direction] = count
    
    # Fill missing hours with 0
    all_hours = []
    for h in range(24):
        all_hours.append(hourly_data.get(h, {"hour": h, "IN": 0, "OUT": 0}))
    
    return all_hours


def get_daily_stats(db: Session, start_date: datetime, end_date: datetime) -> List[Dict]:
    """Get daily statistics for a date range."""
    results = db.query(
        cast(Event.timestamp, Date).label('date'),
        Event.direction,
        func.count(Event.id).label('count')
    ).filter(
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    ).group_by('date', Event.direction).all()
    
    # Format results
    daily_data = {}
    for date_obj, direction, count in results:
        date_str = date_obj.strftime('%Y-%m-%d') if hasattr(date_obj, 'strftime') else str(date_obj)
        if date_str not in daily_data:
            daily_data[date_str] = {"date": date_str, "IN": 0, "OUT": 0}
        daily_data[date_str][direction] = count
    
    # Fill missing days with zeros
    current_date = start_date.date()
    end = end_date.date()
    while current_date <= end:
        date_str = current_date.strftime('%Y-%m-%d')
        if date_str not in daily_data:
            daily_data[date_str] = {"date": date_str, "IN": 0, "OUT": 0}
        current_date += timedelta(days=1)
    
    # Sort by date
    sorted_data = sorted(daily_data.values(), key=lambda x: x['date'])
    return sorted_data


def get_monthly_stats(db: Session, start_date: datetime, end_date: datetime) -> List[Dict]:
    """Get monthly statistics for a date range."""
    # Use PostgreSQL-compatible date_trunc or EXTRACT
    results = db.query(
        func.to_char(Event.timestamp, 'YYYY-MM').label('month'),
        Event.direction,
        func.count(Event.id).label('count')
    ).filter(
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    ).group_by('month', Event.direction).all()
    
    # Format results
    monthly_data = {}
    for month_str, direction, count in results:
        if month_str not in monthly_data:
            monthly_data[month_str] = {"month": month_str, "IN": 0, "OUT": 0}
        monthly_data[month_str][direction] = count
    
    # Fill missing months with zeros
    current_date = start_date.replace(day=1)
    end = end_date.replace(day=1)
    while current_date <= end:
        month_str = current_date.strftime('%Y-%m')
        if month_str not in monthly_data:
            monthly_data[month_str] = {"month": month_str, "IN": 0, "OUT": 0}
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    # Sort by month
    sorted_data = sorted(monthly_data.values(), key=lambda x: x['month'])
    return sorted_data


def get_peak_hours(db: Session, start_date: datetime, end_date: datetime, limit: int = 10) -> List[Dict]:
    """Get peak hours with most activity."""
    results = db.query(
        func.to_char(Event.timestamp, 'YYYY-MM-DD HH24:00').label('hour'),
        func.count(Event.id).label('count')
    ).filter(
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    ).group_by('hour').order_by(func.count(Event.id).desc()).limit(limit).all()
    
    return [{"hour": hour, "count": count} for hour, count in results]


def get_average_peak_hour(db: Session, days: int = 30) -> Dict:
    """Get average peak hour across multiple days."""
    start_date = datetime.now() - timedelta(days=days)
    end_date = datetime.now()
    
    # Get hourly aggregation across all days
    results = db.query(
        extract('hour', Event.timestamp).label('hour'),
        func.count(Event.id).label('count')
    ).filter(
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    ).group_by('hour').order_by(func.count(Event.id).desc()).all()
    
    if not results:
        return {"peak_hour": None, "avg_count": 0, "total_count": 0}
    
    peak_hour = int(results[0][0])
    peak_count = results[0][1]
    
    # Calculate average for that hour
    num_days = (end_date.date() - start_date.date()).days + 1
    avg_count = peak_count / num_days if num_days > 0 else 0
    
    return {
        "peak_hour": peak_hour,
        "avg_count": round(avg_count, 2),
        "total_count": peak_count
    }


def get_weekday_stats(db: Session, days: int = 30) -> List[Dict]:
    """Get activity by day of week."""
    start_date = datetime.now() - timedelta(days=days)
    end_date = datetime.now()
    
    # PostgreSQL: extract dow (0=Sunday, 1=Monday, ..., 6=Saturday)
    results = db.query(
        extract('dow', Event.timestamp).label('dow'),
        Event.direction,
        func.count(Event.id).label('count')
    ).filter(
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    ).group_by('dow', Event.direction).all()
    
    # Convert to Monday=0 format and Russian names
    weekday_names = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    weekday_data = {}
    
    for dow, direction, count in results:
        # Convert Sunday=0 to Monday=0 format
        dow_normalized = 6 if dow == 0 else int(dow) - 1
        weekday_name = weekday_names[dow_normalized]
        
        if weekday_name not in weekday_data:
            weekday_data[weekday_name] = {"weekday": weekday_name, "IN": 0, "OUT": 0, "total": 0}
        
        weekday_data[weekday_name][direction] = count
        weekday_data[weekday_name]["total"] += count
    
    # Ensure all weekdays present
    for name in weekday_names:
        if name not in weekday_data:
            weekday_data[name] = {"weekday": name, "IN": 0, "OUT": 0, "total": 0}
    
    # Return in Monday-Sunday order
    return [weekday_data[name] for name in weekday_names]


def get_averages(db: Session) -> Dict:
    """Calculate average visitors per day/week/month."""
    now = datetime.now()
    
    # Last 7 days
    week_start = now - timedelta(days=7)
    week_counts = get_event_counts(db, week_start, now)
    week_total = week_counts["IN"] + week_counts["OUT"]
    avg_per_day = week_total / 7
    
    # Last 30 days
    month_start = now - timedelta(days=30)
    month_counts = get_event_counts(db, month_start, now)
    month_total = month_counts["IN"] + month_counts["OUT"]
    avg_per_week = month_total / 4.3  # ~4.3 weeks in a month
    avg_per_month = month_total
    
    return {
        "avg_per_day": round(avg_per_day, 1),
        "avg_per_week": round(avg_per_week, 1),
        "avg_per_month": round(avg_per_month, 1)
    }


def get_growth_trend(db: Session) -> Dict:
    """Calculate growth trend comparing current vs previous period."""
    now = datetime.now()
    
    # This week vs last week
    this_week_start = now - timedelta(days=7)
    last_week_start = now - timedelta(days=14)
    last_week_end = this_week_start
    
    this_week = get_event_counts(db, this_week_start, now)
    last_week = get_event_counts(db, last_week_start, last_week_end)
    
    this_week_total = this_week["IN"] + this_week["OUT"]
    last_week_total = last_week["IN"] + last_week["OUT"]
    
    week_change = 0
    if last_week_total > 0:
        week_change = ((this_week_total - last_week_total) / last_week_total) * 100
    
    # This month vs last month
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 1:
        last_month_start = this_month_start.replace(year=now.year - 1, month=12)
    else:
        last_month_start = this_month_start.replace(month=now.month - 1)
    
    this_month = get_event_counts(db, this_month_start, now)
    last_month = get_event_counts(db, last_month_start, this_month_start)
    
    this_month_total = this_month["IN"] + this_month["OUT"]
    last_month_total = last_month["IN"] + last_month["OUT"]
    
    month_change = 0
    if last_month_total > 0:
        month_change = ((this_month_total - last_month_total) / last_month_total) * 100
    
    return {
        "week_change_percent": round(week_change, 1),
        "month_change_percent": round(month_change, 1),
        "trend": "up" if week_change > 0 else "down" if week_change < 0 else "stable"
    }


def predict_peak_hour(db: Session, days: int = 30) -> Dict:
    """Predict next peak hour based on historical data."""
    start_date = datetime.now() - timedelta(days=days)
    end_date = datetime.now()
    current_hour = datetime.now().hour
    
    # Get hourly statistics
    results = db.query(
        extract('hour', Event.timestamp).label('hour'),
        func.count(Event.id).label('count')
    ).filter(
        Event.timestamp >= start_date,
        Event.timestamp <= end_date
    ).group_by('hour').order_by(func.count(Event.id).desc()).all()
    
    if not results:
        return {"predicted_hour": None, "hours_until": 0, "confidence": 0, "expected_count": 0}
    
    # Find peak hour
    peak_hour = int(results[0][0])
    peak_count = results[0][1]
    
    # Calculate average for peak hour
    num_days = (end_date.date() - start_date.date()).days + 1
    avg_count = peak_count / num_days if num_days > 0 else 0
    
    # Determine confidence based on consistency
    # Higher count = higher confidence
    total_events = sum(r[1] for r in results)
    confidence = (peak_count / total_events * 100) if total_events > 0 else 0
    
    # Predict next occurrence
    if peak_hour > current_hour:
        hours_until = peak_hour - current_hour
    else:
        hours_until = (24 - current_hour) + peak_hour
    
    return {
        "predicted_hour": peak_hour,
        "hours_until": hours_until,
        "expected_count": round(avg_count, 1),
        "confidence": round(confidence, 1)
    }
