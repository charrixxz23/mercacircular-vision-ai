// Cliente mínimo de la API. Las rutas son relativas: Next.js las reenvía al backend.

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

function messageFrom(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      // Errores de validación de FastAPI
      return d.map((e: { loc?: string[]; msg?: string }) => `${(e.loc || []).slice(-1)[0] ?? "campo"}: ${e.msg}`).join(" · ");
    }
  }
  if (status === 502 || status === 503 || status === 500) {
    return "No hay conexión con el servidor de análisis. Verifique que el backend esté en ejecución (scripts/start-backend.ps1).";
  }
  return `Error ${status}`;
}

export async function api<T>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init || {};
  let res: Response;
  try {
    res = await fetch(path, {
      ...rest,
      headers: json !== undefined ? { "Content-Type": "application/json", ...(rest.headers || {}) } : rest.headers,
      body: json !== undefined ? JSON.stringify(json) : rest.body,
      cache: "no-store",
    });
  } catch {
    throw new ApiError("No se pudo contactar al servidor. Revise que el backend esté encendido.", 0);
  }
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = text;
  }
  if (!res.ok) throw new ApiError(messageFrom(res.status, body), res.status);
  return body as T;
}

export const errorText = (e: unknown) => (e instanceof Error ? e.message : String(e));
