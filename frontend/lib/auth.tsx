"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiPost, API_URL, type User } from "./api";

type AuthState = {
  user: User | null;
  token: string | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setToken(localStorage.getItem("if_token"));
    try {
      const raw = localStorage.getItem("if_user");
      if (raw) setUser(JSON.parse(raw));
    } catch {
      localStorage.removeItem("if_user");
    }
    setReady(true);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiPost<{ access_token: string }>("/auth/login", { email, password });
    localStorage.setItem("if_token", data.access_token);
    setToken(data.access_token);
    const me = await fetch(`${API_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    }).then((r) => r.json());
    localStorage.setItem("if_user", JSON.stringify(me));
    setUser(me);
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiPost("/auth/logout");
    } catch {
      /* token may already be invalid — still clear locally */
    }
    localStorage.removeItem("if_token");
    localStorage.removeItem("if_user");
    setToken(null);
    setUser(null);
  }, []);

  return <Ctx.Provider value={{ user, token, ready, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
