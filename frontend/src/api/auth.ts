import type { LoginRequest, RegisterRequest, TokenPair, User } from "../types/api";
import { apiRequest, clearTokens, getStoredTokens, saveTokens } from "./client";

export async function register(payload: RegisterRequest): Promise<TokenPair> {
  const pair = await apiRequest<TokenPair>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true
  });
  saveTokens(pair);
  return pair;
}

export async function login(payload: LoginRequest): Promise<TokenPair> {
  const pair = await apiRequest<TokenPair>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
    skipAuth: true
  });
  saveTokens(pair);
  return pair;
}

export async function getMe(): Promise<User> {
  return apiRequest<User>("/api/v1/auth/me");
}

export async function logout(): Promise<void> {
  const { refresh } = getStoredTokens();
  try {
    if (refresh) {
      await apiRequest<void>("/api/v1/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refresh }),
        skipAuth: true
      });
    }
  } finally {
    clearTokens();
  }
}

export async function logoutAll(): Promise<void> {
  try {
    await apiRequest<void>("/api/v1/auth/logout-all", { method: "POST" });
  } finally {
    clearTokens();
  }
}
