import { create } from 'zustand';
import { Message, Citation } from '../api/session';

interface ChatState {
  messages: Message[];
  streaming: boolean;
  streamContent: string;
  citations: Citation[];
  error: string | null;
  addMessage: (msg: Message) => void;
  setMessages: (msgs: Message[]) => void;
  setStreaming: (v: boolean) => void;
  appendStreamToken: (token: string) => void;
  setCitations: (citations: Citation[]) => void;
  setError: (err: string | null) => void;
  clearChat: () => void;
  finalizeStream: () => Message | null;  // Save stream to messages
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  streaming: false,
  streamContent: '',
  citations: [],
  error: null,

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  setMessages: (msgs) => set({ messages: msgs }),

  setStreaming: (v) => set({ streaming: v, streamContent: v ? '' : get().streamContent }),

  appendStreamToken: (token) =>
    set((s) => ({ streamContent: s.streamContent + token })),

  setCitations: (cites) => set({ citations: cites }),

  setError: (err) => set({ error: err }),

  clearChat: () =>
    set({ messages: [], streamContent: '', citations: [], error: null, streaming: false }),

  finalizeStream: () => {
    const { streamContent, citations } = get();
    if (!streamContent) return null;

    const msg: Message = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: streamContent,
      citations: citations,
      token_count: 0,
      created_at: new Date().toISOString(),
    };

    set((s) => ({
      messages: [...s.messages, msg],
      streamContent: '',
      citations: [],
    }));
    return msg;
  },
}));