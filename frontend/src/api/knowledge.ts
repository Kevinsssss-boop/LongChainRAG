import client from './client';

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  status: string;
  uploaded_by: string;
  created_at: string;
}

export const knowledgeAPI = {
  list: (page = 1, pageSize = 20) =>
    client.get<{ total: number; items: Document[] }>('/knowledge/documents', {
      params: { page, page_size: pageSize },
    }),

  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return client.post<Document>('/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  delete: (id: string) => client.delete(`/knowledge/documents/${id}`),

  getChunks: (id: string) =>
    client.get<{ chunks: { chunk_index: number; content: string; metadata: any }[] }>(
      `/knowledge/documents/${id}/chunks`,
    ),
};