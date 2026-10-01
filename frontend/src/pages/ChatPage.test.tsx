import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';

// vi.mock 的工厂会被提升到文件最顶部，那时普通的 const 还没初始化，
// 所以要在测试里断言的那些 spy 必须用 vi.hoisted 创建。
const h = vi.hoisted(() => ({
  chatStore: {
    setMessages: vi.fn(),
    setStreaming: vi.fn(),
    appendStreamToken: vi.fn(),
    setCitations: vi.fn(),
    setError: vi.fn(),
    clearChat: vi.fn(),
    addMessage: vi.fn(),
    finalizeStream: vi.fn(),
  },
  chatStoreState: { streaming: false },
  sessionStore: {
    createSession: vi.fn(),
    fetchSessions: vi.fn(),
    setCurrentSession: vi.fn(),
  },
  chatStream: vi.fn(),
  navigate: vi.fn(),
  messageError: vi.fn(),
}));

vi.mock('../api/session', () => ({
  sessionAPI: {
    get: vi.fn().mockResolvedValue({ data: { id: 's1', title: 'Test', messages: [] } }),
    list: vi.fn().mockResolvedValue({ data: [] }),
  },
}));

vi.mock('../api/chat', () => ({
  chatStream: h.chatStream,
  chatAPI: { sendFeedback: vi.fn() },
}));

vi.mock('../store/sessionStore', () => ({
  useSessionStore: vi.fn((selector?: any) => {
    const store = { sessions: [], currentSessionId: 's1', ...h.sessionStore };
    return selector ? selector(store) : store;
  }),
}));

// 注意 mock 出来的 store 必须和真实 store 的接口一致。
// 原来这里少了 finalizeStream —— ChatPage 从 store 里解构它，拿到 undefined，
// 流一结束调用就抛 TypeError。那个异常被 vitest 记为 unhandled error（整轮
// 退出码变 1），而被它打断的 setStreaming(false) 没能执行。
vi.mock('../store/chatStore', () => ({
  useChatStore: vi.fn((selector?: any) => {
    const store = {
      messages: [],
      // getter：每次读取都反映当前值，测试可以在 render 前改
      get streaming() {
        return h.chatStoreState.streaming;
      },
      streamContent: '',
      citations: [],
      error: null,
      ...h.chatStore,
    };
    return selector ? selector(store) : store;
  }),
}));

vi.mock('antd', async (importOriginal) => {
  const actual = await importOriginal<typeof import('antd')>();
  return {
    ...actual,
    App: {
      useApp: () => ({ message: { success: vi.fn(), error: h.messageError } }),
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

vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>();
  return {
    ...actual,
    useNavigate: () => h.navigate,
    useParams: () => ({ sessionId: 's1' }),
  };
});

import { ChatPage } from './ChatPage';

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/chat/s1']}>
      <ChatPage />
    </MemoryRouter>
  );
}

describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    h.chatStoreState.streaming = false;
    // clearAllMocks 只清调用记录、不清实现，所以上一个用例设的抛异常实现
    // 会漏到下一个用例。这两个手动重置。
    h.chatStore.finalizeStream.mockReset();
    h.chatStream.mockReset();
  });

  it('renders without crashing', () => {
    renderPage();
    expect(screen.getByText('Send')).toBeInTheDocument();
  });

  it('发送消息后不会跳转离开，并且流结束时复位 streaming', async () => {
    h.chatStream.mockImplementation(
      (_sid: string, _msg: string, onToken: any, onCitations: any, onDone: any) => {
        onToken('Hello!');
        onCitations([]);
        onDone();
        return { abort: vi.fn() };
      }
    );

    renderPage();
    const navigateCallsBeforeSend = h.navigate.mock.calls.length;

    screen.getByText('Send').click();

    await waitFor(() => expect(h.chatStore.finalizeStream).toHaveBeenCalled());

    // 原来的断言是 postSendCalls.length <= 1 —— 在那个场景下数组恒为空，
    // 0 <= 1 永远成立，等于什么都没测。这里改成「发送前后调用次数必须相同」。
    expect(h.navigate.mock.calls.length).toBe(navigateCallsBeforeSend);

    // 流结束了就必须把 streaming 复位，否则输入框永远点不动
    expect(h.chatStore.setStreaming).toHaveBeenLastCalledWith(false);
  });

  it('收尾抛异常时也必须复位 streaming，并把错误报给用户', async () => {
    // 守的是 ChatPage 里那个 try/catch/finally。
    // finalizeStream 一旦抛错，如果 setStreaming(false) 跟着被跳过，
    // streaming 就永远停在 true —— 输入框从此禁用，整个会话卡死。
    // 而且不能把异常直接放出去：那样用户只看到卡住，什么提示都没有。
    h.chatStore.finalizeStream.mockImplementation(() => {
      throw new Error('finalize blew up');
    });
    h.chatStream.mockImplementation(
      (_sid: string, _msg: string, onToken: any, _onCitations: any, onDone: any) => {
        onToken('x');
        onDone();
        return { abort: vi.fn() };
      }
    );

    renderPage();
    screen.getByText('Send').click();

    await waitFor(() =>
      expect(h.chatStore.setStreaming).toHaveBeenLastCalledWith(false)
    );
    expect(h.chatStore.setError).toHaveBeenCalledWith('finalize blew up');
  });

  it('disables send button while streaming', () => {
    h.chatStoreState.streaming = true;

    renderPage();

    expect(screen.getByText('Send')).toBeDisabled();
  });
});
