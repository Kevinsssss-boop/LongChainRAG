import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: attach token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: handle 401
client.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const url: string = error.config?.url ?? '';

    // 登录 / 注册接口返回的 401 意思是「密码错了」，不是「会话过期」。
    // 原来这里对**任何** 401 都清 token 并跳转 /login —— 于是输错密码会触发
    // 一次整页重载，React 组件树连同错误状态一起被销毁，用户永远看不到
    // 「用户名或密码错误」，只觉得点了一下按钮页面自己刷新了。
    const isCredentialCheck =
      url.includes('/auth/login') || url.includes('/auth/register');

    // 本来就没有 token 时也无需跳转（否则可能在 /login 上反复重载）
    const hadToken = !!localStorage.getItem('access_token');

    if (status === 401 && !isCredentialCheck && hadToken) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default client;