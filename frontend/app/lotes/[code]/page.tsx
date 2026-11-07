"use client";

import { Check, Loader2, Pencil, ScanSearch } from "lucide-react";
import Link from "next/link";
import { use, useState, type FormEvent } from "react";
import { AnalysisDetails, InspectionImage, RecommendationPanel } from "@/components/analysis";
import { EMPTY, type LotFormValues } from "@/components/LotForm";
import { DecisionForm, QrLabel, Timeline } from "@/components/lot";
import { useOperator } from "@/components/Shell";
import { Badge, ErrorBox, LotTag, ModeBadge, Notice, Spinner, StatusBadge, useRemote, useToast } from "@/components/ui";
import { api, errorText } from "@/lib/api";
import { useCatalog } from "@/lib/catalog";
import { dateTime, kg } from "@/lib/format";
import type { LotDetail } from "@/lib/types";

const PATH = [
  { code: "registrado", label: "Registrado" },
  { code: "pendiente_inspeccion", label: "Pendiente de inspección" },
  { code: "inspeccionado", label: "Inspeccionado" },
  { code: "decision", label: "Revisión o evaluación" },
  { code: "cerrado", label: "Cerrado" },
];
const DECISION_STATES = ["revision_comercial", "evaluacion_donacion", "gestion_residuos"];

function StatusPath({ lot }: { lot: LotDetail }) {
  const visited = new Set(lot.timeline.flatMap((e) => [e.from_status, e.to_status]).filter(Boolean) as string[]);
  visited.add(lot.status);
  const stage = (c: string) => (c === "decision" ? DECISION_STATES.some((s) => visited.has(s)) : visited.has(c));
  const current = DECISION_STATES.includes(lot.status) ? "decision" : lot.status;
  return (
    <section data-tour="status" className="panel p-5" aria-labelledby="path-h">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id="path-h" className="text-lg font-semibold">Estado del lote</h2>
        <StatusBadge status={lot.status} label={lot.status_label} />
      </div>
      <ol className="mt-4 grid gap-2 sm:grid-cols-5">
        {PATH.map((p) => {
          const done = stage(p.code);
          const isCurrent = current === p.code;
          return (
            <li key={p.code} aria-current={isCurrent ? "step" : undefined}
              className={`rounded-lg border px-3 py-2 text-sm ${isCurrent ? "border-field bg-leaf font-semibold text-field-ink" : done ? "border-line bg-sunken" : "border-dashed border-line text-muted"}`}>
              <span className="flex items-center gap-1.5">{done && !isCurrent && <Check className="h-3.5 w-3.5" aria-hidden />}{p.label}</span>
              {p.code === "decision" && DECISION_STATES.includes(lot.status) && <span className="block text-xs font-normal">{lot.status_label}</span>}
              {p.code === "cerrado" && lot.destination_label && <span className="block text-xs font-normal">{lot.destination_label}</span>}
            </li>
          );
        })}
      </ol>
      {lot.status === "cerrado" && (
        <p className="mt-3 text-sm text-muted">
          Cerrado el {dateTime(lot.closed_at)}.{" "}
          {lot.recovered_kg ? `Recuperado (confirmado): ${kg(lot.recovered_kg)}.` : ""} {lot.waste_kg ? `A residuos (confirmado): ${kg(lot.waste_kg)}.` : ""}
        </p>
      )}
    </section>
  );
}

function EditLot({ lot, onSaved, onCancel }: { lot: LotDetail; onSaved: (l: LotDetail) => void; onCancel: () => void }) {
  const { catalog } = useCatalog();
  const { operator } = useOperator();
  const [v, setV] = useState<LotFormValues>({
    ...EMPTY, product_id: String(lot.product.id), merchant_id: String(lot.merchant.id), area_id: String(lot.area.id), origin: lot.origin ?? "",
    quantity: lot.quantity?.toString() ?? "", quantity_unit: lot.quantity_unit, weight_kg: lot.weight_kg?.toString() ?? "", observations: lot.observations ?? "",
  });
  const [actor, setActor] = useState(operator.name);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const up = (k: keyof LotFormValues) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = {
      merchant_id: Number(v.merchant_id), area_id: Number(v.area_id), origin: v.origin, quantity: v.quantity ? Number(v.quantity) : null,
      quantity_unit: v.quantity_unit, observations: v.observations, actor: actor.trim(), reason: reason.trim() || null,
    };
    if (v.weight_kg) body.weight_kg = Number(v.weight_kg);
    if (!lot.inspections) body.product_id = Number(v.product_id);
    try {
      onSaved(await api<LotDetail>(`/api/lots/${lot.code}`, { method: "PATCH", json: body }));
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };
  if (!catalog) return <Spinner />;
  return (
    <form onSubmit={submit} className="mt-4 grid gap-4 sm:grid-cols-2">
      <div>
        <label className="label" htmlFor="e-product">Producto</label>
        <select id="e-product" className="input" value={v.product_id} onChange={up("product_id")} disabled={lot.inspections > 0}>
          {catalog.products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        {lot.inspections > 0 && <p className="hint">No se cambia el producto de un lote ya inspeccionado.</p>}
      </div>
      <div>
        <label className="label" htmlFor="e-merchant">Comerciante</label>
        <select id="e-merchant" className="input" value={v.merchant_id} onChange={up("merchant_id")}>
          {catalog.merchants.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
      </div>
      <div>
        <label className="label" htmlFor="e-area">Área</label>
        <select id="e-area" className="input" value={v.area_id} onChange={up("area_id")}>
          {catalog.areas.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
      </div>
      <div>
        <label className="label" htmlFor="e-origin">Procedencia</label>
        <input id="e-origin" className="input" value={v.origin} onChange={up("origin")} />
      </div>
      <div>
        <label className="label" htmlFor="e-qty">Cantidad ({v.quantity_unit})</label>
        <input id="e-qty" className="input" type="number" min="0" value={v.quantity} onChange={up("quantity")} />
      </div>
      <div>
        <label className="label" htmlFor="e-weight">Peso (kg)</label>
        <input id="e-weight" className="input" type="number" min="0.1" step="0.1" value={v.weight_kg} onChange={up("weight_kg")} />
      </div>
      <div className="sm:col-span-2">
        <label className="label" htmlFor="e-obs">Observaciones</label>
        <textarea id="e-obs" className="input" value={v.observations} onChange={up("observations")} />
      </div>
      <div>
        <label className="label" htmlFor="e-actor">Quién edita</label>
        <input id="e-actor" className="input" required minLength={2} value={actor} onChange={(e) => setActor(e.target.value)} />
      </div>
      <div>
        <label className="label" htmlFor="e-reason">Motivo del cambio</label>
        <input id="e-reason" className="input" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Queda en la trazabilidad" />
      </div>
      {error && <div className="sm:col-span-2"><ErrorBox message={error} /></div>}
      <div className="flex gap-2 sm:col-span-2">
        <button className="btn-primary" disabled={busy}>{busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />} Guardar cambios</button>
        <button type="button" className="btn-ghost" onClick={onCancel}>Cancelar</button>
      </div>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="mt-0.5 text-sm">{children || "—"}</dd>
    </div>
  );
}

export default function LotPage({ params }: { params: Promise<{ code: string }> }) {
  const { code } = use(params);
  const toast = useToast();
  const { data: lot, error, loading, reload, setData } = useRemote(() => api<LotDetail>(`/api/lots/${code}`), [code]);
  const [editing, setEditing] = useState(false);
  const [openInsp, setOpenInsp] = useState<number | null>(null);

  if (loading && !lot) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!lot) return null;

  return (
    <>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm text-muted"><Link href="/lotes" className="hover:underline">Lotes</Link> / ficha</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h1 className="sr-only">Lote {lot.code}</h1>
            <LotTag code={lot.code} size="lg" />
            <span className="font-display text-2xl font-semibold text-deep dark:text-ink">{lot.product.name}</span>
            {lot.is_demo && <Badge>Datos demostrativos</Badge>}
          </div>
        </div>
        {lot.status !== "cerrado" && (
          <Link href={`/inspeccion?lote=${lot.code}`} className="btn-primary"><ScanSearch className="h-4 w-4" aria-hidden /> Inspeccionar</Link>
        )}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_380px] [&>*]:min-w-0">
        <div className="space-y-6">
          <StatusPath lot={lot} />

          <section className="panel p-5" aria-labelledby="data-h">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 id="data-h" className="text-lg font-semibold">Datos del lote</h2>
              {lot.editable && !editing && <button className="btn-ghost" onClick={() => setEditing(true)}><Pencil className="h-4 w-4" aria-hidden /> Editar</button>}
            </div>
            {editing ? (
              <EditLot lot={lot} onCancel={() => setEditing(false)} onSaved={(l) => { setData(l); setEditing(false); toast("Cambios guardados."); }} />
            ) : (
              <dl className="mt-4 grid gap-4 sm:grid-cols-3">
                <Field label="Comerciante">{lot.merchant.name}</Field>
                <Field label="Área o nave">{lot.area.name}</Field>
                <Field label="Procedencia">{lot.origin}</Field>
                <Field label="Cantidad">{lot.quantity ? `${lot.quantity} ${lot.quantity_unit}` : null}</Field>
                <Field label="Peso registrado">{lot.weight_kg ? kg(lot.weight_kg) : <span className="text-warn-ink">pendiente</span>}</Field>
                <Field label="Destino final">{lot.destination_label}</Field>
                <Field label="Registrado">{`${dateTime(lot.created_at)}${lot.registered_by ? ` por ${lot.registered_by}` : ""}`}</Field>
                <Field label="Primera inspección">{lot.inspected_at ? dateTime(lot.inspected_at) : null}</Field>
                <Field label="Primera decisión">{lot.decided_at ? dateTime(lot.decided_at) : null}</Field>
                <div className="sm:col-span-3"><Field label="Observaciones">{lot.observations}</Field></div>
              </dl>
            )}
          </section>

          <section className="panel p-5" aria-labelledby="img-h">
            <h2 id="img-h" className="text-lg font-semibold">Evidencia fotográfica ({lot.image_list.length})</h2>
            {lot.image_list.length === 0 ? (
              <p className="mt-2 text-sm text-muted">Sin fotos. Agréguelas desde <Link className="font-medium text-field-ink underline" href={`/inspeccion?lote=${lot.code}`}>Inspección</Link>.</p>
            ) : (
              <ul className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
                {lot.image_list.map((img) => (
                  <li key={img.id}>
                    <a href={img.url} target="_blank" rel="noreferrer" className="block overflow-hidden rounded-lg border border-line">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={img.url} alt={`Foto del lote tomada el ${dateTime(img.created_at)}`} className="aspect-square w-full bg-sunken object-cover" />
                    </a>
                    <p className="mt-1 text-xs text-muted">{dateTime(img.created_at)}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="panel p-5" aria-labelledby="insp-h">
            <h2 id="insp-h" className="text-lg font-semibold">Inspecciones ({lot.inspection_list.length})</h2>
            {lot.inspection_list.length === 0 && <p className="mt-2 text-sm text-muted">Este lote todavía no se ha inspeccionado.</p>}
            <ul className="mt-3 space-y-3">
              {lot.inspection_list.map((insp, i) => {
                const open = openInsp === insp.id || (openInsp === null && i === 0);
                return (
                  <li key={insp.id} className="rounded-lg border border-line">
                    <button className="flex w-full flex-wrap items-center gap-2 px-4 py-3 text-left text-sm" aria-expanded={open} onClick={() => setOpenInsp(open ? -1 : insp.id)}>
                      <ModeBadge mode={insp.mode} />
                      <span className="font-medium">{insp.recommendation.title}</span>
                      <span className="text-muted">{insp.anomaly_count} región(es) · calidad {insp.quality_summary}</span>
                      <span className="ml-auto text-muted">{dateTime(insp.created_at)}</span>
                    </button>
                    {open && (
                      <div className="grid items-start gap-4 border-t border-line p-4 lg:grid-cols-2">
                        <InspectionImage inspection={insp} />
                        <AnalysisDetails inspection={insp} />
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="panel overflow-hidden" aria-labelledby="dec-list-h">
            <h2 id="dec-list-h" className="px-5 pt-5 text-lg font-semibold">Decisiones registradas</h2>
            {lot.decision_list.length === 0 ? (
              <p className="px-5 pb-5 pt-2 text-sm text-muted">Sin decisiones todavía.</p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[640px] text-sm">
                  <thead className="table-head"><tr><th className="px-5 py-2">Acción</th><th className="px-3 py-2">Responsable</th><th className="px-3 py-2 text-right">Kg</th><th className="px-3 py-2">¿Siguió la recomendación?</th><th className="px-5 py-2">Fecha</th></tr></thead>
                  <tbody>
                    {lot.decision_list.map((d) => (
                      <tr key={d.id} className="border-b border-line last:border-0">
                        <td className="px-5 py-2.5">{d.action_label}{d.notes && <span className="block text-xs text-muted">{d.notes}</span>}</td>
                        <td className="px-3 py-2.5">{d.actor}<span className="block text-xs text-muted">{d.role}</span></td>
                        <td className="px-3 py-2.5 text-right">{d.kg ?? "—"}</td>
                        <td className="px-3 py-2.5">{d.followed_recommendation === null ? "—" : d.followed_recommendation ? "Sí" : "No"}</td>
                        <td className="px-5 py-2.5 text-muted">{dateTime(d.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>

        <aside className="space-y-6" aria-label="Recomendación, decisión y trazabilidad">
          {lot.current_recommendation && <RecommendationPanel rec={lot.current_recommendation} />}
          {lot.status === "registrado" && (
            <Notice tone="info">El lote aún no tiene fotos. <Link className="font-semibold underline" href={`/inspeccion?lote=${lot.code}`}>Inspeccionarlo</Link></Notice>
          )}
          <DecisionForm lot={lot} onDone={setData} />
          <Timeline events={lot.timeline} />
          <QrLabel lot={lot} />
        </aside>
      </div>
    </>
  );
}
