export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  locale: string;
  is_active: boolean;
}

export interface Camera {
  id: string;
  name: string;
  ip: string | null;
  port: number;
  channel: number;
  subtype: number;
  rtsp_url: string | null;
  line_x: number | null;
  direction_in: string;
  hysteresis_px: number;
  processing_mode: string;
  stream_key: string | null;
  status: string;
  last_error: string | null;
  last_seen_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface PeriodStats {
  period: string;
  start_date: string;
  end_date: string;
  in_count: number;
  out_count: number;
  net_flow: number;
  total_events: number;
}

export interface HourlyStats {
  hour: number;
  in_count: number;
  out_count: number;
}

export interface DailyStats {
  date: string;
  IN: number;
  OUT: number;
}

export interface MonthlyStats {
  month: string;
  IN: number;
  OUT: number;
}

export interface WeekdayStats {
  weekday: string;
  IN: number;
  OUT: number;
  total: number;
}

export interface Averages {
  avg_per_day: number;
  avg_per_week: number;
  avg_per_month: number;
}

export interface GrowthTrend {
  week_change_percent: number;
  month_change_percent: number;
  trend: 'up' | 'down' | 'stable';
}

export interface PeakPrediction {
  predicted_hour: number | null;
  hours_until: number;
  expected_count: number;
  confidence: number;
}

export interface AnalyticsSnapshot {
  day?: PeriodStats;
  week?: PeriodStats;
  month?: PeriodStats;
  hourly?: HourlyStats[];
  daily_range?: DailyStats[];
  monthly_range?: MonthlyStats[];
  weekday_stats?: WeekdayStats[];
  averages?: Averages;
  growth_trend?: GrowthTrend;
  predict_peak?: PeakPrediction;
  peak_hour_avg?: { peak_hour: number | null; avg_count: number; total_count: number };
}
