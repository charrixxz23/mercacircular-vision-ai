import { describe, expect, it } from "vitest";
import { hours, kg, pct, variation } from "@/lib/format";
import { TOUR_STEPS } from "@/lib/tour";

describe("formato", () => {
  it("formatea kilogramos y porcentajes en es-PA", () => {
    expect(kg(1234.5)).toMatch(/1.?235 kg|1.?234 kg/);
    expect(kg(null)).toBe("—");
    expect(pct(0.913)).toBe("91 %");
    expect(variation(null)).toBe("sin período anterior");
    expect(variation(12.5)).toMatch(/^\+12[.,]5 %$/);
  });
  it("convierte horas a la unidad legible", () => {
    expect(hours(0.5)).toBe("30 min");
    expect(hours(5)).toBe("5 h");
    expect(hours(72)).toBe("3 días");
  });
});

describe("recorrido guiado", () => {
  it("tiene los 10 pasos pedidos y cada paso apunta a un elemento", () => {
    expect(TOUR_STEPS).toHaveLength(10);
    for (const s of TOUR_STEPS) expect(s.target).toMatch(/^[a-z-]+$/);
  });
  it("usa el lote creado en las rutas de los pasos posteriores", () => {
    const inspeccion = TOUR_STEPS.find((s) => s.id === "imagen")!;
    expect(inspeccion.route({ lotCode: "MC-2026-0001" })).toBe("/inspeccion?lote=MC-2026-0001");
    expect(TOUR_STEPS.find((s) => s.id === "estado")!.route({ lotCode: "MC-2026-0001" })).toBe("/lotes/MC-2026-0001");
  });
  it("los pasos con acción automática esperan un evento", () => {
    for (const s of TOUR_STEPS.filter((x) => x.action && x.action.event !== "go-dashboard" && x.id !== "trazabilidad")) {
      expect(s.waitFor, s.id).toBeTruthy();
    }
  });
});
