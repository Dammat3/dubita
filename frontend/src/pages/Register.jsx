import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { formatApiError } from "@/lib/api";
import { FilmReel, UserPlus } from "@phosphor-icons/react";

export default function Register() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    if (password.length < 6) {
      setErr("La password deve avere almeno 6 caratteri.");
      return;
    }
    setLoading(true);
    try {
      await register(email, password, name);
      navigate("/");
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail) || e2.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-6 bg-[#0A0B0E] grain" data-testid="register-page">
      <form onSubmit={onSubmit} className="w-full max-w-md relative z-10" data-testid="register-form">
        <Link to="/login" className="flex items-center gap-3 mb-10 group">
          <div className="w-10 h-10 rounded-md bg-[#FFB000] flex items-center justify-center transition-transform group-hover:rotate-6">
            <FilmReel size={22} weight="duotone" color="#0A0B0E" />
          </div>
          <div className="font-display text-2xl font-light">
            Dubita<span className="text-[#FFB000]">.</span>
          </div>
        </Link>

        <div className="text-xs tracking-[0.3em] uppercase text-zinc-500 mb-3">Nuovo account</div>
        <h2 className="font-display text-3xl lg:text-4xl font-light tracking-tighter mb-10">
          Inizia a doppiare.
        </h2>

        <div className="space-y-5">
          <div>
            <label className="block text-xs tracking-[0.2em] uppercase text-zinc-500 mb-2">Nome</label>
            <input
              data-testid="register-name-input"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Mario"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-md text-zinc-50 placeholder-zinc-600 focus:outline-none focus:border-[#FFB000] focus:ring-1 focus:ring-[#FFB000]"
            />
          </div>
          <div>
            <label className="block text-xs tracking-[0.2em] uppercase text-zinc-500 mb-2">Email</label>
            <input
              data-testid="register-email-input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="tu@email.it"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-md text-zinc-50 placeholder-zinc-600 focus:outline-none focus:border-[#FFB000] focus:ring-1 focus:ring-[#FFB000]"
            />
          </div>
          <div>
            <label className="block text-xs tracking-[0.2em] uppercase text-zinc-500 mb-2">Password</label>
            <input
              data-testid="register-password-input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Min. 6 caratteri"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-md text-zinc-50 placeholder-zinc-600 focus:outline-none focus:border-[#FFB000] focus:ring-1 focus:ring-[#FFB000]"
            />
          </div>

          {err && (
            <div data-testid="register-error" className="text-sm text-red-400 border-l-2 border-red-500 pl-3 py-1">
              {err}
            </div>
          )}

          <button
            data-testid="register-submit-button"
            type="submit"
            disabled={loading}
            className="w-full px-5 py-3.5 bg-[#FFB000] hover:bg-[#FFD040] text-[#0A0B0E] font-medium rounded-md flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            <UserPlus size={18} weight="bold" />
            {loading ? "Creazione..." : "Crea account"}
          </button>

          <div className="text-sm text-zinc-500 text-center pt-2">
            Hai già un account?{" "}
            <Link to="/login" data-testid="goto-login" className="text-[#FFB000] hover:text-[#FFD040]">Accedi</Link>
          </div>
        </div>
      </form>
    </div>
  );
}
