"use client";

import { Camera, CircleDot, ClipboardCheck, FilePenLine, Gavel, Loader2, Printer, Scale, ScanSearch } from "lucide-react";
import QRCode from "qrcode";
import { useEffect, useState, type FormEvent } from "react";
import { api, errorText } from "@/lib/api";
import { useCatalog } from "@/lib/catalog";
import { dateTime, kg } from "@/lib/format";
import { emitTourDone } from "@/lib/tour";
import type { LotDetail, LotEvent } from "@/lib/types";
import { useOperator } from "./Shell";
import { useTourAction } from "./tour";
import { Badge, ErrorBox, LotTag, Notice, useToast } from "./ui";

// ─── Decisión humana ────────────────────────────────────────────────────────

export function DecisionForm({ lot, onDone }: { lot: LotDetail; onDone: (lot: LotDetail) => void }) {
  const { catalog } = useCatalog();
  const { operator } = useOperator();
  const toast = useToast();
  const actions = lot.available_actions.filter((a) => a.code !== "marcar_pendiente");
  const [action, setAction] = useState<string>("");
  const [actor, setActor] = useState(operator.name);
  const [role, setRole] = useState(operator.role);
  const [kgValue, setKg] = useState<string>("");
  const [confirm, setConfirm] = useState(false);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const selected = actions.find((a) => a.code === action);

  useEffect(() => { setActor((a) => a || operator.name); setRole((r) => r || operator.role); }, [operator]);
  useEffect(() => { if (selected?.requires_kg && lot.weight_kg && !kgValue) setKg(String(lot.weight_kg)); }, [selected, lot.weight_kg, kgValue]);

  useTourAction({
    "fill-decision": () => {
      const suggested = actions.find((a) => a.code === "enviar_evaluacion_donacion") ?? actions.find((a) => a.suggested) ?? actions[0];
      if (suggested) setAction(suggested.code);
      setActor((a) => a || "Usuario de la demo");
      setRole("Inspector(a) de calidad");
      setNotes("Decisión registrada durante el recorrido guiado.");
    },
  });

  if (!actions.length) {
    return (
      <section data-tour="decision" className="panel p-5">
        <h3 className="text-lg font-semibold">Decisión humana</h3>
        <p className="mt-2 text-sm text-muted">
          {lot.status === "cerrado" ? `Lote cerrado: ${lot.destination_label ?? ""}.` : "Primero registre una inspección para poder decidir el destino."}
        </p>
      </section>
    );
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!action) return setError("Elija una acción.");
    setBusy(true);
    try {
      const updated = await api<LotDetail>(`/api/lots/${lot.code}/decisions`, {
        method: "POST",
        json: { action, actor: actor.trim(), role, notes: notes || null, kg: selected?.requires_kg ? Number(kgValue) : null, confirm },
      });
      toast(`Decisión registrada: ${selected?.label}. Estado: ${updated.status_label}.`);
      setAction(""); setNotes(""); setConfirm(false); setKg("");
      onDone(updated);
      emitTourDone("decision-done");
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form data-tour="decision" onSubmit={submit} className="panel p-5" aria-labelledby="dec-h">
      <h3 id="dec-h" className="flex items-center gap-2 text-lg font-semibold"><Gavel className="h-5 w-5" aria-hidden /> Decisión humana</h3>
      <p className="mt-1 text-sm text-muted">La recomendación orienta; la decisión la registra una persona responsable.</p>

      <fieldset className="mt-4">
        <legend className="label">Acción</legend>
        <div className="grid gap-2">
          {actions.map((a) => (
            <label key={a.code} className={`flex cursor-pointer gap-3 rounded-lg border px-3 py-2.5 text-sm ${action === a.code ? "border-field bg-leaf/50" : "border-line hover:bg-sunken"}`}>
              <input type="radio" name="action" value={a.code} checked={action === a.code} onChange={() => setAction(a.code)} className="mt-1 accent-[rgb(var(--field))]" />
              <span>
                <span className="font-medium">{a.label}</span> {a.suggested && <Badge tone="ok">Sugerida por las reglas</Badge>}
                <span className="block text-xs text-muted">{a.description}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="dec-actor">Responsable</label>
          <input id="dec-actor" className="input" required minLength={2} value={actor} onChange={(e) => setActor(e.target.value)} placeholder="Nombre y apellido" />
        </div>
        <div>
          <label className="label" htmlFor="dec-role">Rol</label>
          <select id="dec-role" className="input" required value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="">Elija un rol</option>
            {(catalog?.roles ?? []).map((r) => <option key={r}>{r}</option>)}
          </select>
          {selected?.authorized_roles.length ? <p className="hint">Solo: {selected.authorized_roles.join(" o ")}.</p> : null}
        </div>
        {selected?.requires_kg && (
          <div>
            <label className="label" htmlFor="dec-kg">Kilogramos</label>
            <input id="dec-kg" className="input" type="number" min="0.1" step="0.1" required value={kgValue} onChange={(e) => setKg(e.target.value)} />
            <p className="hint">Peso del lote: {kg(lot.weight_kg)}.</p>
          </div>
        )}
        <div className={selected?.requires_kg ? "" : "sm:col-span-2"}>
          <label className="label" htmlFor="dec-notes">Notas</label>
          <input id="dec-notes" className="input" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Opcional" />
        </div>
      </div>

      {selected?.requires_confirmation && (
        <label className="mt-4 flex gap-3 rounded-lg border border-warn/40 bg-warn-bg px-3 py-3 text-sm text-warn-ink">
          <input type="checkbox" checked={confirm} onChange={(e) => setConfirm(e.target.checked)} className="mt-0.5" required />
          <span>Confirmo que personal autorizado evaluó la aptitud del producto para consumo. El sistema no certifica inocuidad.</span>
        </label>
      )}

      {error && <div className="mt-4"><ErrorBox message={error} /></div>}
      <button className="btn-primary mt-4" disabled={busy}>
        {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />} Registrar decisión
      </button>
    </form>
  );
}

// ─── Peso ───────────────────────────────────────────────────────────────────

export function WeightField({ lot, onSaved }: { lot: LotDetail; onSaved: (l: LotDetail) => void }) {
  const { operator } = useOperator();
  const toast = useToast();
  const [value, setValue] = useState(lot.weight_kg ? String(lot.weight_kg) : "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => setValue(lot.weight_kg ? String(lot.weight_kg) : ""), [lot.weight_kg]);

  const save = async (v = value) => {
    setError(null);
    if (!(Number(v) > 0)) return setError("Escriba un peso mayor que cero.");
    setBusy(true);
    try {
      const updated = await api<LotDetail>(`/api/lots/${lot.code}`, {
        method: "PATCH", json: { weight_kg: Number(v), actor: operator.name || "Usuario de la demo", reason: "Pesaje registrado durante la inspección" },
      });
      toast(`Peso registrado: ${kg(updated.weight_kg)}.`);
      onSaved(updated);
      emitTourDone("weight-saved");
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  useTourAction({ "set-weight": () => { setValue("240"); save("240"); } });

  return (
    <div data-tour="weight" className="panel p-5">
      <h3 className="flex items-center gap-2 text-base font-semibold"><Scale className="h-4 w-4" aria-hidden /> Peso del lote</h3>
      {!lot.weight_kg && <p className="mt-1 text-sm text-warn-ink">Peso pendiente: regístrelo antes de cerrar el lote.</p>}
      <form className="mt-3 flex flex-wrap items-end gap-2" onSubmit={(e) => { e.preventDefault(); save(); }}>
        <div className="w-40">
          <label className="label" htmlFor="w-kg">Kilogramos</label>
          <input id="w-kg" className="input" type="number" min="0.1" step="0.1" value={value} onChange={(e) => setValue(e.target.value)} disabled={!lot.editable} />
        </div>
        <button className="btn-secondary" disabled={busy || !lot.editable || Number(value) === lot.weight_kg}>
          {busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />} {lot.weight_kg ? "Actualizar peso" : "Registrar peso"}
        </button>
      </form>
      {error && <div className="mt-3"><ErrorBox message={error} /></div>}
    </div>
  );
}

// ─── Trazabilidad ───────────────────────────────────────────────────────────

const EVENT_ICON: Record<string, typeof CircleDot> = {
  creado: ClipboardCheck, editado: FilePenLine, peso: Scale, imagen: Camera, inspeccion: ScanSearch, decision: Gavel, estado: CircleDot,
};

export function Timeline({ events }: { events: LotEvent[] }) {
  return (
    <section data-tour="timeline" className="panel p-5" aria-labelledby="tl-h">
      <h2 id="tl-h" className="text-lg font-semibold">Línea de tiempo</h2>
      <ol className="mt-4">
        {[...events].reverse().map((e, i, arr) => {
          const Icon = EVENT_ICON[e.type] ?? CircleDot;
          return (
            <li key={e.id} className="relative flex gap-3 pb-5">
              {i < arr.length - 1 && <span className="absolute left-[15px] top-8 h-[calc(100%-1.75rem)] w-px bg-line" aria-hidden />}
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full border ${e.type === "decision" ? "border-field bg-leaf text-field-ink" : "border-line bg-sunken text-muted"}`}>
                <Icon className="h-4 w-4" aria-hidden />
              </span>
              <div className="min-w-0 pt-1 text-sm">
                <p className="font-medium">{e.title}</p>
                {e.detail && <p className="text-muted">{e.detail}</p>}
                <p className="mt-0.5 text-xs text-muted">{dateTime(e.created_at)}{e.actor ? ` · ${e.actor}` : ""}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

// ─── QR del lote ────────────────────────────────────────────────────────────

export function QrLabel({ lot }: { lot: LotDetail }) {
  const [src, setSrc] = useState<string | null>(null);
  const [url, setUrl] = useState("");
  useEffect(() => {
    const u = `${window.location.origin}/lotes/${lot.code}`;
    setUrl(u);
    QRCode.toDataURL(u, { margin: 1, width: 360, color: { dark: "#12372A", light: "#FFFFFF" } }).then(setSrc).catch(() => setSrc(null));
  }, [lot.code]);
  const local = url.includes("localhost") || url.includes("127.0.0.1");
  return (
    <section className="panel p-5" aria-labelledby="qr-h">
      <h2 id="qr-h" className="text-lg font-semibold">Identificador QR</h2>
      <div className="print-area mt-3 flex items-center gap-4 rounded-lg border border-dashed border-line p-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        {src && <img src={src} alt={`Código QR que abre la ficha del lote ${lot.code}`} className="h-28 w-28 rounded bg-white p-1" />}
        <div className="min-w-0 text-sm">
          <LotTag code={lot.code} />
          <p className="mt-2">{lot.product.name} · {kg(lot.weight_kg)}</p>
          <p className="text-xs text-muted">{lot.merchant.name}</p>
          <p className="mt-1 break-all text-xs text-muted">{url}</p>
        </div>
      </div>
      {local && (
        <div className="mt-3"><Notice tone="info">El QR apunta a <em>localhost</em>: para escanearlo con un teléfono, abra la app con la IP de esta computadora en la red local (ver README).</Notice></div>
      )}
      <button className="btn-secondary mt-3" onClick={() => window.print()}><Printer className="h-4 w-4" aria-hidden /> Imprimir etiqueta</button>
    </section>
  );
}
