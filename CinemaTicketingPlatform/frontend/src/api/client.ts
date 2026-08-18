import axios, { type AxiosRequestConfig } from "axios";

const TOKEN_KEY = "cinema_token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? "http://localhost:8000/api/v1",
});

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY);
export const setToken = (token: string | null): void => {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
};

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const data = error.response?.data;
    const message =
      data?.message ?? (error.response ? `请求失败 (${error.response.status})` : "网络错误");
    return Promise.reject(new Error(message));
  }
);

interface Envelope<T> {
  code: number;
  message: string;
  data: T;
}

export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const resp = await api.get<Envelope<T>>(url, config);
  return resp.data.data;
}

export async function post<T>(url: string, body?: unknown): Promise<T> {
  const resp = await api.post<Envelope<T>>(url, body);
  return resp.data.data;
}
