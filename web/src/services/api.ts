import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('zaga_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('zaga_token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  },
);

export const authAPI = {
  login: (email: string, password: string) =>
    api.post('/api/auth/login', { email, password }).then((r) => r.data),
  register: (email: string, password: string, name: string) =>
    api.post('/api/auth/register', { email, password, name }).then((r) => r.data),
  me: () => api.get('/api/auth/me').then((r) => r.data),
};

export const camerasAPI = {
  list: (activeOnly = false) =>
    api.get('/api/cameras', { params: { active_only: activeOnly } }).then((r) => r.data),
  create: (data: any) => api.post('/api/cameras', data).then((r) => r.data),
  update: (id: string, data: any) => api.put(`/api/cameras/${id}`, data).then((r) => r.data),
  remove: (id: string) => api.delete(`/api/cameras/${id}`),
  logs: (id: string) => api.get(`/api/cameras/${id}/logs`).then((r) => r.data),
};

export const analyticsAPI = {
  day: (cameraId?: string) =>
    api.get('/api/analytics/day', { params: { camera_id: cameraId } }).then((r) => r.data),
  week: (cameraId?: string) =>
    api.get('/api/analytics/week', { params: { camera_id: cameraId } }).then((r) => r.data),
  month: (cameraId?: string) =>
    api.get('/api/analytics/month', { params: { camera_id: cameraId } }).then((r) => r.data),
  hourly: (cameraId?: string) =>
    api.get('/api/analytics/hourly', { params: { camera_id: cameraId } }).then((r) => r.data),
  daily: (days = 30, cameraId?: string) =>
    api.get('/api/analytics/daily', { params: { days, camera_id: cameraId } }).then((r) => r.data),
  monthly: (months = 12, cameraId?: string) =>
    api.get('/api/analytics/monthly', { params: { months, camera_id: cameraId } }).then((r) => r.data),
  peakHourAvg: (days = 30, cameraId?: string) =>
    api.get('/api/analytics/peak-hour-avg', { params: { days, camera_id: cameraId } }).then((r) => r.data),
  weekdayStats: (days = 30, cameraId?: string) =>
    api.get('/api/analytics/weekday-stats', { params: { days, camera_id: cameraId } }).then((r) => r.data),
  averages: (cameraId?: string) =>
    api.get('/api/analytics/averages', { params: { camera_id: cameraId } }).then((r) => r.data),
  growthTrend: (cameraId?: string) =>
    api.get('/api/analytics/growth-trend', { params: { camera_id: cameraId } }).then((r) => r.data),
  predictPeak: (days = 30, cameraId?: string) =>
    api.get('/api/analytics/predict-peak', { params: { days, camera_id: cameraId } }).then((r) => r.data),
};

export function getWsUrl(channel = 'analytics'): string {
  if (API_URL) {
    const base = API_URL.replace(/^https/, 'wss').replace(/^http/, 'ws').replace(/\/$/, '');
    return `${base}/ws/${channel}`;
  }
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws/${channel}`;
}

export default api;
