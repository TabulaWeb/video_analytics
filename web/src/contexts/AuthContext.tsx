import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { authAPI } from '../services/api';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({} as AuthState);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('zaga_token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    authAPI
      .me()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('zaga_token');
        setToken(null);
      })
      .finally(() => setLoading(false));
  }, [token]);

  const login = async (email: string, password: string) => {
    const data = await authAPI.login(email, password);
    localStorage.setItem('zaga_token', data.access_token);
    setToken(data.access_token);
  };

  const register = async (email: string, password: string, name: string) => {
    await authAPI.register(email, password, name);
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem('zaga_token');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
