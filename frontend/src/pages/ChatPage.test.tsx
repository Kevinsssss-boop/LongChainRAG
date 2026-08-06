import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';

// Mock all dependencies
vi.mock('../api/session', () => ({
  sessionAPI: {
    get: vi.fn().mockResolvedValue({ data: { id: 's1', title: 'Test', messages: [] } }),
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
}));

vi.mock('../api/chat', () => ({
  chatStream: vi.fn(),
  chatAPI: {
    sendFeedback: vi.fn(),
  },
}));

vi.mock('../store/sessionStore', () => ({
  useSessionStore: vi.fn((selector?: any) => {
    const store = {
      sessions: [],
      currentSessionId: 's1',
      createSession: vi.fn().mockResolvedValue({ id: 's1', title: 'Test' }),
      fetchSessions: vi.fn(),
      setCurrentSession: vi.fn(),
    };
    return selector ? selector(store) : store;
  }),
}));

vi.mock('../store/chatStore', () => ({
  useChatStore: vi.fn((selector?: any) => {
    const store = {
      messages: [],
      streaming: false,
      streamContent: '',
      citations: [],
      error: null,
      setMessages: vi.fn(),
      setStreaming: vi.fn(),
      appendStreamToken: vi.fn(),
      setCitations: vi.fn(),
      setError: vi.fn(),
      clearChat: vi.fn(),
      addMessage: vi.fn(),
    };
    return selector ? selector(store) : store;
  }),
}));

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>();
  return {
    ...actual,
    App: {
      useApp: () => ({ message: { success: vi.fn(), error: vi.fn() } }),
    },
  };
});

vi.mock('../components/Chat/ChatWindow', () => ({
  ChatWindow: () => <div>ChatWindow</div>,
}));

vi.mock('../components/Chat/ChatInput', () => ({
  ChatInput: ({ onSend, disabled }: any) => (
    <button onClick={() => onSend('test message')} disabled={disabled}>
      Send
    </button>
  ),
}));

// Mock react-router-dom's useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ sessionId: 's1' }),
  };
});

import { ChatPage } from './ChatPage';

describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders without crashing', () => {
    render(
      <MemoryRouter>
        <ChatPage />
      </MemoryRouter>
    );
    expect(screen.getByText('Send')).toBeInTheDocument();
  });

  it('does NOT navigate away after sending a message', async () => {
    const { chatStream } = await import('../api/chat');
    const streamFn = vi.fn();
    (chatStream as any).mockImplementation(
      (sid: string, msg: string, onToken: any, onCitations: any, onDone: any, onError: any) => {
        // Simulate a complete chat flow
        onToken('Hello!');
        onCitations([]);
        onDone();
        return { abort: vi.fn() };
      }
    );

    render(
      <MemoryRouter initialEntries={['/chat/s1']}>
        <ChatPage />
      </MemoryRouter>
    );

    const sendBtn = screen.getByText('Send');
    sendBtn.click();

    // Wait for the flow to complete
    await waitFor(() => {
      // The navigate function should NOT have been called with a new session ID
      const navigateCalls = mockNavigate.mock.calls;
      // If navigate was called for auto-creation, it should only happen once at init
      // After sending a message, navigate should NOT be called again
      const postSendCalls = navigateCalls.filter(
        (call: any) => typeof call[0] === 'string' && call[0].includes('/chat/')
      );
      // Should not have more than 1 navigate call (initial redirect if no sessionId)
      expect(postSendCalls.length).toBeLessThanOrEqual(1);
    });
  });

  it('disables send button while streaming', async () => {
    const { useChatStore } = await import('../store/chatStore');
    // Modify the mock to simulate streaming state
    const originalImpl = (useChatStore as any).getMockImplementation();
    (useChatStore as any).mockImplementation((selector: any) => {
      const store = {
        messages: [],
        streaming: true, // simulate streaming
        streamContent: '',
        citations: [],
        error: null,
        setMessages: vi.fn(),
        setStreaming: vi.fn(),
        appendStreamToken: vi.fn(),
        setCitations: vi.fn(),
        setError: vi.fn(),
        clearChat: vi.fn(),
        addMessage: vi.fn(),
      };
      return selector ? selector(store) : store;
    });

    render(
      <MemoryRouter initialEntries={['/chat/s1']}>
        <ChatPage />
      </MemoryRouter>
    );

    const sendBtn = screen.getByText('Send');
    expect(sendBtn).toBeDisabled();

    // Restore
    (useChatStore as any).mockImplementation(originalImpl);
  });
});
