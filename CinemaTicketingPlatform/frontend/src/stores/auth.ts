import { create } from "zustand";
import { api, getToken, setToken } from "../api/client";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, nickname?: string) => Promise<void>;
  fetchMe: () => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  login: async (username, password) => {
    const r = await api.post("/auth/login", { username, password });
    setToken(r.data.data.access_token);
    const me = await api.get("/auth/me");
    set({ user: me.data.data });
  },
  register: async (username, password, nickname) => {
    await api.post("/auth/register", { username, password, nickname });
  },
  fetchMe: async () => {
    if (!getToken()) return;
    try {
      const r = await api.get("/auth/me");
      set({ user: r.data.data });
    } catch {
      setToken(null);
      set({ user: null });
    }
  },
  logout: () => {
    setToken(null);
    set({ user: null });
  },
}));
