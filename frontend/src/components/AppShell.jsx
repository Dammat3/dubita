import React from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { FilmReel, SignOut, User as UserIcon } from "@phosphor-icons/react";
import { useAuth } from "@/lib/auth";

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-[#0A0B0E] text-zinc-50 grain">
      <header
        className="sticky top-0 z-40 bg-[#0A0B0E]/70 backdrop-blur-xl border-b border-white/10"
        data-testid="app-header"
      >
        <div className="max-w-7xl mx-auto px-6 lg:px-12 h-16 flex items-center justify-between">
          <Link
            to="/"
            data-testid="brand-link"
            className="flex items-center gap-3 group"
          >
            <div className="w-9 h-9 rounded-md bg-[#FFB000] flex items-center justify-center transition-transform duration-200 group-hover:rotate-6">
              <FilmReel size={20} weight="duotone" color="#0A0B0E" />
            </div>
            <div className="leading-none">
              <div className="font-display text-xl font-light tracking-tight">
                Dubita<span className="text-[#FFB000]">.</span>
              </div>
              <div className="text-[10px] tracking-[0.3em] uppercase text-zinc-500 mt-0.5">
                AI Italian Dubbing
              </div>
            </div>
          </Link>

          <nav className="flex items-center gap-2">
            <Link
              to="/"
              data-testid="nav-projects"
              className={`px-3 py-2 text-sm rounded-md transition-colors ${
                location.pathname === "/" ? "text-white" : "text-zinc-400 hover:text-white"
              }`}
            >
              Progetti
            </Link>
            <div className="hidden sm:flex items-center gap-2 px-3 py-2 text-xs text-zinc-400 border-l border-white/10 ml-2">
              <UserIcon size={14} weight="duotone" />
              <span data-testid="current-user-email">{user?.email}</span>
            </div>
            <button
              data-testid="logout-button"
              onClick={async () => { await logout(); navigate("/login"); }}
              className="ml-2 px-3 py-2 text-sm text-zinc-400 hover:text-white rounded-md flex items-center gap-2 transition-colors"
            >
              <SignOut size={16} weight="duotone" />
              <span className="hidden sm:inline">Esci</span>
            </button>
          </nav>
        </div>
      </header>

      <main className="relative z-10 max-w-7xl mx-auto px-6 lg:px-12 py-10">
        {children}
      </main>

      <footer className="border-t border-white/5 mt-20 py-8 text-center text-xs tracking-[0.2em] uppercase text-zinc-600">
        Dubita — Cinematic AI Dubbing
      </footer>
    </div>
  );
}
