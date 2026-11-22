import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import * as authApi from "../api/auth";
import { clearTokens, getStoredTokens } from "../api/client";
import type { LoginRequest, RegisterRequest, User } from "../types/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (payload: LoginRequest) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  logoutAll: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSession = useCallback(async () => {
    const { access, refresh } = getStoredTokens();
    if (!access && !refresh) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const profile = await authApi.getMe();
      setUser(profile);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  const login = useCallback(async (payload: LoginRequest) => {
    await authApi.login(payload);
    const profile = await authApi.getMe();
    setUser(profile);
  }, []);

  const register = useCallback(async (payload: RegisterRequest) => {
    await authApi.register(payload);
    const profile = await authApi.getMe();
    setUser(profile);
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
  }, []);

  const logoutAll = useCallback(async () => {
    await authApi.logoutAll();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, logoutAll }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
