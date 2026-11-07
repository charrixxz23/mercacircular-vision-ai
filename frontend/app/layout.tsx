import "@fontsource-variable/bricolage-grotesque";
import "@fontsource-variable/public-sans";
import "./globals.css";

import type { Metadata, Viewport } from "next";
import Shell from "@/components/Shell";

export const metadata: Metadata = {
  title: { default: "MercaCircular Vision AI", template: "%s · MercaCircular Vision AI" },
  description:
    "Prototipo académico: identificación, análisis y gestión de excedentes agrícolas mediante visión artificial. Caso de estudio: Merca Panamá (sin relación institucional).",
  icons: { icon: "/icon.svg" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#12372A" },
    { media: "(prefers-color-scheme: dark)", color: "#0A1E17" },
  ],
};

// Aplica el tema guardado antes de pintar (evita el parpadeo claro → oscuro).
const themeScript = `try{var t=localStorage.getItem('mc-theme');if(t==='dark'||(!t&&matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('dark')}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-PA" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
