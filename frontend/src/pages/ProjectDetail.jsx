import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, API } from "@/lib/api";
import AppShell from "@/components/AppShell";
import {
  ArrowLeft, Download, CircleNotch, CheckCircle, WarningCircle, FilmReel,
} from "@phosphor-icons/react";

const STAGES = [
  { id: "queued", label: "In coda" },
  { id: "downloading", label: "Download" },
  { id: "extracting", label: "Estrazione audio" },
  { id: "transcribing", label: "Trascrizione" },
  { id: "translating", label: "Traduzione" },
  { id: "synthesizing", label: "Sintesi vocale" },
  { id: "muxing", label: "Composizione" },
  { id: "done", label: "Pronto" },
];

function buildAuthedUrl(path) {
  const token = localStorage.getItem("dubita_token");
  // Append token as query param fallback (FastAPI Depends uses Authorization header from cookie).
  // For <video src> we cannot send Authorization header; rely on cookie.
  // But cookie is httpOnly cross-domain only with secure+samesite=none. We have that. So just return.
  return `${API}${path}`;
}

export default function ProjectDetail() {
  const { id } = useParams();
  const [p, setP] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancel = false;
    let timer;

    const load = async () => {
      try {
        const { data } = await api.get(`/projects/${id}`);
        if (cancel) return;
        setP(data);
        if (!["done", "error"].includes(data.status)) {
          timer = setTimeout(load, 3000);
        }
      } catch (e) {
        setErr(e.response?.data?.detail || "Progetto non trovato");
      }
    };
    load();
    return () => { cancel = true; if (timer) clearTimeout(timer); };
  }, [id]);

  if (err) {
    return (
      <AppShell>
        <div className="text-red-400" data-testid="project-error">{err}</div>
        <Link to="/" className="text-[#FFB000] hover:text-[#FFD040] mt-4 inline-block">← Torna ai progetti</Link>
      </AppShell>
    );
  }

  if (!p) {
    return (
      <AppShell>
        <div className="flex items-center gap-3 text-zinc-400">
          <CircleNotch size={20} className="animate-spin" />
          Caricamento...
        </div>
      </AppShell>
    );
  }

  const isDone = p.status === "done";
  const isErr = p.status === "error";
  const isActive = !isDone && !isErr;
  const stageIndex = STAGES.findIndex((s) => s.id === p.status);
  const segments = p.segments || [];

  return (
    <AppShell>
      <div className="mb-6">
        <Link
          to="/"
          data-testid="back-link"
          className="inline-flex items-center gap-2 text-zinc-500 hover:text-white transition-colors text-sm"
        >
          <ArrowLeft size={16} /> Tutti i progetti
        </Link>
      </div>

      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-10">
        <div>
          <div className="text-xs tracking-[0.3em] uppercase text-zinc-500 mb-2">Progetto</div>
          <h1
            className="font-display text-3xl sm:text-4xl lg:text-5xl font-light tracking-tighter break-words"
            data-testid="project-title"
          >
            {p.title || "Senza titolo"}
          </h1>
          <div className="text-xs text-zinc-500 mt-2 tracking-wide">
            {new Date(p.created_at).toLocaleString("it-IT")} •  voce <span className="text-[#FFB000]">{p.voice}</span>
            {p.duration && <> • {Math.round(p.duration)}s</>}
          </div>
        </div>
        {isDone && (
          <a
            data-testid="download-button"
            href={buildAuthedUrl(`/projects/${p.id}/video/dubbed`)}
            target="_blank"
            rel="noreferrer"
            className="px-5 py-3 bg-[#FFB000] hover:bg-[#FFD040] text-[#0A0B0E] font-medium rounded-md inline-flex items-center gap-2 transition-colors"
          >
            <Download size={16} weight="bold" /> Scarica MP4
          </a>
        )}
      </div>

      {/* Progress / status */}
      <section className={`mb-10 p-6 md:p-8 rounded-lg border bg-white/[0.03] ${
        isErr ? "border-red-500/30" : isDone ? "border-emerald-400/30" : "border-[#FFB000]/30 tracing-beam"
      }`} data-testid="status-card">
        <div className="flex items-center gap-3 mb-6">
          {isActive && <CircleNotch size={20} className="animate-spin text-[#FFB000]" />}
          {isDone && <CheckCircle size={20} weight="duotone" className="text-emerald-400" />}
          {isErr && <WarningCircle size={20} weight="duotone" className="text-red-400" />}
          <div className="font-display text-xl font-light">
            {isErr ? "Errore durante il doppiaggio" : isDone ? "Doppiaggio completato" : "Elaborazione in corso..."}
          </div>
          <div className="ml-auto text-sm tabular-nums text-zinc-400">{p.progress || 0}%</div>
        </div>

        <div className="h-1 bg-white/5 rounded-full overflow-hidden mb-6">
          <div
            className={`h-full transition-all duration-700 ${isErr ? "bg-red-500" : "bg-[#FFB000]"}`}
            style={{ width: `${p.progress || 0}%` }}
          />
        </div>

        {isErr ? (
          <div className="text-sm text-red-400 border-l-2 border-red-500 pl-3" data-testid="error-message">
            {p.error || "Si è verificato un errore sconosciuto."}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
            {STAGES.map((s, idx) => {
              const reached = stageIndex >= idx || isDone;
              const current = p.status === s.id;
              return (
                <div
                  key={s.id}
                  className={`px-3 py-2 text-[10px] tracking-[0.15em] uppercase border rounded-md text-center transition-colors ${
                    current ? "border-[#FFB000] text-[#FFB000] bg-[#FFB000]/5"
                    : reached ? "border-emerald-400/30 text-emerald-400/80"
                    : "border-white/10 text-zinc-600"
                  }`}
                >
                  {s.label}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Video player side-by-side (only if done) */}
      {isDone && (
        <section className="mb-12" data-testid="video-comparison">
          <div className="text-xs tracking-[0.3em] uppercase text-zinc-500 mb-3">Confronto</div>
          <h2 className="font-display text-2xl sm:text-3xl tracking-tight mb-6">Originale &amp; Italiano</h2>
          <div className="grid md:grid-cols-2 gap-5">
            <div className="border border-white/10 rounded-md overflow-hidden bg-black">
              <div className="px-4 py-2 border-b border-white/10 flex items-center justify-between">
                <span className="text-[11px] tracking-[0.2em] uppercase text-zinc-400">Originale</span>
                <span className="text-[10px] text-zinc-600">{p.transcript_language || "—"}</span>
              </div>
              <video
                data-testid="original-video"
                controls
                src={buildAuthedUrl(`/projects/${p.id}/video/source`)}
                className="w-full aspect-video bg-black"
              />
            </div>
            <div className="border border-[#FFB000]/30 rounded-md overflow-hidden bg-black">
              <div className="px-4 py-2 border-b border-[#FFB000]/30 flex items-center justify-between">
                <span className="text-[11px] tracking-[0.2em] uppercase text-[#FFB000]">Italiano</span>
                <span className="text-[10px] text-zinc-600">voce {p.voice}</span>
              </div>
              <video
                data-testid="dubbed-video"
                controls
                src={buildAuthedUrl(`/projects/${p.id}/video/dubbed`)}
                className="w-full aspect-video bg-black"
              />
            </div>
          </div>
        </section>
      )}

      {/* Transcript */}
      {segments.length > 0 && (
        <section data-testid="transcript-section">
          <div className="text-xs tracking-[0.3em] uppercase text-zinc-500 mb-3">Trascrizione</div>
          <h2 className="font-display text-2xl sm:text-3xl tracking-tight mb-6">Segmenti</h2>
          <div className="border border-white/10 rounded-md overflow-hidden">
            <div className="grid grid-cols-12 text-[10px] tracking-[0.2em] uppercase text-zinc-500 px-4 py-2 border-b border-white/10 bg-white/[0.02]">
              <div className="col-span-2">Time</div>
              <div className="col-span-5">{p.transcript_language?.toUpperCase() || "Originale"}</div>
              <div className="col-span-5">Italiano</div>
            </div>
            <div className="divide-y divide-white/5 max-h-[60vh] overflow-y-auto">
              {segments.map((s, i) => (
                <div key={i} className="grid grid-cols-12 gap-3 px-4 py-3 text-sm hover:bg-white/[0.02]">
                  <div className="col-span-2 text-[11px] text-zinc-500 tabular-nums">
                    {formatTime(s.start)} → {formatTime(s.end)}
                  </div>
                  <div className="col-span-5 text-zinc-300">{s.text}</div>
                  <div className="col-span-5 text-zinc-50">{s.text_it || <span className="text-zinc-600 italic">—</span>}</div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {!isDone && !isErr && segments.length === 0 && (
        <div className="text-center py-16 text-zinc-500 text-sm">
          <FilmReel size={32} weight="duotone" className="mx-auto text-zinc-600 mb-3" />
          La trascrizione apparirà qui non appena disponibile.
        </div>
      )}
    </AppShell>
  );
}

function formatTime(sec) {
  if (sec == null) return "0:00";
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}
