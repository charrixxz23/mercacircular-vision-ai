/**
 * El frontend llama a rutas relativas (/api, /media, /samples) y Next.js las
 * reenvía al backend FastAPI. Así no hay problemas de CORS y el QR de un lote
 * funciona con cualquier dirección desde la que se abra la app.
 */
const BACKEND_URL = process.env.BACKEND_URL || "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // En el contenedor (Dockerfile) se compila como servidor autónomo y liviano.
  output: process.env.NEXT_OUTPUT === "standalone" ? "standalone" : undefined,
  async rewrites() {
    return ["api", "media", "samples"].map((p) => ({
      source: `/${p}/:path*`,
      destination: `${BACKEND_URL}/${p}/:path*`,
    }));
  },
};

export default nextConfig;
