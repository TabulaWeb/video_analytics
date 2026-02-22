import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// Create axios instance
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

// Camera API
export const cameraAPI = {
  getSettings: async () => {
    const response = await api.get('/api/camera/settings');
    return response.data;
  },
  
  createSettings: async (settings: any) => {
    const response = await api.post('/api/camera/settings', settings);
    return response.data;
  },
  
  updateSettings: async (id: number, settings: any) => {
    const response = await api.put(`/api/camera/settings/${id}`, settings);
    return response.data;
  },
};

// System API
export const systemAPI = {
  getStatus: async () => {
    const response = await api.get('/api/system/status');
    return response.data;
  },
  
  getCurrentStats: async () => {
    const response = await api.get('/api/stats/current');
    return response.data;
  },
};

// Events API
export const eventsAPI = {
  getEvents: async (limit = 50) => {
    const response = await api.get('/api/events', { params: { limit } });
    return response.data;
  },
  
  clearEvents: async () => {
    const response = await api.post('/api/events/clear');
    return response.data;
  },
  
  reset: async () => {
    const response = await api.post('/api/reset');
    return response.data;
  },
};

export { api };
export default api;
