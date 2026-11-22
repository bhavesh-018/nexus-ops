import { afterEach, describe, expect, it, vi } from "vitest";

import { apiRequest, clearTokens, saveTokens } from "./client";

describe("apiRequest token refresh", () => {
  afterEach(() => {
    clearTokens();
    vi.restoreAllMocks();
  });

  it("deduplicates concurrent 401 refreshes into one /auth/refresh call", async () => {
    saveTokens({
      access_token: "expired-access",
      refresh_token: "refresh-1",
      token_type: "bearer",
      expires_in: 900
    });

    let refreshCalls = 0;
    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/refresh")) {
        refreshCalls += 1;
        return new Response(
          JSON.stringify({
            access_token: "fresh-access",
            refresh_token: "refresh-2",
            token_type: "bearer",
            expires_in: 900
          }),
          { status: 200 }
        );
      }
      const authHeader = new Headers(init?.headers).get("Authorization");
      if (authHeader === "Bearer fresh-access") {
        return new Response(JSON.stringify({ ok: true, path: url }), { status: 200 });
      }
      return new Response(JSON.stringify({ error: { code: "unauthenticated", message: "expired" } }), {
        status: 401
      });
    });
    vi.stubGlobal("fetch", fetchMock);

    const [a, b] = await Promise.all([
      apiRequest<{ ok: boolean }>("/api/v1/services"),
      apiRequest<{ ok: boolean }>("/api/v1/auth/me")
    ]);

    expect(a.ok).toBe(true);
    expect(b.ok).toBe(true);
    expect(refreshCalls).toBe(1);
  });
});
