"use client";

import Link from "next/link";
import { HorizontalBars, WeeklyTrend } from "@/components/charts";
import { Badge, ErrorBox, LotTag, ModeBadge, PageHeader, Spinner, useRemote } from "@/components/ui";
import { api } from "@/lib/api";
import { dateTime, kg, num } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

const STATUS_COLORS: Record<string, string> = {
  registrado: "#A7B0AA", pendiente_inspeccion: "#E0893B", inspeccionado: "#3A78AE", revision_comercial: "#6C9BC7",
  evaluacion_donacion: "#4E8A2F", gestion_residuos: "#C2412D", cerrado: "#2F4A3E",
};

function Kpi({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="min-w-0 px-5 py-4">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-1 font-display text-2xl font-semibold text-deep dark:text-ink">{value}</p>
      {note && <p className="mt-0.5 text-xs text-muted">{note}</p>}
    </div>
  );
}

function StatusPipeline({ data }: { data: Dashboard["por_estado"] }) {
  const total = data.reduce((s, d) => s + d.lotes, 0) || 1;
  return (
    <div>
      <div className="flex h-4 w-full overflow-hidden rounded-full bg-sunken" role="img"
        aria-label={data.map((d) => `${d.etiqueta}: ${d.lotes}`).join("; ")}>
        {data.filter((d) => d.lotes > 0).map((d) => (
          <div key={d.estado} style={{ width: `${(100 * d.lotes) / total}%`, background: STATUS_COLORS[d.estado] }} />
        ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-sm">
        {data.map((d) => (
          <li key={d.estado}>
            <Link href={`/lotes?status=${d.estado}`} className="flex items-center gap-2 rounded hover:underline">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: STATUS_COLORS[d.estado] }} aria-hidden />
              <span className="text-muted">{d.etiqueta}</span>
              <span className="font-semibold">{d.lotes}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function DashboardPage() {
  const { data, error, loading, reload } = useRemote(() => api<Dashboard>("/api/dashboard"));

  if (loading && !data) return <Spinner label="Calculando indicadores…" />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;
  const k = data.kpis;

  return (
    <>
      <PageHeader
        title="Panel de excedentes"
        description={
          <>
            {num(k.lotes_registrados)} lotes y {kg(k.kg_registrados)} registrados. Incluye {num(k.lotes_demo)} lotes demostrativos
            {k.lotes_reales ? ` y ${num(k.lotes_reales)} registrados en esta instalación` : ""}. Datos al {dateTime(data.generado)}
          </>
        }
        actions={<Link href="/inspeccion" className="btn-primary">Nueva inspección</Link>}
      />

      <section data-tour="kpis" aria-label="Indicadores principales"
        className="grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-line bg-line md:grid-cols-3 xl:grid-cols-6 [&>*]:bg-surface">
        <Kpi label="Lotes registrados" value={num(k.lotes_registrados)} />
        <Kpi label="Excedentes registrados" value={kg(k.kg_registrados)} note="volumen de entrada" />
        <Kpi label="Pendientes de inspección" value={num(k.pendientes_inspeccion)} note="registrados o en cola" />
        <Kpi label="En evaluación para donación" value={num(k.en_evaluacion_donacion)} note={`${kg(k.kg_donacion_confirmada)} donados (confirmados)`} />
        <Kpi label="En gestión de residuos" value={num(k.en_gestion_residuos)} note={`${kg(k.kg_residuos_confirmados)} confirmados como residuo`} />
        <Kpi label="Producto observado" value={kg(k.kg_observados)} note="lotes con incidencias (no es merma)" />
      </section>

      <section className="panel mt-6 p-5" aria-labelledby="pipeline-title">
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h2 id="pipeline-title" className="text-lg font-semibold">Lotes por estado</h2>
          <Link className="text-sm font-medium text-field-ink hover:underline" href="/lotes">Ver todos los lotes</Link>
        </div>
        <StatusPipeline data={data.por_estado} />
      </section>

      <div className="mt-6 grid gap-6 xl:grid-cols-3">
        <section className="panel p-5 xl:col-span-2" aria-labelledby="trend-title">
          <h2 id="trend-title" className="text-lg font-semibold">Tendencia semanal</h2>
          <p className="mb-3 text-sm text-muted">Destino confirmado por personas frente al volumen registrado, últimas 12 semanas.</p>
          <WeeklyTrend data={data.tendencia_semanal} />
        </section>
        <section className="panel p-5" aria-labelledby="prod-title">
          <h2 id="prod-title" className="text-lg font-semibold">Distribución por producto</h2>
          <p className="mb-3 text-sm text-muted">Kilogramos registrados.</p>
          <HorizontalBars data={data.por_producto.map((p) => ({ label: `${p.producto} (${p.lotes} lotes)`, value: p.kg, color: p.color }))} />
        </section>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="panel p-5" aria-labelledby="inc-title">
          <h2 id="inc-title" className="text-lg font-semibold">Incidencias detectadas</h2>
          <p className="mb-3 text-sm text-muted">Inspecciones con cada tipo de incidencia.</p>
          <HorizontalBars unit="n" color="#E0893B" data={data.incidencias.map((i) => ({ label: i.categoria, value: i.total }))} />
        </section>
        <section className="panel p-5" aria-labelledby="dest-title">
          <h2 id="dest-title" className="text-lg font-semibold">Destino confirmado</h2>
          <p className="mb-3 text-sm text-muted">Solo cuentan los kilogramos confirmados por un responsable.</p>
          <HorizontalBars data={data.destinos.map((d, i) => ({ label: d.destino, value: d.kg, color: ["#3A78AE", "#4E8A2F", "#E0893B"][i] }))} />
        </section>
      </div>

      <section className="panel mt-6 overflow-hidden" aria-labelledby="hist-title">
        <div className="flex flex-wrap items-baseline justify-between gap-2 px-5 pt-5">
          <h2 id="hist-title" className="text-lg font-semibold">Historial de análisis</h2>
          <Link className="text-sm font-medium text-field-ink hover:underline" href="/reportes">Ir a reportes</Link>
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="table-head">
              <tr>
                <th className="px-5 py-2">Lote</th><th className="px-3 py-2">Producto</th><th className="px-3 py-2">Modo</th>
                <th className="px-3 py-2">Recomendación</th><th className="px-3 py-2 text-right">Regiones</th><th className="px-5 py-2">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {data.historial_analisis.map((h) => (
                <tr key={h.id} className="border-b border-line last:border-0">
                  <td className="px-5 py-2.5"><LotTag code={h.lote} href={`/lotes/${h.lote}`} /></td>
                  <td className="px-3 py-2.5">{h.producto}</td>
                  <td className="px-3 py-2.5"><span className="flex flex-wrap gap-1"><ModeBadge mode={h.modo} />{h.demo && <Badge>Demostrativo</Badge>}</span></td>
                  <td className="px-3 py-2.5">{h.recomendacion}</td>
                  <td className="px-3 py-2.5 text-right">{h.regiones}</td>
                  <td className="px-5 py-2.5 text-muted">{dateTime(h.fecha)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}
