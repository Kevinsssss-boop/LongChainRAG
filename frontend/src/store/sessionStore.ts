import { create } from 'zustand';
import { Session, sessionAPI } from '../api/session';

interface SessionState {
  sessions: Session[];
  currentSessionId: string | null;
  loading: boolean;
  fetchSessions: () => Promise<void>;
  createSession: () => Promise<Session | null>;
  deleteSession: (id: string) => Promise<void>;
  setCurrentSession: (id: string | null) => void;
}

export const useSessionStore = create<SessionState>((set, get) => ({
  sessions: [],
  currentSessionId: null,
  loading: false,

  fetchSessions: async () => {
    try {
      set({ loading: true });
      const res = await sessionAPI.list();
      set({ sessions: res.data });
    } catch {
      // ignore
    } finally {
      set({ loading: false });
    }
  },

  createSession: async () => {
    try {
      const res = await sessionAPI.create();
      const newSession = res.data;
      set((s) => ({
        sessions: [newSession, ...s.sessions],
        currentSessionId: newSession.id,
      }));
      return newSession;
    } catch {
      return null;
    }
  },

  deleteSession: async (id: string) => {
    try {
      await sessionAPI.delete(id);
      set((s) => ({
        sessions: s.sessions.filter((sess) => sess.id !== id),
        currentSessionId: s.currentSessionId === id ? null : s.currentSessionId,
      }));
    } catch {
      // ignore
    }
  },

  setCurrentSession: (id: string | null) => set({ currentSessionId: id }),
}));