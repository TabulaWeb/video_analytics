from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models import User, get_db
from app.services.auth import get_current_user
from app.services import analytics as svc

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/day")
def analytics_day(
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return svc.get_period_stats(db, "day", camera_id)


@router.get("/week")
def analytics_week(
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return svc.get_period_stats(db, "week", camera_id)


@router.get("/month")
def analytics_month(
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return svc.get_period_stats(db, "month", camera_id)


@router.get("/hourly")
def analytics_hourly(
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return svc.get_hourly_stats(db, camera_id=camera_id)


@router.get("/daily")
def analytics_daily(
    days: int = Query(30, ge=1, le=365),
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    return svc.get_daily_stats(db, now - timedelta(days=days), now, camera_id)


@router.get("/monthly")
def analytics_monthly(
    months: int = Query(12, ge=1, le=36),
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    return svc.get_monthly_stats(db, now - timedelta(days=months * 30), now, camera_id)


@router.get("/peak-hour-avg")
def analytics_peak_hour_avg(
    days: int = Query(30, ge=1, le=365),
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return svc.get_peak_hour_avg(db, days, camera_id)


@router.get("/weekday-stats")
def analytics_weekday_stats(
    days: int = Query(30, ge=1, le=365),
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return svc.get_weekday_stats(db, days, camera_id)


@router.get("/averages")
def analytics_averages(
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return svc.get_averages(db, camera_id)


@router.get("/growth-trend")
def analytics_growth_trend(
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return svc.get_growth_trend(db, camera_id)


@router.get("/predict-peak")
def analytics_predict_peak(
    days: int = Query(30, ge=1, le=365),
    camera_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    return svc.predict_peak_hour(db, days, camera_id)
