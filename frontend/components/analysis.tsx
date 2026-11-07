"use client";

import { AlertTriangle, CheckCircle2, Info, ShieldAlert, XCircle } from "lucide-react";
import { useState } from "react";
import { dateTime, pct } from "@/lib/format";
import type { Inspection, QualityCheck, Recommendation } from "@/lib/types";
import { Badge, ModeBadge, Notice } from "./ui";

const PRODUCT_LABEL: Record<string, string> = { tomate: "Tomate", banano: "Banano", papa: "Papa", otro: "Otro producto" };
const label = (c?: string | null) => (c ? PRODUCT_LABEL[c] ?? c : "—");

function CheckIcon({ status }: { status: QualityCheck["status"] }) {
  if (status === "ok") return <CheckCircle2 className="h-4 w-4 shrink-0 text-field-ink" aria-label="Correcto" />;
  if (status === "advertencia") return <AlertTriangle className="h-4 w-4 shrink-0 text-warn-ink" aria-label="Advertencia" />;
  return <XCircle className="h-4 w-4 shrink-0 text-crit" aria-label="Error" />;
}

/** Imagen original o anotada. Las regiones vienen dibujadas por el backend (salida real del detector). */
export function InspectionImage({ inspection }: { inspection: Inspection }) {
  const [showOriginal, setShowOriginal] = useState(false);
  const original = inspection.image?.url;
  const annotated = inspection.annotated_url;
  const src = showOriginal || !annotated ? original : annotated;
  return (
    <figure data-tour="result-image" className="panel overflow-hidden">
      <div className="relative flex min-h-[220px] items-center justify-center bg-sunken">
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt={annotated && !showOriginal ? "Imagen con el contorno del producto y las regiones marcadas" : "Fotografía del lote"}
            className="max-h-[420px] w-full object-contain" />
        ) : (
          <p className="px-6 py-10 text-sm text-muted">Sin imagen asociada a este análisis.</p>
        )}
        {inspection.mode === "demo" && (
          <p className="absolute inset-x-0 bottom-0 bg-warn-bg/95 px-4 py-2 text-xs font-medium text-warn-ink">
            Modo demostrativo: esta imagen no fue analizada; no hay regiones detectadas.
          </p>
        )}
      </div>
      <figcaption className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2.5 text-xs text-muted">
        {annotated ? (
          <>
            <span>
              <span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ background: "#14a080" }} aria-hidden />contorno del producto
              <span className="ml-4 mr-2 inline-block h-2.5 w-2.5 rounded-sm align-middle" style={{ background: "#ff8c00" }} aria-hidden />región marcada
            </span>
            <span className="inline-flex rounded-lg border border-line p-0.5" role="group" aria-label="Vista de la imagen">
              <button className={`rounded-md px-2.5 py-1 ${!showOriginal ? "bg-sunken font-semibold text-ink" : ""}`} aria-pressed={!showOriginal} onClick={() => setShowOriginal(false)}>Análisis</button>
              <button className={`rounded-md px-2.5 py-1 ${showOriginal ? "bg-sunken font-semibold text-ink" : ""}`} aria-pressed={showOriginal} onClick={() => setShowOriginal(true)}>Original</button>
            </span>
          </>
        ) : (
          <span>{inspection.image ? `${inspection.image.width} × ${inspection.image.height} px` : ""}</span>
        )}
      </figcaption>
    </figure>
  );
}

export function AnalysisDetails({ inspection }: { inspection: Inspection }) {
  const r = inspection.result;
  const ident = r.identification;
  const anom = r.anomalies;
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
        <ModeBadge mode={r.mode} />
        {ident.model_version && <Badge>modelo {ident.model_version}</Badge>}
        <span>{dateTime(inspection.created_at)}</span>
        {r.mode === "ia" && <span>{r.processing_ms} ms</span>}
      </div>

      {r.mode === "demo" && (
        <Notice tone="warn">
          <strong>Escenario demostrativo: {r.scenario?.title}.</strong> El resultado está escrito de antemano para mostrar el flujo;
          no lo generó un modelo y no describe la imagen cargada.
        </Notice>
      )}

      <section aria-labelledby="ident-h">
        <h3 id="ident-h" className="text-base font-semibold">Identificación del producto</h3>
        {ident.available ? (
          <div className="mt-2 space-y-3 text-sm">
            <p>
              Declarado: <strong>{label(ident.declared)}</strong>. Modelo: <strong>{label(ident.predicted)}</strong>{" "}
              con probabilidad {pct(ident.probability ?? null)}.{" "}
              {ident.reliable === false && <Badge tone="warn">Incierta (umbral {pct(ident.min_confidence ?? null)})</Badge>}
              {ident.reliable && ident.matches_declared === false && <Badge tone="warn">No coincide</Badge>}
              {ident.reliable && ident.matches_declared && <Badge tone="ok">Coincide</Badge>}
            </p>
            <ul className="space-y-1.5" aria-label="Probabilidad por clase">
              {Object.entries(ident.probabilities ?? {}).sort((a, b) => b[1] - a[1]).map(([c, p]) => (
                <li key={c} className="grid grid-cols-[110px_1fr_48px] items-center gap-2">
                  <span className="text-muted">{label(c)}</span>
                  <span className="h-2 rounded-full bg-sunken"><span className="block h-2 rounded-full bg-field" style={{ width: `${p * 100}%` }} /></span>
                  <span className="text-right">{pct(p)}</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-muted">{ident.note}</p>
          </div>
        ) : (
          <p className="mt-2 text-sm text-muted">{ident.note ?? "Identificación no disponible."} Se usa el producto declarado: <strong>{label(ident.declared)}</strong>.</p>
        )}
      </section>

      <section aria-labelledby="anom-h">
        <h3 id="anom-h" className="text-base font-semibold">Defectos exteriores visibles</h3>
        {anom.available ? (
          <div className="mt-2 text-sm">
            <p>
              {anom.count === 0 ? "No se marcaron regiones." : `${anom.count} región(es) marcada(s)`}
              {anom.affected_pct !== null && anom.count > 0 && ` · ${anom.affected_pct.toLocaleString("es-PA")} % del producto visible`}
            </p>
            {anom.description && <p className="mt-1 text-muted">{anom.description}</p>}
            {anom.regions.length > 0 && (
              <ol className="mt-2 grid gap-1 text-muted sm:grid-cols-2">
                {anom.regions.map((g, i) => (
                  <li key={i}>Región {i + 1}: {g.area_pct?.toLocaleString("es-PA")} % del área, oscurecimiento {g.darkening?.toLocaleString("es-PA")}</li>
                ))}
              </ol>
            )}
            <p className="mt-1 text-xs text-muted">Método: {anom.method}.</p>
          </div>
        ) : (
          <p className="mt-2 text-sm text-muted">No se pudo evaluar (no se encontró el producto en la imagen).</p>
        )}
      </section>

      <section aria-labelledby="qual-h">
        <h3 id="qual-h" className="text-base font-semibold">Calidad de la imagen: {r.quality.summary}</h3>
        <ul className="mt-2 space-y-1.5 text-sm">
          {r.quality.checks.map((c) => (
            <li key={c.code} className="flex gap-2">
              <CheckIcon status={c.status} />
              <span><strong className="font-medium">{c.label}.</strong> <span className="text-muted">{c.message}</span></span>
            </li>
          ))}
        </ul>
      </section>

      {r.observations.length > 0 && (
        <section aria-labelledby="obs-h">
          <h3 id="obs-h" className="text-base font-semibold">Observaciones</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">{r.observations.map((o, i) => <li key={i}>{o}</li>)}</ul>
        </section>
      )}

      <details className="rounded-lg border border-line px-4 py-3 text-sm">
        <summary className="cursor-pointer font-semibold">Limitaciones de este análisis ({r.limitations.length})</summary>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">{r.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
      </details>
    </div>
  );
}

export function RecommendationPanel({ rec }: { rec: Recommendation }) {
  const icon = { info: Info, advertencia: AlertTriangle, critico: ShieldAlert };
  const tone = { info: "text-info", advertencia: "text-warn-ink", critico: "text-crit" };
  return (
    <section data-tour="recommendation" className="panel p-5" aria-labelledby="rec-h">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 id="rec-h" className="text-lg font-semibold">{rec.title}</h3>
        <span className="flex gap-1">
          {rec.priority === "alta" && <Badge tone="crit">Prioridad alta</Badge>}
          <Badge tone="info">Requiere confirmación humana</Badge>
        </span>
      </div>
      <p className="mt-2 text-sm">{rec.summary}</p>
      <h4 className="mt-4 text-sm font-semibold">Por qué</h4>
      <ul className="mt-2 space-y-2 text-sm">
        {rec.reasons.map((r, i) => {
          const Icon = icon[r.level];
          return (
            <li key={i} className="flex gap-2">
              <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${tone[r.level]}`} aria-hidden />
              <span><span className="mr-1 rounded bg-sunken px-1.5 py-0.5 text-xs font-semibold text-muted">{r.rule}</span>{r.text}</span>
            </li>
          );
        })}
      </ul>
      <p className="mt-4 border-t border-line pt-3 text-xs text-muted">{rec.disclaimer}</p>
    </section>
  );
}
