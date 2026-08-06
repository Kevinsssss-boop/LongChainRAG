import { describe, it, expect, beforeEach } from 'vitest';
import { useChatStore } from './chatStore';

describe('ChatStore', () => {
  beforeEach(() => {
    // Reset store state before each test
    useChatStore.setState({
      messages: [],
      streaming: false,
      streamContent: '',
      citations: [],
      error: null,
    });
  });

  describe('addMessage', () => {
    it('should append a message to messages array', () => {
      const msg = { id: '1', role: 'user' as const, content: 'hello', citations: null, token_count: 0, created_at: '' };
      useChatStore.getState().addMessage(msg);
      expect(useChatStore.getState().messages).toHaveLength(1);
      expect(useChatStore.getState().messages[0].content).toBe('hello');
    });

    it('should append multiple messages in order', () => {
      useChatStore.getState().addMessage({ id: '1', role: 'user' as const, content: 'first', citations: null, token_count: 0, created_at: '' });
      useChatStore.getState().addMessage({ id: '2', role: 'assistant' as const, content: 'second', citations: [], token_count: 0, created_at: '' });
      expect(useChatStore.getState().messages).toHaveLength(2);
      expect(useChatStore.getState().messages[0].role).toBe('user');
      expect(useChatStore.getState().messages[1].role).toBe('assistant');
    });
  });

  describe('setMessages', () => {
    it('should replace messages array', () => {
      const msgs = [
        { id: '1', role: 'user' as const, content: 'test', citations: null, token_count: 0, created_at: '' },
      ];
      useChatStore.getState().setMessages(msgs);
      expect(useChatStore.getState().messages).toEqual(msgs);
    });
  });

  describe('setStreaming', () => {
    it('should set streaming state and reset streamContent when true', () => {
      useChatStore.setState({ streamContent: 'old content' });
      useChatStore.getState().setStreaming(true);
      expect(useChatStore.getState().streaming).toBe(true);
      expect(useChatStore.getState().streamContent).toBe('');
    });

    it('should set streaming to false when disabled', () => {
      useChatStore.setState({ streamContent: 'some text' });
      useChatStore.getState().setStreaming(false);
      expect(useChatStore.getState().streaming).toBe(false);
    });
  });

  describe('appendStreamToken', () => {
    it('should concatenate token to existing streamContent', () => {
      useChatStore.setState({ streamContent: 'Hello' });
      useChatStore.getState().appendStreamToken(' World');
      expect(useChatStore.getState().streamContent).toBe('Hello World');
    });

    it('should handle empty initial state', () => {
      useChatStore.getState().appendStreamToken('First');
      expect(useChatStore.getState().streamContent).toBe('First');
    });
  });

  describe('setCitations', () => {
    it('should replace citations array', () => {
      const cites = [{ index: 1, content: 'source text', source: 'doc.pdf', score: 0.9 }];
      useChatStore.getState().setCitations(cites);
      expect(useChatStore.getState().citations).toEqual(cites);
    });
  });

  describe('setError', () => {
    it('should set error message', () => {
      useChatStore.getState().setError('Something went wrong');
      expect(useChatStore.getState().error).toBe('Something went wrong');
    });

    it('should clear error when null', () => {
      useChatStore.setState({ error: 'old error' });
      useChatStore.getState().setError(null);
      expect(useChatStore.getState().error).toBeNull();
    });
  });

  describe('clearChat', () => {
    it('should reset all fields to initial state', () => {
      useChatStore.setState({
        messages: [{ id: '1', role: 'user' as const, content: 'msg', citations: null, token_count: 0, created_at: '' }],
        streaming: true,
        streamContent: 'partial',
        citations: [{ index: 1, content: '', source: '', score: 0 }],
        error: 'err',
      });
      useChatStore.getState().clearChat();
      const state = useChatStore.getState();
      expect(state.messages).toEqual([]);
      expect(state.streaming).toBe(false);
      expect(state.streamContent).toBe('');
      expect(state.citations).toEqual([]);
      expect(state.error).toBeNull();
    });
  });
});
