import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { formatApiError } from "@/lib/api";
import { FilmReel, SignIn } from "@phosphor-icons/react";

const HERO_IMG =
  "https://images.unsplash.com/photo-1485846234645-a62644f84728?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2Nzd8MHwxfHNlYXJjaHwxfHxjaW5lbWF0aWMlMjBmaWxtJTIwY2xhcHBlcmJvYXJkfGVufDB8fHx8MTc4MDQ3Mjg2MXww&ixlib=rb-4.1.0&q=85";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const onSubmit = async (e) => {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail) || e2.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex" data-testid="login-page">
      {/* Left: cinematic image */}
      <div className="hidden lg:block lg:w-1/2 relative overflow-hidden">
        <img
          src={HERO_IMG}
          alt="cinematic"
          className="absolute inset-0 w-full h-full object-cover"
        />
        <div className="absolute inset-0 bg-[#0A0B0E]/80" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0A0B0E] via-transparent to-transparent" />
        <div className="absolute bottom-12 left-12 right-12 z-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-md bg-[#FFB000] flex items-center justify-center">
              <FilmReel size={22} weight="duotone" color="#0A0B0E" />
            </div>
            <div className="font-display text-2xl font-light">
              Dubita<span className="text-[#FFB000]">.</span>
            </div>
          </div>
          <h1 className="font-display text-4xl xl:text-5xl font-light tracking-tighter leading-tight">
            Trasforma qualsiasi video<br />
            in <span className="text-[#FFB000] italic font-normal">italiano</span> con un clic.
          </h1>
          <p className="mt-6 text-zinc-300 text-base leading-relaxed max-w-md">
            Trascrizione, traduzione e doppiaggio AI in voce italiana naturale. Carica un file o incolla un link YouTube.
          </p>
          <div className="mt-8 grid grid-cols-3 gap-3 text-xs tracking-[0.2em] uppercase text-zinc-500">
            <div className="border-t border-white/10 pt-3">Whisper STT</div>
            <div className="border-t border-white/10 pt-3">GPT Translate</div>
            <div className="border-t border-white/10 pt-3">OpenAI TTS</div>
          </div>
        </div>
      </div>

      {/* Right: form */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 lg:p-16 bg-[#0A0B0E]">
        <form
          onSubmit={onSubmit}
          className="w-full max-w-md"
          data-testid="login-form"
        >
          <div className="text-xs tracking-[0.3em] uppercase text-zinc-500 mb-3">
            Accedi
          </div>
          <h2 className="font-display text-3xl lg:text-4xl font-light tracking-tighter mb-10">
            Bentornato sul set.
          </h2>

          <div className="space-y-5">
            <div>
              <label className="block text-xs tracking-[0.2em] uppercase text-zinc-500 mb-2">Email</label>
              <input
                data-testid="login-email-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                placeholder="tu@email.it"
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-md text-zinc-50 placeholder-zinc-600 focus:outline-none focus:border-[#FFB000] focus:ring-1 focus:ring-[#FFB000] transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs tracking-[0.2em] uppercase text-zinc-500 mb-2">Password</label>
              <input
                data-testid="login-password-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="••••••••"
                className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-md text-zinc-50 placeholder-zinc-600 focus:outline-none focus:border-[#FFB000] focus:ring-1 focus:ring-[#FFB000] transition-colors"
              />
            </div>

            {err && (
              <div
                data-testid="login-error"
                className="text-sm text-red-400 border-l-2 border-red-500 pl-3 py-1"
              >
                {err}
              </div>
            )}

            <button
              data-testid="login-submit-button"
              type="submit"
              disabled={loading}
              className="w-full px-5 py-3.5 bg-[#FFB000] hover:bg-[#FFD040] text-[#0A0B0E] font-medium rounded-md flex items-center justify-center gap-2 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <SignIn size={18} weight="bold" />
              {loading ? "Accesso..." : "Entra in studio"}
            </button>

            <div className="text-sm text-zinc-500 text-center pt-2">
              Nuovo qui?{" "}
              <Link
                to="/register"
                data-testid="goto-register"
                className="text-[#FFB000] hover:text-[#FFD040] transition-colors"
              >
                Crea un account
              </Link>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
