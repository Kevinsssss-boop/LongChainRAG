import { useEffect, useRef } from 'react';
import { Empty, Spin } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import { Message, Citation } from '../../api/session';
import { MessageBubble } from './MessageBubble';
import { useChatStore } from '../../store/chatStore';

interface ChatWindowProps {
  messages: Message[];
  citations: Citation[];
  streaming: boolean;
  streamContent: string;
  onFeedback: (messageId: string, rating: 'up' | 'down') => void;
}

export function ChatWindow({ messages, citations, streaming, streamContent, onFeedback }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamContent]);

  return (
    <div
      style={{
        flex: 1,
        overflow: 'auto',
        padding: '24px 24px 0',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {messages.length === 0 && !streaming && (
        <div style={{ margin: 'auto', textAlign: 'center' }}>
          <Empty
            description={
              <div>
                <p style={{ fontSize: 18, marginBottom: 8 }}>开始提问吧</p>
                <p style={{ color: '#999' }}>
                  选择左侧对话或创建新对话，向 AI 助手提问关于商品的问题
                </p>
              </div>
            }
          />
        </div>
      )}

      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          citations={msg.role === 'assistant' ? msg.citations || undefined : undefined}
          onFeedback={onFeedback}
        />
      ))}

      {/* Streaming message */}
      {streaming && streamContent && (
        <MessageBubble
          message={{
            id: 'streaming',
            role: 'assistant',
            content: streamContent,
            citations: citations,
            token_count: 0,
            created_at: new Date().toISOString(),
          }}
        />
      )}

      {streaming && !streamContent && (
        <div style={{ padding: '40px 0', textAlign: 'center' }}>
          <Spin indicator={<LoadingOutlined style={{ fontSize: 32 }} spin />} />
          <p style={{ color: '#999', marginTop: 12 }}>AI 正在思考...</p>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}