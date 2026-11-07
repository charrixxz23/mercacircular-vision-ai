"use client";

import { Badge, ErrorBox, Notice, PageHeader, Spinner, useRemote } from "@/components/ui";
import { api } from "@/lib/api";
import { pct } from "@/lib/format";

type ClassMetrics = { precision: number; sensibilidad: number; f1: number; tasa_falsos_positivos: number; soporte: number };
type AnomProduct = {
  imagenes: number; sensibilidad: number; falsos_positivos_imagenes_limpias: number; precision_regiones: number | null;
  sensibilidad_por_severidad: Record<string, { detectadas: number; total: number; tasa: number | null }>;
};
type ModelCard = {
  loaded: boolean; error: string | null;
  classifier: { version: string; tipo: string; classes: string[]; min_confidence: number; licencia_pesos: string } | null;
  metrics: {
    clasificador?: {
      fecha_entrenamiento: string; entorno: Record<string, string>; dataset: { nombre: string; autor: string; url: string; licencia: string };
      particion: string; muestras: { entrenamiento: number; prueba: number; grupos_prueba: Record<string, string[]> };
      seleccion_modelo: { metodo: string; metrica: string; resultados: Record<string, number>; C_elegido: number };
      prueba: {
        exactitud: number; f1_macro: number; por_clase: Record<string, ClassMetrics>;
        matriz_confusion: { etiquetas: string[]; filas_real_columnas_predicho: number[][] };
        calibracion: { ece_10_bins: number; brier: number };
        umbral_confianza: { umbral: number; cobertura: number; exactitud_sobre_umbral: number };
        por_grupo: Record<string, { clase: string; n: number; exactitud: number }>;
      };
      nitidez: { umbral_error: number; umbral_advertencia: number; rechazadas_como_error: Record<string, number> };
    };
    anomalias?: { tipo: string; advertencia: string; parametros_elegidos: Record<string, number>; prueba_por_producto: Record<string, AnomProduct> };
  };
  rules: { id: string; nombre: string; condicion: string; efecto: string }[];
  limitations: string[];
  scenarios: { id: string; titulo: string; descripcion: string }[];
};

const NAME: Record<string, string> = { tomate: "Tomate", banano: "Banano", papa: "Papa", otro: "Otro" };

const STATUS = [
  ["Validación de calidad de imagen (resolución, nitidez, exposición, encuadre)", "real", "OpenCV; umbrales calibrados con desenfoque artificial."],
  ["Segmentación producto / fondo", "real", "Color del borde + k-means + morfología. Supone fondo uniforme."],
  ["Identificación tomate / banano / papa / otro", "real", "Regresión logística sobre 63 características; validada por grupos."],
  ["Detección de manchas oscuras con regiones", "real", "Heurística validada solo con manchas sintéticas."],
  ["Motor de reglas y decisiones humanas", "real", "Reglas R01–R09, estados, roles y confirmaciones."],
  ["Escenarios del modo demostrativo", "simulado", "Resultados escritos de antemano, siempre rotulados."],
  ["Historial de 12 semanas precargado", "simulado", "Datos sintéticos, marcados como demostrativos."],
  ["Detección de enfermedades, frescura interna o inocuidad", "futuro", "Requiere datos etiquetados y validación experta. No se ofrece."],
  ["Modelo entrenado con fotos de Merca Panamá", "futuro", "Requiere un piloto con autorización y un protocolo de captura."],
] as const;

export default function ModelPage() {
  const { data, error, loading, reload } = useRemote(() => api<ModelCard>("/api/model"));
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  if (!data) return null;
  const clf = data.metrics.clasificador;
  const an = data.metrics.anomalias;

  return (
    <>
      <PageHeader
        title="Modelo y validación"
        description="Qué hace realmente el análisis visual, con qué datos se entrenó, cómo se midió y dónde falla. Todas las cifras provienen de backend/models/metrics.json."
      />

      <section className="panel overflow-hidden" aria-labelledby="impl-h">
        <h2 id="impl-h" className="px-5 pt-5 text-lg font-semibold">Implementado, simulado y futuro</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead className="table-head"><tr><th className="px-5 py-2">Componente</th><th className="px-3 py-2">Estado</th><th className="px-5 py-2">Detalle</th></tr></thead>
            <tbody>
              {STATUS.map(([c, s, d]) => (
                <tr key={c} className="border-b border-line last:border-0">
                  <td className="px-5 py-2.5">{c}</td>
                  <td className="px-3 py-2.5">{s === "real" ? <Badge tone="ok">Implementado</Badge> : s === "simulado" ? <Badge tone="warn">Simulado</Badge> : <Badge>Trabajo futuro</Badge>}</td>
                  <td className="px-5 py-2.5 text-muted">{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {!data.loaded && <div className="mt-6"><Notice tone="crit">Modelo no cargado: {data.error}</Notice></div>}

      {clf && (
        <section className="mt-6 space-y-6" aria-labelledby="clf-h">
          <div className="panel p-5">
            <h2 id="clf-h" className="text-lg font-semibold">Clasificador de producto {data.classifier && <Badge>{data.classifier.version}</Badge>}</h2>
            <p className="mt-1 max-w-3xl text-sm text-muted">
              {data.classifier?.tipo}. Datos: {clf.dataset.nombre} ({clf.dataset.autor}, {clf.dataset.licencia}), fotografías de laboratorio sobre fondo blanco que
              se colocan sobre fondos aleatorios antes de procesarlas. Partición {clf.particion}. Entrenamiento: {clf.muestras.entrenamiento} imágenes; prueba: {clf.muestras.prueba}.
            </p>
            <dl className="mt-4 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-line bg-line sm:grid-cols-4 [&>div]:bg-surface [&>div]:p-4">
              <div><dt className="text-xs text-muted">Exactitud en prueba</dt><dd className="font-display text-2xl font-semibold">{pct(clf.prueba.exactitud)}</dd></div>
              <div><dt className="text-xs text-muted">F1 macro</dt><dd className="font-display text-2xl font-semibold">{clf.prueba.f1_macro.toFixed(2)}</dd></div>
              <div><dt className="text-xs text-muted">Error de calibración (ECE)</dt><dd className="font-display text-2xl font-semibold">{clf.prueba.calibracion.ece_10_bins.toFixed(3)}</dd></div>
              <div><dt className="text-xs text-muted">Exactitud con probabilidad ≥ {pct(clf.prueba.umbral_confianza.umbral)}</dt>
                <dd className="font-display text-2xl font-semibold">{pct(clf.prueba.umbral_confianza.exactitud_sobre_umbral)}</dd>
                <dd className="text-xs text-muted">en el {pct(clf.prueba.umbral_confianza.cobertura)} de las imágenes</dd></div>
            </dl>
            <div className="mt-4"><Notice tone="warn">
              La papa tiene una sensibilidad de {pct(clf.prueba.por_clase.papa?.sensibilidad)}: con solo tres grabaciones de papa en el conjunto de datos, la papa roja de prueba se confunde con tomate u otros. Por eso el producto
              declarado por el operador prevalece y una discrepancia solo genera revisión humana.
            </Notice></div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="panel overflow-hidden">
              <h3 className="px-5 pt-5 text-base font-semibold">Métricas por clase (prueba)</h3>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="table-head"><tr><th className="px-5 py-2">Clase</th><th className="px-3 py-2 text-right">Sensibilidad</th><th className="px-3 py-2 text-right">Precisión</th><th className="px-3 py-2 text-right">Falsos positivos</th><th className="px-5 py-2 text-right">n</th></tr></thead>
                  <tbody>
                    {Object.entries(clf.prueba.por_clase).map(([c, m]) => (
                      <tr key={c} className="border-b border-line last:border-0">
                        <td className="px-5 py-2.5">{NAME[c] ?? c}</td><td className="px-3 py-2.5 text-right">{pct(m.sensibilidad)}</td>
                        <td className="px-3 py-2.5 text-right">{pct(m.precision)}</td><td className="px-3 py-2.5 text-right">{pct(m.tasa_falsos_positivos)}</td>
                        <td className="px-5 py-2.5 text-right">{m.soporte}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="px-5 py-3 text-xs text-muted">Falsos positivos: porcentaje de imágenes de otras clases asignadas a esta clase.</p>
            </div>

            <div className="panel p-5">
              <h3 className="text-base font-semibold">Matriz de confusión (filas: real · columnas: predicho)</h3>
              <ConfusionMatrix labels={clf.prueba.matriz_confusion.etiquetas} rows={clf.prueba.matriz_confusion.filas_real_columnas_predicho} />
            </div>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="panel p-5">
              <h3 className="text-base font-semibold">Exactitud por grupo de prueba</h3>
              <p className="text-sm text-muted">Cada grupo es una grabación que el modelo nunca vio. La variación entre grupos muestra cuánto depende de la variedad.</p>
              <ul className="mt-3 space-y-1.5 text-sm">
                {Object.entries(clf.prueba.por_grupo).sort((a, b) => a[1].clase.localeCompare(b[1].clase)).map(([g, v]) => (
                  <li key={g} className="grid grid-cols-[1fr_120px_48px] items-center gap-2">
                    <span className="truncate">{g} <span className="text-muted">({NAME[v.clase] ?? v.clase})</span></span>
                    <span className="h-2 rounded-full bg-sunken"><span className="block h-2 rounded-full bg-field" style={{ width: `${v.exactitud * 100}%` }} /></span>
                    <span className="text-right">{pct(v.exactitud)}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className="panel p-5">
              <h3 className="text-base font-semibold">Selección del modelo</h3>
              <p className="text-sm text-muted">{clf.seleccion_modelo.metodo}; métrica: {clf.seleccion_modelo.metrica}. Se eligió C = {clf.seleccion_modelo.C_elegido}.</p>
              <ul className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
                {Object.entries(clf.seleccion_modelo.resultados).map(([c, f]) => (
                  <li key={c} className={`rounded-lg px-3 py-2 ${Number(c) === clf.seleccion_modelo.C_elegido ? "bg-leaf font-semibold" : "bg-sunken"}`}>C = {c}: {f.toFixed(3)}</li>
                ))}
              </ul>
              <p className="mt-4 text-sm text-muted">
                Se compararon también una red neuronal pequeña, SVM, bosque aleatorio y boosting: ninguno superó de forma consistente a la regresión logística en la validación por grupos
                (ver docs/dataset-y-validacion.md), así que se conservó el modelo más simple e interpretable.
              </p>
              <p className="mt-3 text-xs text-muted">Entrenado el {clf.fecha_entrenamiento} · Python {clf.entorno.python} · scikit-learn {clf.entorno.scikit_learn} · OpenCV {clf.entorno.opencv}.</p>
            </div>
          </div>
        </section>
      )}

      {an && (
        <section className="panel mt-6 overflow-hidden" aria-labelledby="an-h">
          <h2 id="an-h" className="px-5 pt-5 text-lg font-semibold">Detector de manchas oscuras</h2>
          <div className="px-5 pt-2"><Notice tone="warn">{an.tipo}. {an.advertencia}</Notice></div>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="table-head"><tr><th className="px-5 py-2">Producto</th><th className="px-3 py-2 text-right">Sensibilidad manchas leves</th><th className="px-3 py-2 text-right">Sensibilidad manchas marcadas</th><th className="px-3 py-2 text-right">Falsos positivos (limpias)</th><th className="px-5 py-2 text-right">Precisión de regiones</th></tr></thead>
              <tbody>
                {Object.entries(an.prueba_por_producto).map(([p, m]) => (
                  <tr key={p} className="border-b border-line last:border-0">
                    <td className="px-5 py-2.5">{NAME[p]} <span className="text-muted">({m.imagenes} imágenes)</span></td>
                    <td className="px-3 py-2.5 text-right">{pct(m.sensibilidad_por_severidad.leve?.tasa ?? null)}</td>
                    <td className="px-3 py-2.5 text-right">{pct(m.sensibilidad_por_severidad.marcada?.tasa ?? null)}</td>
                    <td className="px-3 py-2.5 text-right">{pct(m.falsos_positivos_imagenes_limpias)}</td>
                    <td className="px-5 py-2.5 text-right">{pct(m.precision_regiones)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="px-5 py-3 text-xs text-muted">
            Parámetros elegidos con los grupos de entrenamiento: {Object.entries(an.parametros_elegidos).map(([k, v]) => `${k} = ${v}`).join(", ")}.
            El banano tiene muchos falsos positivos porque sus manchas naturales de maduración también son oscuras.
          </p>
        </section>
      )}

      <section className="panel mt-6 overflow-hidden" aria-labelledby="rules-h">
        <h2 id="rules-h" className="px-5 pt-5 text-lg font-semibold">Reglas del motor de decisiones</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="table-head"><tr><th className="px-5 py-2">Regla</th><th className="px-3 py-2">Condición</th><th className="px-5 py-2">Efecto</th></tr></thead>
            <tbody>
              {data.rules.map((r) => (
                <tr key={r.id} className="border-b border-line align-top last:border-0">
                  <td className="px-5 py-2.5"><span className="font-semibold">{r.id}</span> {r.nombre}</td>
                  <td className="px-3 py-2.5 text-muted">{r.condicion}</td><td className="px-5 py-2.5">{r.efecto}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="panel p-5" aria-labelledby="lim-h">
          <h2 id="lim-h" className="text-lg font-semibold">Limitaciones</h2>
          <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm">{data.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
        </section>
        <section className="panel p-5" aria-labelledby="sc-h">
          <h2 id="sc-h" className="text-lg font-semibold">Escenarios del modo demostrativo</h2>
          <ul className="mt-3 space-y-2 text-sm">{data.scenarios.map((s) => <li key={s.id}><strong>{s.titulo}.</strong> <span className="text-muted">{s.descripcion}</span></li>)}</ul>
        </section>
      </div>
    </>
  );
}

function ConfusionMatrix({ labels, rows }: { labels: string[]; rows: number[][] }) {
  const max = Math.max(...rows.flat(), 1);
  return (
    <div className="mt-3 overflow-x-auto">
      <table className="text-sm">
        <thead><tr><th className="p-2" /><th colSpan={labels.length} className="p-2 text-xs font-medium text-muted">predicho</th></tr>
          <tr><th className="p-2 text-left text-xs font-medium text-muted">real</th>{labels.map((l) => <th key={l} className="p-2 text-xs font-semibold">{NAME[l] ?? l}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              <th className="p-2 text-left text-xs font-semibold">{NAME[labels[i]] ?? labels[i]}</th>
              {r.map((v, j) => (
                <td key={j} className="h-14 w-16 border border-canvas text-center font-semibold"
                  style={{ background: i === j ? `rgba(78,138,47,${0.15 + 0.75 * (v / max)})` : `rgba(224,137,59,${(0.85 * v) / max})`, color: v / max > 0.55 ? "white" : undefined }}>
                  {v}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
