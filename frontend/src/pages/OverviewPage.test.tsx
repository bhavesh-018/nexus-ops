import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { saveTokens, clearTokens } from "../api/client";
import { AuthProvider } from "../hooks/useAuth";
import { OverviewPage } from "./OverviewPage";

describe("OverviewPage", () => {
  afterEach(() => {
    clearTokens();
    vi.restoreAllMocks();
  });

  it("displays service health counts and recent audit logs for admin", async () => {
    saveTokens({
      access_token: "token",
      refresh_token: "refresh",
      token_type: "bearer",
      expires_in: 900
    });

    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith("/api/v1/auth/me")) {
          return new Response(
            JSON.stringify({
              id: "u1",
              organization_id: "o1",
              email: "ada@acme.io",
              full_name: "Ada Admin",
              role: "admin",
              is_active: true,
              created_at: "2026-11-22T10:00:00Z"
            }),
            { status: 200 }
          );
        }
        if (url.includes("/api/v1/services")) {
          return new Response(
            JSON.stringify([
              {
                id: "s1",
                organization_id: "o1",
                name: "payment-service",
                slug: "payment-service",
                environment: "production",
                tier: "tier1",
                status: "healthy",
                health_url: null,
                metadata: {},
                created_at: "2026-11-22T10:00:00Z",
                updated_at: "2026-11-22T10:00:00Z"
              },
              {
                id: "s2",
                organization_id: "o1",
                name: "order-service",
                slug: "order-service",
                environment: "production",
                tier: "tier1",
                status: "degraded",
                health_url: null,
                metadata: {},
                created_at: "2026-11-22T10:00:00Z",
                updated_at: "2026-11-22T10:00:00Z"
              }
            ]),
            { status: 200 }
          );
        }
        if (url.includes("/api/v1/audit-logs")) {
          return new Response(
            JSON.stringify([
              {
                id: "a1",
                actor_id: "u1",
                action: "service.created",
                resource_type: "service",
                resource_id: "s1",
                details: {},
                ip_address: "127.0.0.1",
                created_at: "2026-11-22T10:00:00Z"
              }
            ]),
            { status: 200 }
          );
        }
        return new Response("not found", { status: 404 });
      })
    );

    render(
      <MemoryRouter>
        <AuthProvider>
          <OverviewPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText("payment-service")).toBeInTheDocument();
    expect(screen.getByText("order-service")).toBeInTheDocument();
    expect(await screen.findByText("service.created")).toBeInTheDocument();
    expect(screen.getByText("2 total")).toBeInTheDocument();
  });
});
