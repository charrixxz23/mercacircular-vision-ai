// Pasos del recorrido guiado "Explorar MercaCircular".
// Cada paso usa funciones reales de la aplicación: las acciones del panel
// disparan eventos que las páginas escuchan (no hay pantallas simuladas).

export type TourState = { lotCode: string | null };

export type TourStep = {
  id: string;
  title: string;
  body: string;
  route: (s: TourState) => string;
  target: string;                         // valor de data-tour del elemento a resaltar
  action?: { label: string; event: string };
  waitFor?: string;                       // evento que avanza automáticamente
  needsLot?: boolean;
};

const lotRoute = (s: TourState, base: string) => (s.lotCode ? `${base}${base.includes("?") ? "&" : "?"}lote=${s.lotCode}` : base);

export const TOUR_STEPS: TourStep[] = [
  {
    id: "dashboard", title: "Panel de indicadores", route: () => "/", target: "kpis",
    body: "Todos los indicadores se calculan desde la base de datos. Los lotes precargados están marcados como demostrativos; los que usted registre se suman a ellos.",
  },
  {
    id: "lote", title: "Registrar un lote de tomates", route: () => "/lotes/nuevo", target: "lot-form",
    body: "Complete el formulario con datos de ejemplo y registre el lote. El peso se deja vacío a propósito: lo registraremos más adelante.",
    action: { label: "Completar con datos de ejemplo", event: "fill-lot-form" }, waitFor: "lot-created",
  },
  {
    id: "imagen", title: "Capturar o cargar una imagen", route: (s) => lotRoute(s, "/inspeccion"), target: "capture", needsLot: true,
    body: "Puede usar la cámara, subir una foto o tomar una imagen de ejemplo. La de ejemplo es un tomate de prueba con manchas sintéticas.",
    action: { label: "Usar imagen de ejemplo", event: "load-sample" }, waitFor: "image-ready",
  },
  {
    id: "analisis", title: "Ejecutar el análisis", route: (s) => lotRoute(s, "/inspeccion"), target: "analyze", needsLot: true,
    body: "El modo IA real valida la imagen, separa el producto del fondo, lo identifica con el modelo entrenado y busca manchas oscuras.",
    action: { label: "Analizar ahora", event: "run-analysis" }, waitFor: "analysis-done",
  },
  {
    id: "anomalias", title: "Revisar las anomalías", route: (s) => lotRoute(s, "/inspeccion"), target: "result-image", needsLot: true,
    body: "Las cajas naranjas son regiones que el detector marcó. Solo se dibujan cuando el algoritmo realmente las localiza; el modo demostrativo nunca dibuja regiones.",
  },
  {
    id: "peso", title: "Registrar el peso", route: (s) => lotRoute(s, "/inspeccion"), target: "weight", needsLot: true,
    body: "El motor de reglas pide el peso antes de cerrar el lote. Al registrarlo, el cambio queda en la trazabilidad con su responsable.",
    action: { label: "Registrar 240 kg", event: "set-weight" }, waitFor: "weight-saved",
  },
  {
    id: "recomendacion", title: "Recomendación y sus razones", route: (s) => lotRoute(s, "/inspeccion"), target: "recommendation", needsLot: true,
    body: "Cada recomendación muestra qué reglas se activaron. Es una sugerencia: no certifica inocuidad.",
  },
  {
    id: "decision", title: "Confirmar la decisión humana", route: (s) => lotRoute(s, "/inspeccion"), target: "decision", needsLot: true,
    body: "Una persona responsable elige el siguiente paso. Queda registrado quién decidió, con qué rol y si siguió la recomendación.",
    action: { label: "Completar decisión de ejemplo", event: "fill-decision" }, waitFor: "decision-done",
  },
  {
    id: "estado", title: "Estado actualizado del lote", route: (s) => (s.lotCode ? `/lotes/${s.lotCode}` : "/lotes"), target: "status", needsLot: true,
    body: "El lote pasó a evaluación para donación. La donación solo puede registrarla personal autorizado, confirmando la evaluación de aptitud.",
  },
  {
    id: "trazabilidad", title: "Trazabilidad e indicadores", route: (s) => (s.lotCode ? `/lotes/${s.lotCode}` : "/lotes"), target: "timeline", needsLot: true,
    body: "La línea de tiempo conserva cada evento con fecha y responsable, y el QR abre esta ficha. Vuelva al panel para ver los indicadores actualizados.",
    action: { label: "Ver indicadores actualizados", event: "go-dashboard" },
  },
];

export const TOUR_EVENT = "mc:tour-action";
export const TOUR_DONE = "mc:tour-done";

/** Dispara la acción de un paso (la escucha la página correspondiente). */
export function emitTourAction(event: string) {
  window.dispatchEvent(new CustomEvent(TOUR_EVENT, { detail: { event } }));
}

/** Avisa al recorrido que algo ocurrió (p. ej. que se creó el lote). */
export function emitTourDone(name: string, data?: Record<string, unknown>) {
  window.dispatchEvent(new CustomEvent(TOUR_DONE, { detail: { name, ...data } }));
}
