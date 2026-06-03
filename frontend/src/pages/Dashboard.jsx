import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, formatApiError } from "@/lib/api";
import {
  CloudArrowUp, YoutubeLogo, FilmStrip, Trash, Sparkle,
  WaveSawtooth, CircleNotch, CheckCircle, WarningCircle,
} from "@phosphor-icons/react";
import AppShell from "@/components/AppShell";
import CookiesPanel from "@/components/CookiesPanel";

const STATUS_LABEL = {
  queued: "In coda",
  downloading: "Scaricamento",
  extracting: "Estrazione audio",
  transcribing: "Trascrizione",
  translating: "Traduzione",
  synthesizing: "Sintesi vocale",
  muxing: "Composizione video",
  done: "Pronto",
  error: "Errore",
};

function StatusBadge({ status }) {
  const isDone = status === "done";
  const isErr = status === "error";
  const isActive = !isDone && !isErr;
  const color = isDone ? "text-emerald-400 border-emerald-400/30 bg-emerald-400/5"
              : isErr ? "text-red-400 border-red-400/30 bg-red-400/5"
              : "text-[#FFB000] border-[#FFB000]/30 bg-[#FFB000]/5";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] tracking-[0.2em] uppercase border ${color}`}>
      {isActive && <CircleNotch size={10} className="animate-spin" weight="bold" />}
      {isDone && <CheckCircle size={11} weight="duotone" />}
      {isErr && <WarningCircle size={11} weight="duotone" />}
      {STATUS_LABEL[status] || status}
    </span>
  );
}

export default function Dashboard() {
  const [projects, setProjects] = useState([]);
  const [voices, setVoices] = useState([]);
  const [voice, setVoice] = useState("alloy");
  const [tab, setTab] = useState("upload"); // upload | youtube
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [title, setTitle] = useState("");
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState("");
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const loadProjects = async () => {
    try {
      const { data } = await api.get("/projects");
      setProjects(data);
    } catch {}
  };

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/voices");
        setVoices(data.voices);
      } catch {}
    })();
    loadProjects();
    const intv = setInterval(loadProjects, 4000);
    return () => clearInterval(intv);
  }, []);

  const submitUpload = async (e) => {
    e.preventDefault();
    setErr("");
    if (!file) {
      setErr("Seleziona un file video.");
      return;
    }
    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("voice", voice);
      if (title) fd.append("title", title);
      await api.post("/projects/upload", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setFile(null);
      setTitle("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadProjects();
      // Don't navigate away — let user queue more videos. They can click the row to view details.
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail) || e2.message);
    } finally {
      setSubmitting(false);
    }
  };

  const submitYoutube = async (e) => {
    e.preventDefault();
    setErr("");
    if (!youtubeUrl.trim()) {
      setErr("Inserisci un URL YouTube.");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/projects/youtube", {
        youtube_url: youtubeUrl.trim(),
        voice,
        title: title || undefined,
      });
      setYoutubeUrl("");
      setTitle("");
      await loadProjects();
      // Stay on dashboard so the user can queue another video right away.
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail) || e2.message);
    } finally {
      setSubmitting(false);
    }
  };

  const deleteProject = async (id) => {
    if (!window.confirm("Eliminare definitivamente questo progetto?")) return;
    try {
      await api.delete(`/projects/${id}`);
      await loadProjects();
    } catch {}
  };

  return (
    <AppShell>
      {/* Hero */}
      <section className="mb-12" data-testid="dashboard-hero">
        <div className="text-xs tracking-[0.3em] uppercase text-zinc-500 mb-3">Studio</div>
        <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-light tracking-tighter">
          Doppia un video in <span className="text-[#FFB000] italic font-normal">italiano</span>.
        </h1>
        <p className="mt-4 text-zinc-400 max-w-2xl">
          Carica un file MP4 o incolla un link YouTube. Pensiamo noi a trascrizione, traduzione e voce naturale italiana — fino a 30 minuti per video.
        </p>
      </section>

      {/* Create form */}
      <section className="mb-8" data-testid="create-section">
        <div className="bg-white/5 border border-white/10 rounded-lg overflow-hidden">
          <div className="flex border-b border-white/10">
            <button
              data-testid="tab-upload"
              onClick={() => setTab("upload")}
              className={`flex-1 px-6 py-4 text-sm tracking-wide flex items-center justify-center gap-2 transition-colors ${
                tab === "upload" ? "bg-white/5 text-white" : "text-zinc-400 hover:text-white"
              }`}
            >
              <CloudArrowUp size={18} weight="duotone" /> Carica file
            </button>
            <button
              data-testid="tab-youtube"
              onClick={() => setTab("youtube")}
              className={`flex-1 px-6 py-4 text-sm tracking-wide flex items-center justify-center gap-2 transition-colors border-l border-white/10 ${
                tab === "youtube" ? "bg-white/5 text-white" : "text-zinc-400 hover:text-white"
              }`}
            >
              <YoutubeLogo size={18} weight="duotone" /> Link YouTube
            </button>
          </div>

          <form
            onSubmit={tab === "upload" ? submitUpload : submitYoutube}
            className="p-6 md:p-8 grid md:grid-cols-12 gap-5"
          >
            {tab === "upload" ? (
              <div className="md:col-span-7">
                <label className="block text-xs tracking-[0.2em] uppercase text-zinc-500 mb-2">
                  Video sorgente
                </label>
                <label
                  htmlFor="file-input"
                  className="flex flex-col items-center justify-center gap-2 px-4 py-10 border-2 border-dashed border-white/10 rounded-md cursor-pointer hover:border-[#FFB000]/50 transition-colors bg-black/20"
                  data-testid="upload-dropzone"
                >
                  <CloudArrowUp size={28} weight="duotone" className="text-zinc-500" />
                  <div className="text-sm text-zinc-300">
                    {file ? file.name : "Clicca per scegliere un file (.mp4 / .mov / .webm)"}
                  </div>
                  <div className="text-[10px] tracking-[0.2em] uppercase text-zinc-600">
                    Max 30 minuti
                  </div>
                  <input
                    id="file-input"
                    ref={fileInputRef}
                    data-testid="upload-file-input"
                    type="file"
                    accept="video/*"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                </label>
              </div>
            ) : (
              <div className="md:col-span-7">
                <label className="block text-xs tracking-[0.2em] uppercase text-zinc-500 mb-2">
                  URL YouTube
                </label>
                <input
                  data-testid="youtube-url-input"
                  type="url"
                  value={youtubeUrl}
                  onChange={(e) => setYoutubeUrl(e.target.value)}
                  placeholder="https://www.youtube.com/watch?v=..."
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-md text-zinc-50 placeholder-zinc-600 focus:outline-none focus:border-[#FFB000] focus:ring-1 focus:ring-[#FFB000]"
                />
                <div className="mt-2 text-[10px] tracking-[0.2em] uppercase text-zinc-600">
                  Max 30 minuti — il video viene scaricato in 720p
                </div>
              </div>
            )}

            <div className="md:col-span-5 space-y-4">
              <div>
                <label className="block text-xs tracking-[0.2em] uppercase text-zinc-500 mb-2">
                  Titolo (opzionale)
                </label>
                <input
                  data-testid="project-title-input"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Es. Intervista Steve Jobs"
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-md text-zinc-50 placeholder-zinc-600 focus:outline-none focus:border-[#FFB000] focus:ring-1 focus:ring-[#FFB000]"
                />
              </div>
              <div>
                <label className="block text-xs tracking-[0.2em] uppercase text-zinc-500 mb-2">
                  Voce italiana
                </label>
                <select
                  data-testid="voice-select"
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                  className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-md text-zinc-50 focus:outline-none focus:border-[#FFB000] focus:ring-1 focus:ring-[#FFB000]"
                >
                  {voices.map((v) => (
                    <option key={v.id} value={v.id} className="bg-[#0A0B0E]">{v.label}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="md:col-span-12 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2 border-t border-white/5">
              {err ? (
                <div data-testid="create-error" className="text-sm text-red-400 border-l-2 border-red-500 pl-3">
                  {err}
                </div>
              ) : <div className="text-xs text-zinc-600 tracking-[0.2em] uppercase">Whisper → GPT → TTS → MP4</div>}

              <button
                data-testid="create-project-button"
                type="submit"
                disabled={submitting}
                className="px-6 py-3 bg-[#FFB000] hover:bg-[#FFD040] text-[#0A0B0E] font-medium rounded-md flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
              >
                <Sparkle size={16} weight="fill" />
                {submitting ? "Avvio..." : "Avvia doppiaggio"}
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* Projects list */}
      <CookiesPanel />
      <section data-testid="projects-section">
        <div className="flex items-end justify-between mb-6">
          <div>
            <div className="text-xs tracking-[0.3em] uppercase text-zinc-500 mb-2">Libreria</div>
            <h2 className="font-display text-2xl sm:text-3xl tracking-tight">
              I tuoi progetti
              <span className="ml-3 text-zinc-600 text-base">({projects.length})</span>
            </h2>
          </div>
        </div>

        {projects.length === 0 ? (
          <div
            className="border border-white/10 rounded-lg p-12 text-center bg-white/[0.02]"
            data-testid="empty-state"
          >
            <FilmStrip size={36} weight="duotone" className="text-zinc-600 mx-auto mb-4" />
            <div className="text-zinc-300 mb-1">Nessun progetto ancora.</div>
            <div className="text-sm text-zinc-500">Carica un video o incolla un link YouTube per iniziare.</div>
          </div>
        ) : (
          <div className="divide-y divide-white/5 border border-white/10 rounded-lg overflow-hidden bg-white/[0.02]">
            {projects.map((p) => {
              const isActive = !["done", "error"].includes(p.status);
              return (
                <div
                  key={p.id}
                  className={`px-5 md:px-6 py-4 hover:bg-white/[0.03] transition-colors relative ${
                    isActive ? "tracing-beam" : ""
                  }`}
                  data-testid={`project-row-${p.id}`}
                >
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-md bg-white/5 border border-white/10 flex items-center justify-center shrink-0">
                      {p.source_type === "youtube"
                        ? <YoutubeLogo size={18} weight="duotone" className="text-zinc-400" />
                        : <WaveSawtooth size={18} weight="duotone" className="text-zinc-400" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <Link
                        to={`/projects/${p.id}`}
                        data-testid={`project-link-${p.id}`}
                        className="font-medium truncate block hover:text-[#FFB000] transition-colors"
                      >
                        {p.title || "Senza titolo"}
                      </Link>
                      <div className="flex items-center gap-3 text-xs text-zinc-500 mt-1">
                        <span>{new Date(p.created_at).toLocaleString("it-IT")}</span>
                        {p.duration && <span>• {Math.round(p.duration)}s</span>}
                        <span className="hidden sm:inline">• voce {p.voice}</span>
                        {p.status === "queued" && p.queue_position > 1 && (
                          <span className="text-[#FFB000]" data-testid={`queue-pos-${p.id}`}>
                            • posizione {p.queue_position} in coda
                          </span>
                        )}
                        {p.step_detail && (
                          <span className="text-[#FFB000] hidden md:inline truncate" data-testid={`step-detail-${p.id}`}>
                            • {p.step_detail}
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="hidden sm:flex items-center gap-2 w-32">
                        <div className="h-1 flex-1 bg-white/5 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-[#FFB000] transition-all duration-500"
                            style={{ width: `${p.progress || 0}%` }}
                          />
                        </div>
                        <span className="text-[10px] text-zinc-500 tabular-nums w-8">{p.progress || 0}%</span>
                      </div>
                      <StatusBadge status={p.status} />
                      <button
                        data-testid={`delete-project-${p.id}`}
                        onClick={() => deleteProject(p.id)}
                        className="p-2 text-zinc-500 hover:text-red-400 transition-colors"
                        title="Elimina"
                      >
                        <Trash size={16} weight="duotone" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </AppShell>
  );
}
