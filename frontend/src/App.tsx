import { AuthProvider, useAuth } from "./hooks/useAuth";
import { LoginPage } from "./pages/LoginPage";

function AppContent() {
  const { user, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-canvas text-slate-400 flex items-center justify-center text-sm">
        Loading workspace...
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  return (
    <main className="min-h-screen bg-canvas text-slate-100 flex items-center justify-center p-6">
      <div className="w-full max-w-md rounded-lg border border-border bg-surface p-6">
        <p className="text-xs font-medium uppercase tracking-wider text-slate-400">Signed in</p>
        <h1 className="mt-1 text-lg font-semibold">{user.full_name}</h1>
        <p className="mt-1 text-sm text-slate-400">
          {user.email} · <span className="font-mono text-slate-300">{user.role}</span>
        </p>
        <button
          type="button"
          onClick={() => void logout()}
          className="mt-5 rounded-md border border-border bg-panel px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-800"
        >
          Sign out
        </button>
      </div>
    </main>
  );
}

export function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
