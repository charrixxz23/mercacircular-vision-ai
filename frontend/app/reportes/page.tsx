"use client";

import { Download, FileText } from "lucide-react";
import { useState } from "react";
import { CompareBars } from "@/components/charts";
import { Badge, ErrorBox, LotTag, PageHeader, Spinner, useRemote } from "@/components/ui";
import { api } from "@/lib/api";
import { dateShort, hours, isoDay, kg, num, variation } from "@/lib/format";
import type { Report } from "@/lib/types";

const PRESETS = [
  { label: "Últimos 7 días", days: 7 },
  { label: "Últimas 4 semanas", days: 28 },
  { label: "Últimas 12 semanas", days: 84 },
];

const LABELS: Record<string, string> = {
  lotes_registrados: "Lotes registrados",
  kg_registrados: "Kg registrados (entrada)",
  kg_observados: "Kg observados con incidencias",
  kg_recuperado_donacion: "Kg donados (confirmados)",
  kg_recuperado_comercial: "Kg comercializados (confirmados)",
  kg_merma_confirmada: "Kg a residuos (confirmados)",
  inspecciones: "Inspecciones",
};

function toRows(a: Record<string, number>, b: Record<string, number>) {
  return Array.from(new Set([...Object.keys(a), ...Object.keys(b)])).map((k) => ({ label: k, actual: a[k] ?? 0, anterior: b[k] ?? 0 }));
}

export default function ReportsPage() {
  const [desde, setDesde] = useState(isoDay(-27));
  const [hasta, setHasta] = useState(isoDay(0));
  const qs = `desde=${desde}&hasta=${hasta}`;
  const { data, error, loading, reload } = useRemote(() => api<Report>(`/api/reports/summary?${qs}`), [qs]);

  return (
    <>
      <PageHeader
        title="Reportes e indicadores"
        description="Compare un período con el anterior de igual duración. Volumen registrado, producto observado, recuperado y merma se miden por separado."
      />

      <section className="panel flex flex-wrap items-end gap-4 p-4" aria-label="Período">
        <div>
          <label className="label" htmlFor="r-desde">Desde</label>
          <input id="r-desde" type="date" className="input" value={desde} max={hasta} onChange={(e) => setDesde(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="r-hasta">Hasta</label>
          <input id="r-hasta" type="date" className="input" value={hasta} min={desde} onChange={(e) => setHasta(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button key={p.days} className="btn-secondary" onClick={() => { setDesde(isoDay(-(p.days - 1))); setHasta(isoDay(0)); }}>{p.label}</button>
          ))}
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <a className="btn-primary" href={`/api/reports/summary.pdf?${qs}`}><FileText className="h-4 w-4" aria-hidden /> Resumen PDF</a>
          <a className="btn-secondary" href={`/api/reports/summary.csv?${qs}`}><Download className="h-4 w-4" aria-hidden /> Resumen CSV</a>
        </div>
      </section>

      <div className="mt-3 flex flex-wrap gap-2 text-sm">
        <span className="text-muted">Tablas completas (CSV):</span>
        <a className="font-medium text-field-ink underline" href="/api/reports/lotes.csv">Lotes</a>
        <a className="font-medium text-field-ink underline" href="/api/reports/inspecciones.csv">Inspecciones</a>
        <a className="font-medium text-field-ink underline" href="/api/reports/decisiones.csv">Decisiones</a>
      </div>

      {loading && !data && <Spinner label="Calculando el reporte…" />}
      {error && <div className="mt-4"><ErrorBox message={error} onRetry={reload} /></div>}
      {data && (
        <div className="mt-6 space-y-6">
          <section className="panel overflow-hidden" aria-labelledby="cmp-h">
            <h2 id="cmp-h" className="px-5 pt-5 text-lg font-semibold">Comparación entre períodos</h2>
            <p className="px-5 text-sm text-muted">
              Actual: {dateShort(data.periodo.desde + "T12:00:00Z")} a {dateShort(data.periodo.hasta + "T12:00:00Z")} ({data.periodo.dias} días).
              Anterior: {dateShort(data.periodo_anterior.desde + "T12:00:00Z")} a {dateShort(data.periodo_anterior.hasta + "T12:00:00Z")}.
            </p>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead className="table-head"><tr><th className="px-5 py-2">Indicador</th><th className="px-3 py-2 text-right">Actual</th><th className="px-3 py-2 text-right">Anterior</th><th className="px-5 py-2 text-right">Variación</th></tr></thead>
                <tbody>
                  {Object.entries(data.comparacion).map(([k, c]) => (
                    <tr key={k} className="border-b border-line last:border-0">
                      <td className="px-5 py-2.5">{LABELS[k] ?? k}{data.definiciones[k] && <span className="block text-xs text-muted">{data.definiciones[k]}</span>}</td>
                      <td className="px-3 py-2.5 text-right font-semibold">{num(c.actual, 1)}</td>
                      <td className="px-3 py-2.5 text-right">{num(c.anterior, 1)}</td>
                      <td className="px-5 py-2.5 text-right text-muted">{variation(c.variacion_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <section className="panel p-5" aria-labelledby="kgp-h">
              <h2 id="kgp-h" className="text-lg font-semibold">Kilogramos registrados por producto</h2>
              <CompareBars data={toRows(data.actual.kg_por_producto, data.anterior.kg_por_producto)} />
            </section>
            <section className="panel p-5" aria-labelledby="incc-h">
              <h2 id="incc-h" className="text-lg font-semibold">Incidencias por categoría</h2>
              <CompareBars data={toRows(data.actual.incidencias, data.anterior.incidencias)} />
            </section>
            <section className="panel p-5" aria-labelledby="dst-h">
              <h2 id="dst-h" className="text-lg font-semibold">Distribución de destinos (kg confirmados)</h2>
              <CompareBars data={toRows(data.actual.kg_destino_confirmado, data.anterior.kg_destino_confirmado)} />
            </section>
            <section className="panel p-5" aria-labelledby="time-h">
              <h2 id="time-h" className="text-lg font-semibold">Tiempos de procesamiento</h2>
              <p className="text-sm text-muted">Promedio de los lotes registrados en cada período.</p>
              <dl className="mt-4 grid gap-4 sm:grid-cols-3">
                {([["registro_a_inspeccion", "Registro a inspección"], ["inspeccion_a_decision", "Inspección a decisión"], ["registro_a_cierre", "Registro a cierre"]] as const).map(([k, l]) => (
                  <div key={k} className="rounded-lg bg-sunken p-3">
                    <dt className="text-xs text-muted">{l}</dt>
                    <dd className="mt-1 font-display text-xl font-semibold">{hours(data.actual.tiempos_horas[k])}</dd>
                    <dd className="text-xs text-muted">antes: {hours(data.anterior.tiempos_horas[k])}</dd>
                  </div>
                ))}
              </dl>
              <p className="mt-4 text-sm text-muted">
                {data.actual.decisiones} decisiones en el período; {data.actual.decisiones_siguen_recomendacion} siguieron una acción sugerida por las reglas.
              </p>
            </section>
          </div>

          <section className="panel overflow-hidden" aria-labelledby="pend-h">
            <h2 id="pend-h" className="px-5 pt-5 text-lg font-semibold">Lotes pendientes de inspección ({data.lotes_pendientes.length})</h2>
            {data.lotes_pendientes.length === 0 ? (
              <p className="px-5 pb-5 pt-2 text-sm text-muted">No hay lotes pendientes.</p>
            ) : (
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[560px] text-sm">
                  <thead className="table-head"><tr><th className="px-5 py-2">Lote</th><th className="px-3 py-2">Producto</th><th className="px-3 py-2">Estado</th><th className="px-3 py-2 text-right">Peso</th><th className="px-5 py-2">Registrado</th></tr></thead>
                  <tbody>
                    {data.lotes_pendientes.map((p) => (
                      <tr key={p.lote} className="border-b border-line last:border-0">
                        <td className="px-5 py-2.5"><span className="flex items-center gap-2"><LotTag code={p.lote} href={`/lotes/${p.lote}`} />{p.demo && <Badge>Demo</Badge>}</span></td>
                        <td className="px-3 py-2.5">{p.producto}</td><td className="px-3 py-2.5">{p.estado}</td>
                        <td className="px-3 py-2.5 text-right">{kg(p.kg)}</td><td className="px-5 py-2.5 text-muted">{dateShort(p.registrado)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </div>
      )}
    </>
  );
}
