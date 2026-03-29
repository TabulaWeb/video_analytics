import { useCallback, useEffect, useRef, useState } from 'react';
import { analyticsAPI, getWsUrl } from '../services/api';
import type {
  AnalyticsSnapshot,
  PeriodStats,
  HourlyStats,
  DailyStats,
  MonthlyStats,
  WeekdayStats,
  Averages,
  GrowthTrend,
  PeakPrediction,
} from '../types';

export function useAnalytics(cameraId?: string) {
  const [day, setDay] = useState<PeriodStats | null>(null);
  const [week, setWeek] = useState<PeriodStats | null>(null);
  const [month, setMonth] = useState<PeriodStats | null>(null);
  const [hourly, setHourly] = useState<HourlyStats[]>([]);
  const [daily, setDaily] = useState<DailyStats[]>([]);
  const [monthly, setMonthly] = useState<MonthlyStats[]>([]);
  const [weekdayStats, setWeekdayStats] = useState<WeekdayStats[]>([]);
  const [averages, setAverages] = useState<Averages | null>(null);
  const [growthTrend, setGrowthTrend] = useState<GrowthTrend | null>(null);
  const [peakPrediction, setPeakPrediction] = useState<PeakPrediction | null>(null);
  const [peakHourAvg, setPeakHourAvg] = useState<{
    peak_hour: number | null;
    avg_count: number;
    total_count: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasData, setHasData] = useState(false);
  const wsReceivedRef = useRef(false);

  const applySnapshot = useCallback((data: AnalyticsSnapshot) => {
    if (data.day) setDay(data.day);
    if (data.week) setWeek(data.week);
    if (data.month) setMonth(data.month);
    if (data.hourly) setHourly(data.hourly);
    if (data.daily_range) setDaily(data.daily_range);
    if (data.monthly_range) setMonthly(data.monthly_range);
    if (data.weekday_stats) setWeekdayStats(data.weekday_stats);
    if (data.averages) setAverages(data.averages);
    if (data.growth_trend) setGrowthTrend(data.growth_trend);
    if (data.predict_peak) setPeakPrediction(data.predict_peak);
    if (data.peak_hour_avg) setPeakHourAvg(data.peak_hour_avg);

    const d = data.day;
    const w = data.week;
    const m = data.month;
    const has =
      (d?.total_events ?? 0) > 0 ||
      (w?.total_events ?? 0) > 0 ||
      (m?.total_events ?? 0) > 0;
    setHasData(has);
  }, []);

  const fetchAll = useCallback(async () => {
    try {
      setLoading(true);
      const [d, w, m, h, dl, ml, pha, wd, avg, gt, pp] = await Promise.all([
        analyticsAPI.day(cameraId),
        analyticsAPI.week(cameraId),
        analyticsAPI.month(cameraId),
        analyticsAPI.hourly(cameraId),
        analyticsAPI.daily(30, cameraId),
        analyticsAPI.monthly(12, cameraId),
        analyticsAPI.peakHourAvg(30, cameraId),
        analyticsAPI.weekdayStats(30, cameraId),
        analyticsAPI.averages(cameraId),
        analyticsAPI.growthTrend(cameraId),
        analyticsAPI.predictPeak(30, cameraId),
      ]);
      setDay(d);
      setWeek(w);
      setMonth(m);
      setHourly(h);
      setDaily(dl);
      setMonthly(ml);
      setPeakHourAvg(pha);
      setWeekdayStats(wd);
      setAverages(avg);
      setGrowthTrend(gt);
      setPeakPrediction(pp);
      setHasData((d?.total_events ?? 0) > 0 || (w?.total_events ?? 0) > 0 || (m?.total_events ?? 0) > 0);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [cameraId]);

  useEffect(() => {
    wsReceivedRef.current = false;
    let ws: WebSocket | null = null;
    let unmounted = false;
    let fallback: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      if (unmounted) return;
      ws = new WebSocket(getWsUrl('analytics'));
      ws.onmessage = (e) => {
        if (unmounted) return;
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === 'analytics' && msg.data) {
            wsReceivedRef.current = true;
            if (fallback) clearTimeout(fallback);
            applySnapshot(msg.data);
            setLoading(false);
          }
        } catch { /* ignore */ }
      };
      ws.onclose = () => {
        if (!unmounted) setTimeout(connect, 5000);
      };
    };

    fallback = setTimeout(() => {
      if (!unmounted && !wsReceivedRef.current) fetchAll();
    }, 5000);

    const t = setTimeout(connect, 150);

    return () => {
      unmounted = true;
      clearTimeout(t);
      if (fallback) clearTimeout(fallback);
      ws?.close();
    };
  }, [cameraId, applySnapshot, fetchAll]);

  return {
    day, week, month, hourly, daily, monthly,
    weekdayStats, averages, growthTrend, peakPrediction, peakHourAvg,
    loading, hasData, refresh: fetchAll,
  };
}
