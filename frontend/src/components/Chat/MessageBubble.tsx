import { useRef, useEffect } from 'react';
import { Avatar, Typography, Space, Button, App } from 'antd';
import { UserOutlined, RobotOutlined, CopyOutlined, LikeOutlined, DislikeOutlined } from '@ant-design/icons';
import { Message, Citation } from '../../api/session';
import { MarkdownRenderer } from '../../utils/markdown';
import { CitationCard } from './CitationCard';

const { Text } = Typography;

interface MessageBubbleProps {
  message: Message;
  citations?: Citation[];
  onFeedback?: (messageId: string, rating: 'up' | 'down') => void;
}

export function MessageBubble({ message, citations, onFeedback }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const { message: msgApi } = App.useApp();

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    msgApi.success('已复制到剪贴板');
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: isUser ? 'row-reverse' : 'row',
        gap: 12,
        marginBottom: 20,
        alignItems: 'flex-start',
      }}
    >
      <Avatar
        icon={isUser ? <UserOutlined /> : <RobotOutlined />}
        style={{
          background: isUser ? '#1677ff' : '#52c41a',
          flexShrink: 0,
        }}
      />
      <div style={{ maxWidth: '75%', minWidth: 120 }}>
        <div style={{ marginBottom: 4 }}>
          <Text strong style={{ fontSize: 12, color: '#999' }}>
            {isUser ? '你' : 'AI 助手'}
          </Text>
        </div>
        <div
          style={{
            padding: '12px 16px',
            borderRadius: 12,
            background: isUser ? '#e6f4ff' : '#f5f5f5',
            border: isUser ? '1px solid #91caff' : '1px solid #d9d9d9',
            wordBreak: 'break-word',
          }}
        >
          {isUser ? (
            <Text style={{ whiteSpace: 'pre-wrap' }}>{message.content}</Text>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}
        </div>
        {/* Citations */}
        {!isUser && citations && citations.length > 0 && (
          <CitationCard citations={citations} />
        )}
        {/* Actions for assistant messages */}
        {!isUser && (
          <Space style={{ marginTop: 6 }}>
            <Button type="text" size="small" icon={<CopyOutlined />} onClick={handleCopy}>
              复制
            </Button>
            <Button
              type="text"
              size="small"
              icon={<LikeOutlined />}
              onClick={() => onFeedback?.(message.id, 'up')}
            />
            <Button
              type="text"
              size="small"
              icon={<DislikeOutlined />}
              onClick={() => onFeedback?.(message.id, 'down')}
            />
          </Space>
        )}
      </div>
    </div>
  );
}