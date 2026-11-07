"use client";

import {
  Boxes, Compass, FileBarChart2, FlaskConical, Info, LayoutDashboard, Menu, Moon, ScanSearch, Sun, UserRound, X,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { TourProvider, useTour } from "./tour";
import { ToastProvider } from "./ui";

const NAV = [
  { href: "/", label: "Panel", icon: LayoutDashboard },
  { href: "/inspeccion", label: "Inspección", icon: ScanSearch },
  { href: "/lotes", label: "Lotes", icon: Boxes },
  { href: "/reportes", label: "Reportes", icon: FileBarChart2 },
  { href: "/modelo", label: "Modelo y validación", icon: FlaskConical },
  { href: "/acerca", label: "Acerca del proyecto", icon: Info },
];

export const DISCLAIMER =
  "Prototipo académico independiente desarrollado como caso de estudio para Merca Panamá. No representa un sistema oficial de la institución.";

// ─── Persona que opera la demo (se usa para prellenar responsables) ─────────
type Operator = { name: string; role: string };
const OperatorCtx = createContext<{ operator: Operator; setOperator: (o: Operator) => void }>({
  operator: { name: "", role: "" }, setOperator: () => {},
});
export const useOperator = () => useContext(OperatorCtx);

function Logo() {
  // Isotipo propio: caja de mercado con una hoja que la atraviesa.
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8 shrink-0" aria-hidden>
      <rect x="3" y="11" width="26" height="17" rx="3" fill="rgb(var(--tag))" />
      <path d="M3 17h26" stroke="rgb(var(--deep))" strokeOpacity=".35" strokeWidth="1.5" />
      <path d="M9 14c3-9 12-11 19-10-1 8-6 14-15 13" fill="rgb(104 163 70)" />
      <path d="M10 17c4-4 9-7 14-9" stroke="rgb(var(--deep))" strokeWidth="1.5" fill="none" strokeLinecap="round" />
    </svg>
  );
}

function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => setDark(document.documentElement.classList.contains("dark")), []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try { localStorage.setItem("mc-theme", next ? "dark" : "light"); } catch { /* ignorar */ }
  };
  return (
    <button className="btn-ghost px-2.5" onClick={toggle} aria-label={dark ? "Usar tema claro" : "Usar tema oscuro"} title={dark ? "Tema claro" : "Tema oscuro"}>
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}

function OperatorButton() {
  const { operator, setOperator } = useOperator();
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(operator);
  useEffect(() => setDraft(operator), [operator]);
  return (
    <div className="relative">
      <button className="btn-ghost max-w-[220px] px-2.5" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-haspopup="dialog">
        <UserRound className="h-4 w-4 shrink-0" aria-hidden />
        <span className="truncate">{operator.name || "Identificarse"}</span>
      </button>
      {open && (
        <div role="dialog" aria-label="Persona que opera" className="absolute right-0 top-11 z-50 w-72 rounded-xl border border-line bg-surface p-4 shadow-xl">
          <p className="text-sm text-muted">Se usa para prellenar el responsable de cada acción. Puede cambiarlo en cada formulario.</p>
          <label className="label mt-3" htmlFor="op-name">Nombre</label>
          <input id="op-name" className="input" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="Ej.: María González" />
          <label className="label mt-3" htmlFor="op-role">Rol</label>
          <input id="op-role" className="input" value={draft.role} onChange={(e) => setDraft({ ...draft, role: e.target.value })} placeholder="Ej.: Inspector(a) de calidad" />
          <div className="mt-4 flex justify-end gap-2">
            <button className="btn-ghost" onClick={() => setOpen(false)}>Cancelar</button>
            <button className="btn-primary" onClick={() => { setOperator(draft); setOpen(false); }}>Guardar</button>
          </div>
        </div>
      )}
    </div>
  );
}

function TourButton() {
  const { start, active } = useTour();
  return (
    <button className="btn-secondary" onClick={start} disabled={active}>
      <Compass className="h-4 w-4" aria-hidden /> <span className="hidden sm:inline">Explorar MercaCircular</span>
      <span className="sm:hidden">Recorrido</span>
    </button>
  );
}

function NavLinks({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <ul className="space-y-1">
      {NAV.map(({ href, label, icon: Icon }) => {
        const active = href === "/" ? pathname === "/" : pathname.startsWith(href);
        return (
          <li key={href}>
            <Link
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active ? "bg-white/15 text-white" : "text-white/75 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              {label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function Frame({ children }: { children: ReactNode }) {
  const [menu, setMenu] = useState(false);
  const pathname = usePathname();
  useEffect(() => setMenu(false), [pathname]);

  const brand = (
    <Link href="/" className="flex items-center gap-2.5 rounded-lg">
      <Logo />
      <span className="leading-tight">
        <span className="block font-display text-[15px] font-semibold text-white">MercaCircular</span>
        <span className="block text-xs text-white/70">Vision AI</span>
      </span>
    </Link>
  );

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_1fr]">
      <a href="#contenido" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[70] focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2">
        Saltar al contenido
      </a>

      {/* Barra lateral (escritorio) */}
      <aside className="sticky top-0 hidden h-screen flex-col bg-deep px-4 py-5 lg:flex">
        {brand}
        <nav aria-label="Principal" className="mt-8 flex-1"><NavLinks /></nav>
        <p className="text-[11px] leading-snug text-white/60">{DISCLAIMER}</p>
      </aside>

      {/* Encabezado (móvil) */}
      <div className="sticky top-0 z-40 flex items-center justify-between bg-deep px-4 py-3 lg:hidden">
        {brand}
        <button className="rounded-lg p-2 text-white" onClick={() => setMenu(true)} aria-label="Abrir menú" aria-expanded={menu}>
          <Menu className="h-5 w-5" />
        </button>
      </div>
      {menu && (
        <div className="fixed inset-0 z-50 lg:hidden" role="dialog" aria-modal="true" aria-label="Menú">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMenu(false)} />
          <nav aria-label="Principal" className="absolute inset-y-0 left-0 flex w-72 flex-col bg-deep px-4 py-5">
            <div className="flex items-center justify-between">
              {brand}
              <button className="rounded-lg p-2 text-white" onClick={() => setMenu(false)} aria-label="Cerrar menú"><X className="h-5 w-5" /></button>
            </div>
            <div className="mt-8 flex-1"><NavLinks onNavigate={() => setMenu(false)} /></div>
            <p className="text-[11px] leading-snug text-white/60">{DISCLAIMER}</p>
          </nav>
        </div>
      )}

      <div className="min-w-0">
        <header className="flex flex-wrap items-center justify-end gap-2 border-b border-line bg-canvas/90 px-4 py-2.5 backdrop-blur sm:px-8">
          <TourButton />
          <OperatorButton />
          <ThemeToggle />
        </header>
        <main id="contenido" className="mx-auto max-w-[1280px] px-4 py-6 sm:px-8 sm:py-8">{children}</main>
        <footer className="mx-auto max-w-[1280px] px-4 pb-8 text-xs text-muted sm:px-8 lg:hidden">{DISCLAIMER}</footer>
      </div>
    </div>
  );
}

export default function Shell({ children }: { children: ReactNode }) {
  const [operator, setOp] = useState<Operator>({ name: "", role: "" });
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem("mc-operator") || "null");
      if (saved) setOp(saved);
    } catch { /* ignorar */ }
  }, []);
  const setOperator = (o: Operator) => {
    setOp(o);
    try { localStorage.setItem("mc-operator", JSON.stringify(o)); } catch { /* ignorar */ }
  };
  return (
    <OperatorCtx.Provider value={{ operator, setOperator }}>
      <ToastProvider>
        <TourProvider>
          <Frame>{children}</Frame>
        </TourProvider>
      </ToastProvider>
    </OperatorCtx.Provider>
  );
}
