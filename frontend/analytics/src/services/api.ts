import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth API
export const authAPI = {
  login: async (username: string, password: string) => {
    const response = await api.post('/api/auth/login', { username, password });
    return response.data;
  },
  
  getCurrentUser: async () => {
    const response = await api.get('/api/auth/me');
    return response.data;
  },
};

// Stats API
export const statsAPI = {
  getCurrent: async () => {
    const response = await api.get('/api/stats/current');
    return response.data;
  },
  
  getDay: async (date?: string) => {
    const response = await api.get('/api/analytics/day', { params: { date } });
    return response.data;
  },
  
  getWeek: async (date?: string) => {
    const response = await api.get('/api/analytics/week', { params: { date } });
    return response.data;
  },
  
  getMonth: async (date?: string) => {
    const response = await api.get('/api/analytics/month', { params: { date } });
    return response.data;
  },
  
  getHourly: async (date?: string) => {
    const response = await api.get('/api/analytics/hourly', { params: { date } });
    return response.data;
  },
  
  getPeakHours: async (startDate?: string, endDate?: string, limit = 10) => {
    const response = await api.get('/api/analytics/peak-hours', {
      params: { start_date: startDate, end_date: endDate, limit },
    });
    return response.data;
  },
  
  getDailyRange: async (startDate?: string, endDate?: string) => {
    const response = await api.get('/api/analytics/daily', {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  },
  
  getMonthlyRange: async (startDate?: string, endDate?: string) => {
    const response = await api.get('/api/analytics/monthly', {
      params: { start_date: startDate, end_date: endDate },
    });
    return response.data;
  },
  
  getPeakHourAvg: async (days: number = 30) => {
    const response = await api.get('/api/analytics/peak-hour-avg', {
      params: { days },
    });
    return response.data;
  },
  
  getWeekdayStats: async (days: number = 30) => {
    const response = await api.get('/api/analytics/weekday-stats', {
      params: { days },
    });
    return response.data;
  },
  
  getAverages: async () => {
    const response = await api.get('/api/analytics/averages');
    return response.data;
  },
  
  getGrowthTrend: async () => {
    const response = await api.get('/api/analytics/growth-trend');
    return response.data;
  },
  
  getPredictPeak: async (days: number = 30) => {
    const response = await api.get('/api/analytics/predict-peak', {
      params: { days },
    });
    return response.data;
  },
};

// Export API
export const exportAPI = {
  exportData: async (format: 'csv' | 'excel' | 'pdf', includeCharts = false, startDate?: string, endDate?: string) => {
    const response = await api.post('/api/export', {
      format,
      include_charts: includeCharts,
      start_date: startDate,
      end_date: endDate,
    }, {
      responseType: 'blob',
    });
    
    // Create download link
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    
    const extension = format === 'csv' ? 'csv' : format === 'excel' ? 'xlsx' : 'pdf';
    link.setAttribute('download', `people_counter_${new Date().toISOString().split('T')[0]}.${extension}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
  },
};

export { api };
export default api;
