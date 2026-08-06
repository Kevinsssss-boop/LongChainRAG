import { describe, it, expect, beforeEach } from 'vitest';
import { useSessionStore } from './sessionStore';

// Mock sessionAPI
vi.mock('../api/session', () => ({
  sessionAPI: {
    list: vi.fn(),
    create: vi.fn(),
    get: vi.fn(),
    delete: vi.fn(),
    update: vi.fn(),
  },
}));

describe('SessionStore', () => {
  beforeEach(() => {
    useSessionStore.setState({
      sessions: [],
      currentSessionId: null,
      loading: false,
    });
  });

  describe('setCurrentSession', () => {
    it('should update currentSessionId', () => {
      useSessionStore.getState().setCurrentSession('session-123');
      expect(useSessionStore.getState().currentSessionId).toBe('session-123');
    });

    it('should allow setting to null', () => {
      useSessionStore.setState({ currentSessionId: 'abc' });
      useSessionStore.getState().setCurrentSession(null);
      expect(useSessionStore.getState().currentSessionId).toBeNull();
    });
  });

  describe('deleteSession', () => {
    it('should remove session and clear currentSessionId if deleted', async () => {
      const { sessionAPI } = await import('../api/session');
      (sessionAPI.delete as any).mockResolvedValue({});

      // Setup
      useSessionStore.setState({
        sessions: [{ id: 's1', title: 'Chat 1', is_active: true, created_at: '', updated_at: '', message_count: 0 }],
        currentSessionId: 's1',
        loading: false,
      });

      await useSessionStore.getState().deleteSession('s1');

      expect(useSessionStore.getState().sessions).toEqual([]);
      expect(useSessionStore.getState().currentSessionId).toBeNull();
    });

    it('should not affect currentSessionId if deleting other session', async () => {
      const { sessionAPI } = await import('../api/session');
      (sessionAPI.delete as any).mockResolvedValue({});

      useSessionStore.setState({
        sessions: [
          { id: 's1', title: 'Chat 1', is_active: true, created_at: '', updated_at: '', message_count: 0 },
          { id: 's2', title: 'Chat 2', is_active: true, created_at: '', updated_at: '', message_count: 0 },
        ],
        currentSessionId: 's2',
        loading: false,
      });

      await useSessionStore.getState().deleteSession('s1');

      expect(useSessionStore.getState().sessions).toHaveLength(1);
      expect(useSessionStore.getState().currentSessionId).toBe('s2');
    });
  });
});
