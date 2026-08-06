import { useState, useRef, useEffect } from 'react';
import { Input, Button } from 'antd';
import { SendOutlined } from '@ant-design/icons';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<any>(null);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue('');
  };

  return (
    <div
      style={{
        display: 'flex',
        gap: 12,
        padding: '16px 24px',
        background: '#fff',
        borderTop: '1px solid #f0f0f0',
        alignItems: 'flex-end',
      }}
    >
      <Input.TextArea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onPressEnter={(e) => {
          if (!e.shiftKey) {
            e.preventDefault();
            handleSend();
          }
        }}
        placeholder="输入您的问题，按 Enter 发送，Shift+Enter 换行"
        autoSize={{ minRows: 1, maxRows: 6 }}
        disabled={disabled}
        style={{ borderRadius: 8, resize: 'none' }}
      />
      <Button
        type="primary"
        icon={<SendOutlined />}
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        style={{ borderRadius: 8, height: 40 }}
      >
        发送
      </Button>
    </div>
  );
}