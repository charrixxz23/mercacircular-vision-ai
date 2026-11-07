"use client";

import { Loader2 } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { api, errorText } from "@/lib/api";
import { useCatalog } from "@/lib/catalog";
import type { LotDetail } from "@/lib/types";
import { useOperator } from "./Shell";
import { useTourAction } from "./tour";
import { ErrorBox, Spinner } from "./ui";

export type LotFormValues = {
  product_id: string; merchant_id: string; area_id: string; origin: string; quantity: string; quantity_unit: string;
  weight_kg: string; observations: string;
};

export const EMPTY: LotFormValues = { product_id: "", merchant_id: "", area_id: "", origin: "", quantity: "", quantity_unit: "cajas", weight_kg: "", observations: "" };

export function toPayload(v: LotFormValues) {
  return {
    product_id: Number(v.product_id), merchant_id: Number(v.merchant_id), area_id: Number(v.area_id),
    origin: v.origin.trim() || null, quantity: v.quantity ? Number(v.quantity) : null, quantity_unit: v.quantity_unit || "cajas",
    weight_kg: v.weight_kg ? Number(v.weight_kg) : null, observations: v.observations.trim() || null,
  };
}

/** Formulario de alta de lote. */
export function NewLotForm({ onCreated }: { onCreated: (lot: LotDetail) => void }) {
  const { catalog, error: catError } = useCatalog();
  const { operator } = useOperator();
  const [v, setV] = useState<LotFormValues>(EMPTY);
  const [registeredBy, setRegisteredBy] = useState(operator.name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => setRegisteredBy((r) => r || operator.name), [operator.name]);

  useTourAction({
    "fill-lot-form": () => {
      if (!catalog) return;
      const area = catalog.areas.find((a) => a.name.includes("Hortalizas")) ?? catalog.areas[0];
      setV({
        product_id: String(catalog.products.find((p) => p.code === "tomate")?.id ?? catalog.products[0].id),
        merchant_id: String(catalog.merchants[0].id), area_id: String(area.id), origin: "Coclé (Penonomé)", quantity: "12",
        quantity_unit: "cajas", weight_kg: "", observations: "Lote creado durante el recorrido guiado. Sin comprador al cierre.",
      });
      setRegisteredBy((r) => r || "Usuario de la demo");
    },
  });

  if (catError) return <ErrorBox message={catError} />;
  if (!catalog) return <Spinner />;
  const up = (k: keyof LotFormValues) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const lot = await api<LotDetail>("/api/lots", { method: "POST", json: { ...toPayload(v), registered_by: registeredBy.trim() || null } });
      onCreated(lot);
    } catch (err) {
      setError(errorText(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form data-tour="lot-form" onSubmit={submit} className="panel max-w-3xl p-6">
      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="l-product">Producto</label>
          <select id="l-product" className="input" required value={v.product_id} onChange={up("product_id")}>
            <option value="">Elija el producto</option>
            {catalog.products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="l-merchant">Comerciante</label>
          <select id="l-merchant" className="input" required value={v.merchant_id} onChange={up("merchant_id")}>
            <option value="">Elija el comerciante</option>
            {catalog.merchants.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <p className="hint">Comerciantes ficticios de la demostración.</p>
        </div>
        <div>
          <label className="label" htmlFor="l-area">Área o nave</label>
          <select id="l-area" className="input" required value={v.area_id} onChange={up("area_id")}>
            <option value="">Elija el área</option>
            {catalog.areas.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="l-origin">Procedencia</label>
          <input id="l-origin" className="input" maxLength={120} value={v.origin} onChange={up("origin")} placeholder="Provincia o finca" />
        </div>
        <div className="grid grid-cols-[1fr_120px] gap-2">
          <div>
            <label className="label" htmlFor="l-qty">Cantidad</label>
            <input id="l-qty" className="input" type="number" min="0" step="1" value={v.quantity} onChange={up("quantity")} />
          </div>
          <div>
            <label className="label" htmlFor="l-unit">Unidad</label>
            <select id="l-unit" className="input" value={v.quantity_unit} onChange={up("quantity_unit")}>
              {["cajas", "sacos", "racimos", "canastas", "unidades"].map((u) => <option key={u}>{u}</option>)}
            </select>
          </div>
        </div>
        <div>
          <label className="label" htmlFor="l-weight">Peso (kg)</label>
          <input id="l-weight" className="input" type="number" min="0.1" step="0.1" value={v.weight_kg} onChange={up("weight_kg")} placeholder="Puede registrarlo después" />
        </div>
        <div className="sm:col-span-2">
          <label className="label" htmlFor="l-obs">Observaciones</label>
          <textarea id="l-obs" className="input min-h-[88px]" maxLength={2000} value={v.observations} onChange={up("observations")} />
        </div>
        <div>
          <label className="label" htmlFor="l-by">Registrado por</label>
          <input id="l-by" className="input" maxLength={120} value={registeredBy} onChange={(e) => setRegisteredBy(e.target.value)} placeholder="Nombre de quien registra" />
        </div>
      </div>
      {error && <div className="mt-5"><ErrorBox message={error} /></div>}
      <div className="mt-6 flex gap-2">
        <button className="btn-primary" disabled={busy}>{busy && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />} Registrar lote</button>
      </div>
    </form>
  );
}
