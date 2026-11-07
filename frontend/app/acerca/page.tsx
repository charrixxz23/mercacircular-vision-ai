"use client";

import { RotateCcw } from "lucide-react";
import { useState } from "react";
import { DISCLAIMER } from "@/components/Shell";
import { ConfirmDialog, ErrorBox, PageHeader, useToast } from "@/components/ui";
import { api, errorText } from "@/lib/api";

const FLOW = [
  ["Problema", "Excedentes que pierden valor comercial y requieren una decisión: venta, donación o residuos."],
  ["Captura de datos", "Registro del lote (producto, comerciante, área, procedencia, peso) y fotografía."],
  ["Visión artificial", "Calidad de imagen, segmentación, identificación del producto y detección de manchas."],
  ["Análisis", "Reglas transparentes convierten el resultado en una recomendación con sus razones."],
  ["Decisión humana", "Una persona responsable confirma el destino; la donación exige personal autorizado."],
  ["Trazabilidad", "Cada evento queda con fecha, responsable y evidencia; el QR abre la ficha del lote."],
  ["Indicadores", "Volumen registrado, producto observado, recuperado y merma, medidos por separado."],
];

const GLOSSARY = [
  ["Volumen registrado", "Peso de los lotes de excedentes que entran al sistema."],
  ["Producto observado", "Peso de los lotes con al menos una incidencia en la inspección. No equivale a merma."],
  ["Recuperado", "Kilogramos confirmados por una persona como donación o comercialización tras revisión."],
  ["Merma confirmada", "Kilogramos confirmados como entregados a gestión de residuos."],
];

export default function AboutPage() {
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = async () => {
    setBusy(true);
    setError(null);
    try {
      const r = await api<{ lotes_demo: number }>("/api/demo/reset", { method: "POST" });
      toast(`Demostración restablecida: ${r.lotes_demo} lotes demostrativos.`);
      setOpen(false);
    } catch (e) {
      setError(errorText(e));
      setOpen(false);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader title="Acerca del proyecto" description={DISCLAIMER} />
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <section className="panel p-6">
            <h2 className="text-lg font-semibold">Caso de estudio: Merca Panamá</h2>
            <div className="mt-3 max-w-prose space-y-3 text-sm leading-relaxed">
              <p>
                Merca Panamá es el mercado mayorista de productos agrícolas de la República de Panamá. En un mercado de este tipo, durante la recepción,
                el almacenamiento y la venta, una parte del producto puede perder valor comercial o quedarse sin comprador, y hay que decidir qué hacer con ella.
              </p>
              <p>
                Este prototipo explora si la visión artificial y un sistema de información pueden apoyar esa decisión: documentar cada lote, señalar indicios
                visibles de deterioro y dejar trazabilidad de quién decidió qué. No supone que el mercado carezca de sistemas ni que sus procesos sean manuales;
                plantea una mejora que tendría que evaluarse en un piloto.
              </p>
              <p className="font-medium">
                No existe relación institucional, contrato ni autorización de Merca Panamá para este proyecto. Los comerciantes, personas y lotes precargados son ficticios.
              </p>
            </div>
          </section>

          <section className="panel p-6" aria-labelledby="flow-h">
            <h2 id="flow-h" className="text-lg font-semibold">Cómo funciona</h2>
            <ol className="mt-4 space-y-3">
              {FLOW.map(([t, d], i) => (
                <li key={t} className="grid grid-cols-[32px_1fr] gap-3 text-sm">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-leaf font-semibold text-field-ink">{i + 1}</span>
                  <span><strong>{t}.</strong> <span className="text-muted">{d}</span></span>
                </li>
              ))}
            </ol>
          </section>

          <section className="panel p-6" aria-labelledby="gl-h">
            <h2 id="gl-h" className="text-lg font-semibold">Glosario de indicadores</h2>
            <dl className="mt-3 grid gap-3 sm:grid-cols-2">
              {GLOSSARY.map(([t, d]) => (
                <div key={t} className="rounded-lg bg-sunken p-3"><dt className="text-sm font-semibold">{t}</dt><dd className="mt-1 text-sm text-muted">{d}</dd></div>
              ))}
            </dl>
          </section>
        </div>

        <aside className="space-y-6">
          <section className="panel p-5">
            <h2 className="text-base font-semibold">Restablecer la demostración</h2>
            <p className="mt-1 text-sm text-muted">Borra todos los lotes, fotos e inspecciones (también los que usted registró) y vuelve a cargar los datos demostrativos.</p>
            {error && <div className="mt-3"><ErrorBox message={error} /></div>}
            <button className="btn-danger mt-3" onClick={() => setOpen(true)}><RotateCcw className="h-4 w-4" aria-hidden /> Restablecer datos</button>
          </section>
          <section className="panel p-5 text-sm">
            <h2 className="text-base font-semibold">Licencias</h2>
            <p className="mt-1 text-muted">Código: MIT. Imágenes de ejemplo y pesos del modelo: derivados de Fruits-360 (Mihai Oltean), CC BY-SA 4.0. Ver LICENSE y demo-data/ATTRIBUTION.md.</p>
          </section>
        </aside>
      </div>

      <ConfirmDialog open={open} title="¿Restablecer la demostración?" confirmLabel="Borrar y restablecer" danger busy={busy} onConfirm={reset} onCancel={() => setOpen(false)}>
        Se eliminarán todos los lotes y sus fotos. Esta acción no se puede deshacer.
      </ConfirmDialog>
    </>
  );
}
