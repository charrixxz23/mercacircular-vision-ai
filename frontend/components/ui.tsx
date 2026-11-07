"use client";

import { AlertTriangle, CheckCircle2, Info, Loader2, XCircle } from "lucide-react";
import Link from "next/link";
import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { STATUS_TONE } from "@/lib/format";

type Tone = "neutral" | "info" | "warn" | "ok" | "crit";
const TONES: Record<Tone, string> = {
  neutral: "bg-sunken text-ink border-line",
  info: "bg-info-bg text-info border-info/30",
  warn: "bg-warn-bg text-warn-ink border-warn/40",
  ok: "bg-leaf text-field-ink border-field/30",
  crit: "bg-crit-bg text-crit border-crit/30",
};

export function Badge({ tone = "neutral", children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function StatusBadge({ status, label }: { status: string; label: string }) {
  return <Badge tone={STATUS_TONE[status] ?? "neutral"}>{label}</Badge>;
}

export function DemoBadge() {
  return <Badge tone="neutral" title="Registro sintético precargado para la demostración">Demostrativo</Badge>;
}

/** Modo del análisis: siempre visible para no confundir IA real con escenario. */
export function ModeBadge({ mode }: { mode: "ia" | "demo" | string }) {
  return mode === "ia" ? (
    <Badge tone="ok" title="Inferencia con el modelo implementado">Modo IA real</Badge>
  ) : (
    <Badge tone="warn" title="Resultado predefinido; no lo generó un modelo">Modo demostrativo</Badge>
  );
}

/**
 * Marbete de lote: la etiqueta de cartón que cuelga de las cajas en el mercado.
 * Es el elemento de identidad de la interfaz.
 */
export function LotTag({ code, href, size = "md" }: { code: string; href?: string; size?: "md" | "lg" }) {
  const body = (
    <span
      className={`relative inline-flex items-center whitespace-nowrap rounded-tag border border-[rgb(var(--warn)/0.35)] bg-tag font-semibold text-deep shadow-[inset_0_-2px_0_rgb(0_0_0/0.06)] dark:text-ink ${
        size === "lg" ? "py-1.5 pl-7 pr-3 text-lg" : "py-0.5 pl-5 pr-2 text-xs"
      }`}
      style={{ fontVariantNumeric: "tabular-nums" }}
    >
      <span
        aria-hidden
        className={`absolute top-1/2 -translate-y-1/2 rounded-full border border-[rgb(var(--warn)/0.45)] bg-canvas ${size === "lg" ? "left-2 h-3 w-3" : "left-1.5 h-2 w-2"}`}
      />
      {code}
    </span>
  );
  return href ? (
    <Link href={href} className="rounded-tag hover:brightness-95" aria-label={`Abrir lote ${code}`}>
      {body}
    </Link>
  ) : (
    body
  );
}

export function Spinner({ label = "Cargando…" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center gap-2 py-8 text-sm text-muted">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> {label}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-wrap items-start gap-3 rounded-lg border border-crit/30 bg-crit-bg px-4 py-3 text-sm text-crit">
      <XCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <p className="flex-1">{message}</p>
      {onRetry && (
        <button className="font-semibold underline" onClick={onRetry}>
          Reintentar
        </button>
      )}
    </div>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn" | "ok" | "crit"; children: ReactNode }) {
  const Icon = { info: Info, warn: AlertTriangle, ok: CheckCircle2, crit: XCircle }[tone];
  return (
    <div className={`flex gap-3 rounded-lg border px-4 py-3 text-sm ${TONES[tone]}`}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-start gap-2 rounded-xl border border-dashed border-line px-6 py-10">
      <h3 className="text-base">{title}</h3>
      {children && <p className="max-w-prose text-sm text-muted">{children}</p>}
      {action}
    </div>
  );
}

export function PageHeader({ title, description, actions }: { title: string; description?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold sm:text-3xl">{title}</h1>
        {description && <p className="mt-1 max-w-3xl text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

// ─── Avisos (toasts) ─────────────────────────────────────────────────────────

type Toast = { id: number; text: string; tone: "ok" | "crit" | "info" };
const ToastCtx = createContext<(text: string, tone?: Toast["tone"]) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((text: string, tone: Toast["tone"] = "ok") => {
    const id = Date.now() + Math.random();
    setItems((x) => [...x, { id, text, tone }]);
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 4500);
  }, []);
  return (
    <ToastCtx.Provider value={push}>
      {children}
      <div aria-live="polite" role="status" className="pointer-events-none fixed bottom-4 left-4 z-[60] flex max-w-sm flex-col gap-2">
        {items.map((t) => (
          <div key={t.id} className={`pointer-events-auto rounded-lg border px-4 py-3 text-sm shadow-lg ${TONES[t.tone === "ok" ? "ok" : t.tone === "crit" ? "crit" : "info"]}`}>
            {t.text}
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}

// ─── Confirmación modal ─────────────────────────────────────────────────────

export function ConfirmDialog({
  open, title, children, confirmLabel, danger, busy, onConfirm, onCancel,
}: {
  open: boolean; title: string; children: ReactNode; confirmLabel: string; danger?: boolean; busy?: boolean;
  onConfirm: () => void; onCancel: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) d.showModal();
    if (!open && d.open) d.close();
  }, [open]);
  return (
    <dialog
      ref={ref}
      onCancel={(e) => { e.preventDefault(); onCancel(); }}
      className="w-[min(480px,calc(100%-2rem))] rounded-xl border border-line bg-surface p-0 text-ink backdrop:bg-black/40"
      aria-labelledby="confirm-title"
    >
      <div className="p-6">
        <h2 id="confirm-title" className="text-lg font-semibold">{title}</h2>
        <div className="mt-2 text-sm text-muted">{children}</div>
        <div className="mt-6 flex justify-end gap-2">
          <button className="btn-secondary" onClick={onCancel} autoFocus>Cancelar</button>
          <button className={danger ? "btn-danger" : "btn-primary"} onClick={onConfirm} disabled={busy}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />} {confirmLabel}
          </button>
        </div>
      </div>
    </dialog>
  );
}

// ─── Datos remotos ──────────────────────────────────────────────────────────

export function useRemote<T>(load: () => Promise<T>, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await load());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { reload(); }, [reload]);
  return { data, error, loading, reload, setData };
}
