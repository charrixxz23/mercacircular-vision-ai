"use client";

import { Plus, Search } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { Badge, EmptyState, ErrorBox, LotTag, PageHeader, Spinner, StatusBadge, useRemote } from "@/components/ui";
import { api } from "@/lib/api";
import { useCatalog } from "@/lib/catalog";
import { dateShort, kg } from "@/lib/format";
import type { LotSummary } from "@/lib/types";

const PAGE = 25;

function LotsList() {
  const params = useSearchParams();
  const router = useRouter();
  const { catalog } = useCatalog();
  const [q, setQ] = useState(params.get("q") ?? "");
  const filters = {
    q: params.get("q") ?? "",
    status: params.get("status") ?? "",
    product: params.get("product") ?? "",
    area_id: params.get("area_id") ?? "",
    demo: params.get("demo") ?? "",
    page: Number(params.get("page") ?? "0"),
  };
  useEffect(() => setQ(filters.q), [filters.q]);

  const set = (key: string, value: string) => {
    const next = new URLSearchParams(params.toString());
    if (value) next.set(key, value); else next.delete(key);
    if (key !== "page") next.delete("page");
    router.replace(`/lotes?${next.toString()}`);
  };

  const query = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => { if (v && k !== "page") query.set(k, String(v)); });
  query.set("limit", String(PAGE));
  query.set("offset", String(filters.page * PAGE));
  const { data, error, loading, reload } = useRemote(() => api<{ total: number; items: LotSummary[] }>(`/api/lots?${query}`), [query.toString()]);
  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE)) : 1;
  const anyFilter = filters.q || filters.status || filters.product || filters.area_id || filters.demo;

  return (
    <>
      <PageHeader
        title="Lotes de excedentes"
        description="Busque por código, comerciante, procedencia u observaciones. Abra un lote para ver su historial completo."
        actions={<Link href="/lotes/nuevo" className="btn-primary"><Plus className="h-4 w-4" aria-hidden /> Registrar lote</Link>}
      />

      <form className="panel grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-[2fr_1fr_1fr_1fr_1fr]" role="search" onSubmit={(e) => { e.preventDefault(); set("q", q.trim()); }}>
        <div className="relative">
          <label className="sr-only" htmlFor="f-q">Buscar</label>
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
          <input id="f-q" className="input pl-9" type="search" placeholder="Buscar lote, comerciante, procedencia…" value={q} onChange={(e) => setQ(e.target.value)} onBlur={() => q.trim() !== filters.q && set("q", q.trim())} />
        </div>
        <div>
          <label className="sr-only" htmlFor="f-status">Estado</label>
          <select id="f-status" className="input" value={filters.status} onChange={(e) => set("status", e.target.value)}>
            <option value="">Todos los estados</option>
            {catalog?.statuses.map((s) => <option key={s.code} value={s.code}>{s.label}</option>)}
          </select>
        </div>
        <div>
          <label className="sr-only" htmlFor="f-product">Producto</label>
          <select id="f-product" className="input" value={filters.product} onChange={(e) => set("product", e.target.value)}>
            <option value="">Todos los productos</option>
            {catalog?.products.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
          </select>
        </div>
        <div>
          <label className="sr-only" htmlFor="f-area">Área</label>
          <select id="f-area" className="input" value={filters.area_id} onChange={(e) => set("area_id", e.target.value)}>
            <option value="">Todas las áreas</option>
            {catalog?.areas.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
        <div>
          <label className="sr-only" htmlFor="f-demo">Origen de los datos</label>
          <select id="f-demo" className="input" value={filters.demo} onChange={(e) => set("demo", e.target.value)}>
            <option value="">Demostrativos y propios</option>
            <option value="false">Solo registrados aquí</option>
            <option value="true">Solo demostrativos</option>
          </select>
        </div>
      </form>

      <div className="mt-4">
        {loading && !data && <Spinner />}
        {error && <ErrorBox message={error} onRetry={reload} />}
        {data && data.total === 0 && (
          <EmptyState
            title={anyFilter ? "Ningún lote coincide con los filtros" : "Todavía no hay lotes"}
            action={anyFilter ? <button className="btn-secondary" onClick={() => router.replace("/lotes")}>Quitar filtros</button>
              : <Link href="/lotes/nuevo" className="btn-primary">Registrar el primer lote</Link>}
          >
            {anyFilter ? "Pruebe con otro estado o producto, o quite la búsqueda." : "Registre un lote para comenzar a inspeccionar excedentes."}
          </EmptyState>
        )}
        {data && data.total > 0 && (
          <div className="panel overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] text-sm">
                <caption className="sr-only">Lotes registrados</caption>
                <thead className="table-head">
                  <tr>
                    <th className="px-4 py-2.5">Lote</th><th className="px-3 py-2.5">Producto</th><th className="px-3 py-2.5">Comerciante</th>
                    <th className="px-3 py-2.5">Área</th><th className="px-3 py-2.5 text-right">Peso</th><th className="px-3 py-2.5">Estado</th>
                    <th className="px-3 py-2.5">Incidencias</th><th className="px-4 py-2.5">Registro</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((l) => (
                    <tr key={l.code} className="border-b border-line last:border-0 hover:bg-sunken/50">
                      <td className="px-4 py-2.5"><span className="flex items-center gap-2"><LotTag code={l.code} href={`/lotes/${l.code}`} />{l.is_demo && <Badge>Demo</Badge>}</span></td>
                      <td className="px-3 py-2.5"><span className="mr-2 inline-block h-2 w-2 rounded-full align-middle" style={{ background: l.product.color }} aria-hidden />{l.product.name}</td>
                      <td className="max-w-[220px] truncate px-3 py-2.5">{l.merchant.name}</td>
                      <td className="px-3 py-2.5 text-muted">{l.area.name}</td>
                      <td className="px-3 py-2.5 text-right">{l.weight_kg ? kg(l.weight_kg) : <span className="text-warn-ink">pendiente</span>}</td>
                      <td className="px-3 py-2.5"><StatusBadge status={l.status} label={l.status_label} /></td>
                      <td className="px-3 py-2.5">{l.incidents.length ? <span className="flex flex-wrap gap-1">{l.incidents.map((i) => <Badge key={i} tone="warn">{catalog?.incident_labels[i] ?? i}</Badge>)}</span> : <span className="text-muted">—</span>}</td>
                      <td className="px-4 py-2.5 text-muted">{dateShort(l.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-3 text-sm">
              <span className="text-muted">{data.total} lotes · página {filters.page + 1} de {pages}</span>
              <span className="flex gap-2">
                <button className="btn-secondary" disabled={filters.page === 0} onClick={() => set("page", String(filters.page - 1))}>Anterior</button>
                <button className="btn-secondary" disabled={filters.page + 1 >= pages} onClick={() => set("page", String(filters.page + 1))}>Siguiente</button>
              </span>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

export default function LotsPage() {
  return <Suspense fallback={<Spinner />}><LotsList /></Suspense>;
}
