import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { clearTokens, saveTokens } from "../api/client";
import { AuthProvider } from "../hooks/useAuth";
import { ServicesPage } from "./ServicesPage";

function stubSession(role: "admin" | "viewer") {
  saveTokens({
    access_token: "token",
    refresh_token: "refresh",
    token_type: "bearer",
    expires_in: 900
  });

  const services = [
    {
      id: "s1",
      organization_id: "o1",
      name: "Payment Service",
      slug: "payment-service",
      environment: "production",
      tier: "tier1",
      status: "unknown",
      health_url: null,
      metadata: {},
      created_at: "2026-11-22T10:00:00Z",
      updated_at: "2026-11-22T10:00:00Z"
    }
  ];

  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";

      if (url.endsWith("/api/v1/auth/me")) {
        return new Response(
          JSON.stringify({
            id: "u1",
            organization_id: "o1",
            email: "user@acme.io",
            full_name: "Test User",
            role,
            is_active: true,
            created_at: "2026-11-22T10:00:00Z"
          }),
          { status: 200 }
        );
      }
      if (url.endsWith("/api/v1/services") && method === "GET") {
        return new Response(JSON.stringify(services), { status: 200 });
      }
      if (url.endsWith("/api/v1/services") && method === "POST") {
        const body = JSON.parse(String(init?.body)) as { name: string; environment: string; tier: string };
        const created = {
          id: "s2",
          organization_id: "o1",
          name: body.name,
          slug: body.name.toLowerCase().replace(/\s+/g, "-"),
          environment: body.environment,
          tier: body.tier,
          status: "unknown",
          health_url: null,
          metadata: {},
          created_at: "2026-11-22T10:05:00Z",
          updated_at: "2026-11-22T10:05:00Z"
        };
        services.push(created);
        return new Response(JSON.stringify(created), { status: 201 });
      }
      if (url.endsWith("/monitoring-configs") && method === "GET") {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response("not found", { status: 404 });
    })
  );
}

describe("ServicesPage", () => {
  afterEach(() => {
    clearTokens();
    vi.restoreAllMocks();
  });

  it("allows admin to register a new service and open thresholds drawer", async () => {
    stubSession("admin");

    render(
      <MemoryRouter>
        <AuthProvider>
          <ServicesPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText("Payment Service")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Register service" }));
    fireEvent.change(screen.getByLabelText("Service name"), { target: { value: "Order Service" } });
    fireEvent.click(screen.getByRole("button", { name: "Create service" }));

    await waitFor(() => {
      expect(screen.getByText("Order Service")).toBeInTheDocument();
    });

    fireEvent.click(screen.getAllByRole("button", { name: "Thresholds" })[0]);
    expect(await screen.findByText("Monitoring Thresholds")).toBeInTheDocument();
    expect(screen.getByRole("dialog").parentElement?.parentElement).toBe(document.body);
  });

  it("hides write actions for viewer role", async () => {
    stubSession("viewer");

    render(
      <MemoryRouter>
        <AuthProvider>
          <ServicesPage />
        </AuthProvider>
      </MemoryRouter>
    );

    expect(await screen.findByText("Payment Service")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Register service" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });
});
