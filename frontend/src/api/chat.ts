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
    // 流是否已经有「结局」（收到 done 或 error）。
    // 服务端中途断开、反向代理截断响应时，reader 会正常读到 EOF，
    // 循环于是干净退出 —— 但两个回调一个都没被调用过。调用方的 streaming
    // 状态就永远停在 true，输入框从此点不动，只能刷新页面。
    // 所以循环结束后要兜底收尾一次。
    let settled = false;

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
                settled = true;
                onDone();
                break;
              case 'error':
                settled = true;
                onError(data.content || '未知错误');
                break;
            }
          } catch {
            // ignore parse errors
          }
        }
      }
    }

    if (!settled) {
      onDone();
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