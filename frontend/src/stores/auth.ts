import { create } from "zustand";
import api from "../api/client";

interface AuthState {
  token: string | null;
  userId: string | null;
  email: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem("nexa_token"),
  userId: localStorage.getItem("nexa_user_id"),
  email: localStorage.getItem("nexa_email"),
  isAuthenticated: !!localStorage.getItem("nexa_token"),

  login: async (email: string, password: string) => {
    const { data } = await api.post("/api/auth/login", { email, password });
    localStorage.setItem("nexa_token", data.token);
    localStorage.setItem("nexa_user_id", data.user_id);
    localStorage.setItem("nexa_email", data.email);
    set({ token: data.token, userId: data.user_id, email: data.email, isAuthenticated: true });
  },

  register: async (email: string, password: string) => {
    const { data } = await api.post("/api/auth/register", { email, password });
    localStorage.setItem("nexa_token", data.token);
    localStorage.setItem("nexa_user_id", data.user_id);
    localStorage.setItem("nexa_email", data.email);
    set({ token: data.token, userId: data.user_id, email: data.email, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem("nexa_token");
    localStorage.removeItem("nexa_user_id");
    localStorage.removeItem("nexa_email");
    set({ token: null, userId: null, email: null, isAuthenticated: false });
  },

  checkAuth: () => {
    const token = localStorage.getItem("nexa_token");
    set({ isAuthenticated: !!token });
  },
}));
