import { useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { App } from 'antd';
import { sessionAPI } from '../api/session';
import { chatStream } from '../api/chat';
import { useSessionStore } from '../store/sessionStore';
import { useChatStore } from '../store/chatStore';
import { ChatWindow } from '../components/Chat/ChatWindow';
import { ChatInput } from '../components/Chat/ChatInput';

export function ChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { message: msgApi } = App.useApp();
  const abortRef = useRef<AbortController | null>(null);
  const switcherRef = useRef<string | undefined>();

  const { createSession, fetchSessions } = useSessionStore();
  const {
    messages, streaming, streamContent, citations,
    setMessages, setStreaming, appendStreamToken, setCitations, setError, clearChat, addMessage, finalizeStream,
  } = useChatStore();

  // Load messages when session changes
  useEffect(() => {
    if (!sessionId) return;
    if (switcherRef.current === sessionId) return;
    switcherRef.current = sessionId;

    clearChat();
    sessionAPI.get(sessionId).then((res) => {
      setMessages(res.data.messages || []);
    }).catch(() => {});
  }, [sessionId]);

  // Create session on first load
  useEffect(() => {
    if (!sessionId && !switcherRef.current) {
      switcherRef.current = 'creating';
      createSession().then((s) => {
        if (s) {
          switcherRef.current = undefined;
          navigate(`/chat/${s.id}`, { replace: true });
        }
      });
    }
  }, [sessionId]);

  const handleSend = useCallback(
    (text: string) => {
      if (!sessionId || streaming) return;

      addMessage({
        id: `user-${Date.now()}`,
        role: 'user',
        content: text,
        citations: null,
        token_count: 0,
        created_at: new Date().toISOString(),
      });

      setStreaming(true);
      setError(null);

      abortRef.current = chatStream(
        sessionId,
        text,
        (token) => appendStreamToken(token),
        (cites) => setCitations(cites),
        () => {
          // Save stream as permanent message
          finalizeStream();
          setStreaming(false);
          fetchSessions();
        },
        (err) => {
          setStreaming(false);
          setError(err);
          msgApi.error(err);
        },
      );
    },
    [sessionId, streaming],
  );

  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, []);

  if (!sessionId) {
    return <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>Loading...</div>;
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <ChatWindow messages={messages} citations={citations} streaming={streaming} streamContent={streamContent} onFeedback={() => {}} />
      <ChatInput onSend={handleSend} disabled={streaming} />
    </div>
  );
}