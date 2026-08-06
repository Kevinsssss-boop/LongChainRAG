import client from './client';

export interface Session {
  id: string;
  title: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[] | null;
  token_count: number;
  created_at: string;
}

export interface Citation {
  index: number;
  content: string;
  source: string;
  score: number;
}

export interface SessionDetail extends Session {
  messages: Message[];
}

export const sessionAPI = {
  list: () => client.get<Session[]>('/sessions'),

  create: (title?: string) => client.post<Session>('/sessions', { title: title || '新对话' }),

  get: (id: string) => client.get<SessionDetail>(`/sessions/${id}`),

  delete: (id: string) => client.delete(`/sessions/${id}`),

  update: (id: string, title: string) => client.put(`/sessions/${id}`, { title }),
};