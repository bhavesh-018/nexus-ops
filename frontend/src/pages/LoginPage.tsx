import { useState, type FormEvent } from "react";
import { Terminal } from "lucide-react";

import { ApiError } from "../api/client";
import { useAuth } from "../hooks/useAuth";

type Mode = "login" | "register";

export function LoginPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>("login");
  const [organizationName, setOrganizationName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login({ email, password });
      } else {
        await register({
          organization_name: organizationName,
          full_name: fullName,
          email,
          password
        });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to reach NexusOps API");
    } finally {
      setSubmitting(false);
    }
  }

  function switchMode(next: Mode) {
    setMode(next);
    setError(null);
  }

  return (
    <div className="min-h-screen bg-canvas text-slate-100 flex flex-col justify-center px-4 py-12">
      <div className="mx-auto w-full max-w-sm">
        <div className="mb-8 flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-panel text-slate-200">
            <Terminal className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-semibold tracking-tight text-slate-100">NexusOps</p>
            <p className="text-xs text-slate-400">Incident Intelligence Platform</p>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-surface p-6">
          <div
            role="tablist"
            aria-label="Authentication mode"
            className="mb-5 flex rounded-md border border-border bg-canvas p-0.5 text-xs font-medium"
          >
            <button
              type="button"
              role="tab"
              aria-selected={mode === "login"}
              onClick={() => switchMode("login")}
              className={`flex-1 rounded py-1.5 transition-colors ${
                mode === "login" ? "bg-panel text-slate-100" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === "register"}
              onClick={() => switchMode("register")}
              className={`flex-1 rounded py-1.5 transition-colors ${
                mode === "register"
                  ? "bg-panel text-slate-100"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Create organization
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <>
                <div>
                  <label htmlFor="org-name" className="block text-xs font-medium text-slate-300">
                    Organization name
                  </label>
                  <input
                    id="org-name"
                    type="text"
                    required
                    minLength={2}
                    value={organizationName}
                    onChange={(e) => setOrganizationName(e.target.value)}
                    placeholder="Acme Infrastructure"
                    className="mt-1.5 w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label htmlFor="full-name" className="block text-xs font-medium text-slate-300">
                    Full name
                  </label>
                  <input
                    id="full-name"
                    type="text"
                    required
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Ada Lovelace"
                    className="mt-1.5 w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </>
            )}

            <div>
              <label htmlFor="email" className="block text-xs font-medium text-slate-300">
                Work email
              </label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ada@acme.io"
                className="mt-1.5 w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-xs font-medium text-slate-300">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={mode === "register" ? 12 : 1}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={mode === "register" ? "Minimum 12 characters" : "Enter your password"}
                className="mt-1.5 w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:outline-none"
              />
            </div>

            {error && (
              <div
                role="alert"
                className="rounded-md border border-red-900/60 bg-red-950/40 px-3 py-2 text-xs text-red-300"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
            >
              {submitting
                ? "Please wait..."
                : mode === "login"
                  ? "Sign in"
                  : "Create organization"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
