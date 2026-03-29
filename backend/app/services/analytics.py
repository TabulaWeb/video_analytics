from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, cast, Date, extract
from sqlalchemy.orm import Session

from app.models import Event


def get_event_counts(
    db: Session,
    start: datetime,
    end: datetime,
    camera_id: Optional[UUID] = None,
) -> Dict[str, int]:
    q = db.query(Event.direction, func.count(Event.id))
    if camera_id:
        q = q.filter(Event.camera_id == camera_id)
    q = q.filter(Event.timestamp >= start, Event.timestamp <= end)
    results = q.group_by(Event.direction).all()
    counts = {"IN": 0, "OUT": 0}
    for direction, count in results:
        counts[direction] = count
    return counts


def get_period_stats(
    db: Session,
    period: str,
    camera_id: Optional[UUID] = None,
) -> Dict:
    now = datetime.now(timezone.utc)
    if period == "day":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    counts = get_event_counts(db, start, now, camera_id)
    in_c, out_c = counts["IN"], counts["OUT"]
    return {
        "period": period,
        "start_date": start.isoformat(),
        "end_date": now.isoformat(),
        "in_count": in_c,
        "out_count": out_c,
        "net_flow": in_c - out_c,
        "total_events": in_c + out_c,
    }


def get_hourly_stats(
    db: Session,
    date: Optional[datetime] = None,
    camera_id: Optional[UUID] = None,
) -> List[Dict]:
    if not date:
        date = datetime.now(timezone.utc)
    start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)

    q = db.query(
        extract("hour", Event.timestamp).label("hour"),
        Event.direction,
        func.count(Event.id).label("count"),
    )
    if camera_id:
        q = q.filter(Event.camera_id == camera_id)
    q = q.filter(Event.timestamp >= start, Event.timestamp < end)
    results = q.group_by("hour", Event.direction).all()

    hourly: Dict[int, Dict] = {}
    for hour, direction, count in results:
        h = int(hour)
        if h not in hourly:
            hourly[h] = {"hour": h, "in_count": 0, "out_count": 0}
        hourly[h]["in_count" if direction == "IN" else "out_count"] = count

    return [hourly.get(h, {"hour": h, "in_count": 0, "out_count": 0}) for h in range(24)]


def get_daily_stats(
    db: Session,
    start: datetime,
    end: datetime,
    camera_id: Optional[UUID] = None,
) -> List[Dict]:
    q = db.query(
        cast(Event.timestamp, Date).label("date"),
        Event.direction,
        func.count(Event.id).label("count"),
    )
    if camera_id:
        q = q.filter(Event.camera_id == camera_id)
    q = q.filter(Event.timestamp >= start, Event.timestamp <= end)
    results = q.group_by("date", Event.direction).all()

    daily: Dict[str, Dict] = {}
    for d, direction, count in results:
        ds = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
        if ds not in daily:
            daily[ds] = {"date": ds, "IN": 0, "OUT": 0}
        daily[ds][direction] = count

    cur = start.date()
    while cur <= end.date():
        ds = cur.strftime("%Y-%m-%d")
        if ds not in daily:
            daily[ds] = {"date": ds, "IN": 0, "OUT": 0}
        cur += timedelta(days=1)

    return sorted(daily.values(), key=lambda x: x["date"])


def get_monthly_stats(
    db: Session,
    start: datetime,
    end: datetime,
    camera_id: Optional[UUID] = None,
) -> List[Dict]:
    q = db.query(
        func.to_char(Event.timestamp, "YYYY-MM").label("month"),
        Event.direction,
        func.count(Event.id).label("count"),
    )
    if camera_id:
        q = q.filter(Event.camera_id == camera_id)
    q = q.filter(Event.timestamp >= start, Event.timestamp <= end)
    results = q.group_by("month", Event.direction).all()

    monthly: Dict[str, Dict] = {}
    for ms, direction, count in results:
        if ms not in monthly:
            monthly[ms] = {"month": ms, "IN": 0, "OUT": 0}
        monthly[ms][direction] = count

    cur = start.replace(day=1)
    e = end.replace(day=1)
    while cur <= e:
        ms = cur.strftime("%Y-%m")
        if ms not in monthly:
            monthly[ms] = {"month": ms, "IN": 0, "OUT": 0}
        if cur.month == 12:
            cur = cur.replace(year=cur.year + 1, month=1)
        else:
            cur = cur.replace(month=cur.month + 1)

    return sorted(monthly.values(), key=lambda x: x["month"])


def get_peak_hour_avg(
    db: Session,
    days: int = 30,
    camera_id: Optional[UUID] = None,
) -> Dict:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    end = datetime.now(timezone.utc)

    q = db.query(
        extract("hour", Event.timestamp).label("hour"),
        func.count(Event.id).label("count"),
    )
    if camera_id:
        q = q.filter(Event.camera_id == camera_id)
    q = q.filter(Event.timestamp >= start, Event.timestamp <= end)
    results = q.group_by("hour").order_by(func.count(Event.id).desc()).all()

    if not results:
        return {"peak_hour": None, "avg_count": 0, "total_count": 0}

    peak_hour = int(results[0][0])
    peak_count = results[0][1]
    num_days = max((end.date() - start.date()).days, 1)
    return {
        "peak_hour": peak_hour,
        "avg_count": round(peak_count / num_days, 2),
        "total_count": peak_count,
    }


def get_weekday_stats(
    db: Session,
    days: int = 30,
    camera_id: Optional[UUID] = None,
) -> List[Dict]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    end = datetime.now(timezone.utc)
    names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    q = db.query(
        extract("dow", Event.timestamp).label("dow"),
        Event.direction,
        func.count(Event.id).label("count"),
    )
    if camera_id:
        q = q.filter(Event.camera_id == camera_id)
    q = q.filter(Event.timestamp >= start, Event.timestamp <= end)
    results = q.group_by("dow", Event.direction).all()

    data: Dict[str, Dict] = {}
    for dow, direction, count in results:
        idx = 6 if int(dow) == 0 else int(dow) - 1
        name = names[idx]
        if name not in data:
            data[name] = {"weekday": name, "IN": 0, "OUT": 0, "total": 0}
        data[name][direction] = count
        data[name]["total"] += count

    for n in names:
        if n not in data:
            data[n] = {"weekday": n, "IN": 0, "OUT": 0, "total": 0}

    return [data[n] for n in names]


def get_averages(
    db: Session,
    camera_id: Optional[UUID] = None,
) -> Dict:
    now = datetime.now(timezone.utc)

    week_counts = get_event_counts(db, now - timedelta(days=7), now, camera_id)
    week_total = week_counts["IN"] + week_counts["OUT"]

    month_counts = get_event_counts(db, now - timedelta(days=30), now, camera_id)
    month_total = month_counts["IN"] + month_counts["OUT"]

    return {
        "avg_per_day": round(week_total / 7, 1),
        "avg_per_week": round(month_total / 4.3, 1),
        "avg_per_month": round(month_total, 1),
    }


def get_growth_trend(
    db: Session,
    camera_id: Optional[UUID] = None,
) -> Dict:
    now = datetime.now(timezone.utc)

    this_w = get_event_counts(db, now - timedelta(days=7), now, camera_id)
    last_w = get_event_counts(db, now - timedelta(days=14), now - timedelta(days=7), camera_id)
    tw = this_w["IN"] + this_w["OUT"]
    lw = last_w["IN"] + last_w["OUT"]
    wc = ((tw - lw) / lw * 100) if lw > 0 else 0.0

    this_m_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if now.month == 1:
        last_m_start = this_m_start.replace(year=now.year - 1, month=12)
    else:
        last_m_start = this_m_start.replace(month=now.month - 1)

    tm = get_event_counts(db, this_m_start, now, camera_id)
    lm = get_event_counts(db, last_m_start, this_m_start, camera_id)
    tm_t = tm["IN"] + tm["OUT"]
    lm_t = lm["IN"] + lm["OUT"]
    mc = ((tm_t - lm_t) / lm_t * 100) if lm_t > 0 else 0.0

    return {
        "week_change_percent": round(wc, 1),
        "month_change_percent": round(mc, 1),
        "trend": "up" if wc > 0 else ("down" if wc < 0 else "stable"),
    }


def predict_peak_hour(
    db: Session,
    days: int = 30,
    camera_id: Optional[UUID] = None,
) -> Dict:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    end = datetime.now(timezone.utc)
    current_hour = datetime.now(timezone.utc).hour

    q = db.query(
        extract("hour", Event.timestamp).label("hour"),
        func.count(Event.id).label("count"),
    )
    if camera_id:
        q = q.filter(Event.camera_id == camera_id)
    q = q.filter(Event.timestamp >= start, Event.timestamp <= end)
    results = q.group_by("hour").order_by(func.count(Event.id).desc()).all()

    if not results:
        return {"predicted_hour": None, "hours_until": 0, "expected_count": 0, "confidence": 0}

    peak_hour = int(results[0][0])
    peak_count = results[0][1]
    num_days = max((end.date() - start.date()).days, 1)
    total = sum(r[1] for r in results)
    confidence = (peak_count / total * 100) if total > 0 else 0

    hours_until = peak_hour - current_hour if peak_hour > current_hour else (24 - current_hour) + peak_hour

    return {
        "predicted_hour": peak_hour,
        "hours_until": hours_until,
        "expected_count": round(peak_count / num_days, 1),
        "confidence": round(confidence, 1),
    }
