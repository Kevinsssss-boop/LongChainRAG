import client from './client';
import { Citation } from './session';

export interface ChatStreamEvent {
  type: 'token' | 'citations' | 'done' | 'error';
  content?: string;
  data?: Citation[];
}

export function chatStream(
  sessionId: string,
  message: string,
  onToken: (token: string) => void,
  onCitations: (citations: Citation[]) => void,
  onDone: () => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController();
  const token = localStorage.getItem('access_token');

  fetch(`/api/chat/${sessionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message }),
    signal: controller.signal,
  }).then(async (response) => {
    if (!response.ok) {
      const err = await response.json();
      onError(err.detail || '请求失败');
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data: ChatStreamEvent = JSON.parse(line.slice(6));
            switch (data.type) {
              case 'token':
                onToken(data.content || '');
                break;
              case 'citations':
                onCitations(data.data || []);
                break;
              case 'done':
                onDone();
                break;
              case 'error':
                onError(data.content || '未知错误');
                break;
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    }
  }).catch((err) => {
    if (err.name !== 'AbortError') {
      onError(err.message);
    }
  });

  return controller;
}

export const chatAPI = {
  sendFeedback: (sessionId: string, messageId: string, rating: 'up' | 'down') =>
    client.post(`/chat/${sessionId}/feedback`, { message_id: messageId, rating }),
};