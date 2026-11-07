// Formato de números y fechas en español de Panamá (zona horaria America/Panama).

const TZ = "America/Panama";

export const kg = (n: number | null | undefined, digits = 0) =>
  n === null || n === undefined ? "—" : `${n.toLocaleString("es-PA", { maximumFractionDigits: digits })} kg`;

export const num = (n: number | null | undefined, digits = 0) =>
  n === null || n === undefined ? "—" : n.toLocaleString("es-PA", { maximumFractionDigits: digits });

export const pct = (p: number | null | undefined, digits = 0) =>
  p === null || p === undefined ? "—" : `${(p * 100).toLocaleString("es-PA", { maximumFractionDigits: digits })} %`;

export const dateTime = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString("es-PA", { timeZone: TZ, day: "numeric", month: "short", year: "numeric", hour: "numeric", minute: "2-digit" }) : "—";

export const dateShort = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString("es-PA", { timeZone: TZ, day: "numeric", month: "short" }) : "—";

/** "lunes 2 nov" para una semana ISO (YYYY-MM-DD). */
export const weekLabel = (isoDate: string) => {
  const [y, m, d] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d, 12)).toLocaleDateString("es-PA", { timeZone: "UTC", day: "numeric", month: "short" });
};

export const hours = (h: number | null | undefined) => {
  if (h === null || h === undefined) return "—";
  if (h < 1) return `${Math.round(h * 60)} min`;
  if (h < 48) return `${h.toLocaleString("es-PA", { maximumFractionDigits: 1 })} h`;
  return `${(h / 24).toLocaleString("es-PA", { maximumFractionDigits: 1 })} días`;
};

export const variation = (v: number | null) =>
  v === null ? "sin período anterior" : `${v > 0 ? "+" : ""}${v.toLocaleString("es-PA", { maximumFractionDigits: 1 })} %`;

/** Fecha local de Panamá en formato YYYY-MM-DD, desplazada `days` días. */
export const isoDay = (days = 0) => {
  const now = new Date(Date.now() + days * 86400000);
  return now.toLocaleDateString("en-CA", { timeZone: TZ });
};

export const STATUS_TONE: Record<string, "neutral" | "info" | "warn" | "ok" | "crit"> = {
  registrado: "neutral",
  pendiente_inspeccion: "warn",
  inspeccionado: "info",
  revision_comercial: "info",
  evaluacion_donacion: "ok",
  gestion_residuos: "crit",
  cerrado: "neutral",
};

export const STATUS_ORDER = ["registrado", "pendiente_inspeccion", "inspeccionado", "revision_comercial", "evaluacion_donacion", "gestion_residuos", "cerrado"];
