// Tipos de las respuestas de la API (ver docs/api.md).

export type Ref = { id: number; name: string };
export type ProductRef = { id: number; code: string; name: string; color: string };

export type Catalog = {
  products: (ProductRef & { in_model: boolean })[];
  merchants: (Ref & { is_demo: boolean })[];
  areas: Ref[];
  statuses: { code: string; label: string }[];
  destinations: { code: string; label: string }[];
  roles: string[];
  donation_roles: string[];
  actions: { code: string; label: string; description: string }[];
  scenarios: { id: string; title: string; description: string }[];
  incident_labels: Record<string, string>;
};

export type LotSummary = {
  code: string;
  product: ProductRef;
  merchant: Ref;
  area: Ref;
  origin: string | null;
  quantity: number | null;
  quantity_unit: string;
  weight_kg: number | null;
  status: string;
  status_label: string;
  destination: string | null;
  destination_label: string | null;
  recovered_kg: number | null;
  waste_kg: number | null;
  is_demo: boolean;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  images: number;
  inspections: number;
  last_recommendation: string | null;
  incidents: string[];
};

export type ImageInfo = { id: number; url: string; source: string; width: number; height: number; original_name: string | null; created_at: string };

export type QualityCheck = { code: string; label: string; status: "ok" | "advertencia" | "error"; value: number | null; threshold: string; message: string };
export type Region = { x: number; y: number; w: number; h: number; area_pct?: number; darkening?: number };

export type AnalysisResult = {
  mode: "ia" | "demo";
  scenario?: { id: string; title: string; description: string };
  image?: { width: number; height: number };
  quality: { summary: "buena" | "aceptable" | "insuficiente"; checks: QualityCheck[] };
  identification: {
    available: boolean;
    declared: string;
    predicted?: string;
    probability?: number;
    probabilities?: Record<string, number>;
    min_confidence?: number;
    reliable?: boolean;
    declared_in_model?: boolean;
    matches_declared?: boolean | null;
    model_version?: string;
    note?: string;
  };
  anomalies: { available: boolean; count: number; affected_pct: number | null; regions: Region[]; method: string; description?: string };
  observations: string[];
  limitations: string[];
  processing_ms: number;
};

export type Reason = { rule: string; text: string; level: "info" | "advertencia" | "critico" };
export type Recommendation = {
  code: string;
  title: string;
  summary: string;
  priority: "normal" | "alta";
  suggested_actions: string[];
  reasons: Reason[];
  requires_human_confirmation: boolean;
  disclaimer: string;
};

export type Inspection = {
  id: number;
  mode: "ia" | "demo";
  scenario: string | null;
  model_version: string | null;
  declared_product: string;
  predicted_product: string | null;
  prediction_score: number | null;
  quality_summary: string | null;
  anomaly_count: number;
  affected_pct: number | null;
  incidents: string[];
  result: AnalysisResult;
  recommendation: Recommendation;
  image: ImageInfo | null;
  annotated_url: string | null;
  processing_ms: number | null;
  performed_by: string | null;
  is_demo: boolean;
  created_at: string;
};

export type DecisionInfo = {
  id: number; action: string; action_label: string; actor: string; role: string; notes: string | null; kg: number | null;
  from_status: string; to_status: string; recommendation_code: string | null; followed_recommendation: boolean | null;
  is_demo: boolean; created_at: string;
};

export type LotEvent = {
  id: number; type: string; title: string; detail: string | null; actor: string | null; from_status: string | null;
  to_status: string | null; payload: Record<string, unknown>; created_at: string;
};

export type AvailableAction = {
  code: string; label: string; description: string; requires_kg: boolean; requires_confirmation: boolean;
  authorized_roles: string[]; suggested: boolean;
};

export type LotDetail = LotSummary & {
  observations: string | null;
  registered_by: string | null;
  inspected_at: string | null;
  decided_at: string | null;
  image_list: ImageInfo[];
  inspection_list: Inspection[];
  decision_list: DecisionInfo[];
  timeline: LotEvent[];
  current_recommendation: Recommendation | null;
  available_actions: AvailableAction[];
  editable: boolean;
};

export type Dashboard = {
  generado: string;
  kpis: {
    lotes_registrados: number; kg_registrados: number; pendientes_inspeccion: number; en_evaluacion_donacion: number;
    kg_donacion_confirmada: number; en_gestion_residuos: number; kg_residuos_confirmados: number;
    kg_recuperado_comercial: number; kg_observados: number; lotes_demo: number; lotes_reales: number;
  };
  por_estado: { estado: string; etiqueta: string; lotes: number }[];
  por_producto: { producto: string; codigo: string; color: string; lotes: number; kg: number }[];
  tendencia_semanal: { semana: string; kg_registrados: number; kg_donacion: number; kg_comercial: number; kg_residuos: number; lotes: number; incidencias: number }[];
  incidencias: { categoria: string; total: number }[];
  destinos: { destino: string; kg: number }[];
  historial_analisis: { id: number; lote: string; producto: string; modo: string; fecha: string; recomendacion: string; regiones: number; calidad: string; demo: boolean }[];
};

export type PeriodMetrics = {
  lotes_registrados: number; kg_registrados: number; kg_sin_peso: number; kg_observados: number;
  kg_por_producto: Record<string, number>; lotes_por_producto: Record<string, number>; inspecciones: number; inspecciones_ia: number;
  incidencias: Record<string, number>; kg_destino_confirmado: Record<string, number>;
  kg_recuperado_donacion: number; kg_recuperado_comercial: number; kg_merma_confirmada: number;
  tiempos_horas: { registro_a_inspeccion: number | null; inspeccion_a_decision: number | null; registro_a_cierre: number | null };
  decisiones: number; decisiones_siguen_recomendacion: number;
};

export type Report = {
  periodo: { desde: string; hasta: string; dias: number };
  periodo_anterior: { desde: string; hasta: string };
  actual: PeriodMetrics;
  anterior: PeriodMetrics;
  comparacion: Record<string, { actual: number; anterior: number; variacion_pct: number | null }>;
  lotes_pendientes: { lote: string; producto: string; estado: string; registrado: string; kg: number | null; demo: boolean }[];
  definiciones: Record<string, string>;
};
