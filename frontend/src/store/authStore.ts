import { create } from 'zustand';
import { User, authAPI } from '../api/auth';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, email?: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  isAdmin: () => boolean;
  isAuthenticated: () => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  token: localStorage.getItem('access_token'),
  loading: false,

  login: async (username: string, password: string) => {
    const res = await authAPI.login(username, password);
    const { access_token, user } = res.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('user', JSON.stringify(user));
    set({ user, token: access_token });
  },

  register: async (username: string, password: string, email?: string) => {
    const res = await authAPI.register(username, password, email);
    const { access_token, user } = res.data;
    localStorage.setItem('access_token', access_token);
    localStorage.setItem('user', JSON.stringify(user));
    set({ user, token: access_token });
  },

  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    set({ user: null, token: null });
  },

  loadUser: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) return;
    try {
      set({ loading: true });
      const res = await authAPI.getMe();
      localStorage.setItem('user', JSON.stringify(res.data));
      set({ user: res.data });
    } catch {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      set({ user: null, token: null });
    } finally {
      set({ loading: false });
    }
  },

  isAdmin: () => get().user?.is_admin ?? false,
  isAuthenticated: () => !!get().token && !!get().user,
}));