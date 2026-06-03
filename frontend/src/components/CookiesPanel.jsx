import React, { useEffect, useRef, useState } from "react";
import { api, formatApiError } from "@/lib/api";
import { Cookie, Trash, CheckCircle, Info } from "@phosphor-icons/react";

export default function CookiesPanel() {
  const [status, setStatus] = useState({ has_cookies: false });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState(false);
  const fileRef = useRef(null);

  const refresh = async () => {
    try {
      const { data } = await api.get("/me/cookies");
      setStatus(data);
    } catch {}
  };

  useEffect(() => { refresh(); }, []);

  const onUpload = async (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    setBusy(true); setErr("");
    try {
      const fd = new FormData();
      fd.append("file", f);
      await api.post("/me/cookies", fd, { headers: { "Content-Type": "multipart/form-data" }});
      await refresh();
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail) || e2.message);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const onDelete = async () => {
    setBusy(true); setErr("");
    try {
      await api.delete("/me/cookies");
      await refresh();
    } catch (e2) {
      setErr(formatApiError(e2.response?.data?.detail) || e2.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mb-10 border border-white/10 rounded-lg bg-white/[0.02] overflow-hidden" data-testid="cookies-panel">
      <button
        data-testid="cookies-toggle"
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full px-5 md:px-6 py-3 flex items-center justify-between text-left hover:bg-white/[0.03] transition-colors"
      >
        <div className="flex items-center gap-3">
          <Cookie size={20} weight="duotone" className={status.has_cookies ? "text-emerald-400" : "text-zinc-500"} />
          <div>
            <div className="text-sm font-medium">Cookies YouTube</div>
            <div className="text-[11px] text-zinc-500 tracking-wide">
              {status.has_cookies
                ? "Cookies caricati — i download YouTube useranno la tua sessione"
                : "Per scaricare video da YouTube (anti-bot)"}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {status.has_cookies && (
            <span className="text-[10px] tracking-[0.2em] uppercase text-emerald-400 flex items-center gap-1">
              <CheckCircle size={12} weight="duotone" /> Attivi
            </span>
          )}
          <span className="text-zinc-500 text-xs">{open ? "Chiudi" : "Espandi"}</span>
        </div>
      </button>

      {open && (
        <div className="border-t border-white/10 p-5 md:p-6 space-y-4">
          <div className="flex items-start gap-3 text-sm text-zinc-400 bg-white/[0.02] border border-white/10 rounded-md p-4">
            <Info size={18} weight="duotone" className="text-[#FFB000] shrink-0 mt-0.5" />
            <div>
              YouTube blocca i download da molti server cloud. Per aggirare il blocco:
              <ol className="list-decimal list-inside mt-2 space-y-1 text-zinc-300 text-[13px]">
                <li>Installa l'estensione <span className="text-[#FFB000]">"Get cookies.txt LOCALLY"</span> su Chrome/Firefox.</li>
                <li>Apri <span className="text-[#FFB000]">youtube.com</span> mentre sei loggato.</li>
                <li>Clicca sull'estensione → esporta cookies in formato <span className="text-[#FFB000]">Netscape</span>.</li>
                <li>Carica qui il file <code className="px-1.5 py-0.5 bg-white/5 rounded text-[12px]">cookies.txt</code>.</li>
              </ol>
              <div className="mt-2 text-[12px] text-zinc-500">
                I cookies restano sul server solo per il tuo account e vengono usati esclusivamente per scaricare i video che richiedi.
              </div>
            </div>
          </div>

          {err && (
            <div data-testid="cookies-error" className="text-sm text-red-400 border-l-2 border-red-500 pl-3">
              {err}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <label
              htmlFor="cookies-file"
              data-testid="cookies-upload-label"
              className="px-4 py-2.5 bg-[#FFB000] hover:bg-[#FFD040] text-[#0A0B0E] text-sm font-medium rounded-md cursor-pointer transition-colors inline-flex items-center gap-2"
            >
              <Cookie size={16} weight="duotone" />
              {status.has_cookies ? "Sostituisci cookies" : "Carica cookies.txt"}
              <input
                id="cookies-file"
                ref={fileRef}
                data-testid="cookies-file-input"
                type="file"
                accept=".txt,text/plain"
                className="hidden"
                onChange={onUpload}
                disabled={busy}
              />
            </label>
            {status.has_cookies && (
              <button
                data-testid="cookies-delete-button"
                type="button"
                onClick={onDelete}
                disabled={busy}
                className="px-4 py-2.5 border border-white/10 hover:border-red-400/50 hover:text-red-400 text-sm text-zinc-400 rounded-md transition-colors inline-flex items-center gap-2"
              >
                <Trash size={14} weight="duotone" /> Rimuovi
              </button>
            )}
            {busy && <span className="text-xs text-zinc-500">Salvataggio...</span>}
            {status.has_cookies && (
              <span className="text-[11px] text-zinc-600 ml-auto">
                {Math.round(status.size / 1024)} KB •  {new Date(status.uploaded_at).toLocaleString("it-IT")}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
