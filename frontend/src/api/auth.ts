import client from './client';

export interface User {
  id: string;
  username: string;
  email: string | null;
  is_admin: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export const authAPI = {
  register: (username: string, password: string, email?: string) =>
    client.post<TokenResponse>('/auth/register', { username, password, email }),

  login: (username: string, password: string) =>
    client.post<TokenResponse>('/auth/login', { username, password }),

  getMe: () => client.get<User>('/auth/me'),

  changePassword: (old_password: string, new_password: string) =>
    client.put('/auth/password', { old_password, new_password }),
};