"use client";

import { ChevronLeft, ChevronRight, Compass, SkipForward, X } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { emitTourAction, TOUR_DONE, TOUR_EVENT, TOUR_STEPS, type TourState } from "@/lib/tour";

type Ctx = { start: () => void; active: boolean };
const TourCtx = createContext<Ctx>({ start: () => {}, active: false });
export const useTour = () => useContext(TourCtx);

const KEY = "mc-tour";

/** Las páginas registran aquí lo que hacen cuando el recorrido pide una acción. */
export function useTourAction(handlers: Record<string, () => void>) {
  useEffect(() => {
    const fn = (e: Event) => {
      const ev = (e as CustomEvent<{ event: string }>).detail.event;
      handlers[ev]?.();
    };
    window.addEventListener(TOUR_EVENT, fn);
    return () => window.removeEventListener(TOUR_EVENT, fn);
  });
}

export function TourProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [active, setActive] = useState(false);
  const [step, setStep] = useState(0);
  const [state, setState] = useState<TourState>({ lotCode: null });

  // Restaurar el recorrido si se recarga la página.
  useEffect(() => {
    try {
      const saved = JSON.parse(sessionStorage.getItem(KEY) || "null");
      if (saved?.active) {
        setActive(true);
        setStep(saved.step);
        setState(saved.state);
      }
    } catch { /* sin almacenamiento: el recorrido empieza de cero */ }
  }, []);
  useEffect(() => {
    try { sessionStorage.setItem(KEY, JSON.stringify({ active, step, state })); } catch { /* ignorar */ }
  }, [active, step, state]);

  const current = TOUR_STEPS[step];
  const target = current ? current.route(state) : null;

  // Navegar a la ruta del paso.
  useEffect(() => {
    if (!active || !target) return;
    const path = target.split("?")[0];
    if (pathname !== path) router.push(target);
  }, [active, target, pathname, router]);

  // Resaltar el elemento del paso.
  useEffect(() => {
    if (!active || !current) return;
    let el: Element | null = null;
    let tries = 0;
    const timer = setInterval(() => {
      el = document.querySelector(`[data-tour="${current.target}"]`);
      if (el || ++tries > 40) {
        clearInterval(timer);
        if (el) {
          el.classList.add("tour-highlight");
          const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
          el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "center" });
        }
      }
    }, 100);
    return () => {
      clearInterval(timer);
      document.querySelectorAll(".tour-highlight").forEach((n) => n.classList.remove("tour-highlight"));
    };
  }, [active, current, pathname]);

  const next = useCallback(() => setStep((s) => Math.min(s + 1, TOUR_STEPS.length - 1)), []);
  const finish = useCallback(() => {
    setActive(false);
    setStep(0);
    document.querySelectorAll(".tour-highlight").forEach((n) => n.classList.remove("tour-highlight"));
  }, []);

  // Avance automático cuando la página informa que la acción se completó.
  useEffect(() => {
    const fn = (e: Event) => {
      const d = (e as CustomEvent<{ name: string; code?: string }>).detail;
      if (d.name === "lot-created" && d.code) setState((s) => ({ ...s, lotCode: d.code as string }));
      if (active && current?.waitFor === d.name) setTimeout(next, 600);
    };
    window.addEventListener(TOUR_DONE, fn);
    return () => window.removeEventListener(TOUR_DONE, fn);
  }, [active, current, next]);

  const start = useCallback(() => {
    setState({ lotCode: null });
    setStep(0);
    setActive(true);
  }, []);

  const runAction = () => {
    if (!current?.action) return;
    if (current.action.event === "go-dashboard") {
      finish();
      router.push("/");
      return;
    }
    emitTourAction(current.action.event);
  };

  const missingLot = current?.needsLot && !state.lotCode;

  return (
    <TourCtx.Provider value={{ start, active }}>
      {children}
      {active && current && (
        <section
          aria-label="Recorrido guiado"
          aria-live="polite"
          className="fixed bottom-4 right-4 z-50 w-[min(380px,calc(100%-2rem))] rounded-xl border border-line bg-surface p-4 text-ink shadow-2xl"
        >
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="flex items-center gap-1.5 text-xs font-medium text-muted">
                <Compass className="h-3.5 w-3.5" aria-hidden /> Explorar MercaCircular · paso {step + 1} de {TOUR_STEPS.length}
              </p>
              <h2 className="mt-1 text-base font-semibold">{current.title}</h2>
            </div>
            <button className="rounded p-1 text-muted hover:bg-sunken" onClick={finish} aria-label="Finalizar recorrido">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-1 h-1 rounded-full bg-sunken" aria-hidden>
            <div className="h-1 rounded-full bg-field" style={{ width: `${((step + 1) / TOUR_STEPS.length) * 100}%` }} />
          </div>
          <p className="mt-3 text-sm leading-relaxed text-muted">
            {missingLot ? "Este paso usa el lote creado en el paso 2. Vuelva atrás para registrarlo, o continúe solo para leer." : current.body}
          </p>
          {current.action && !missingLot && (
            <button className="btn-primary mt-3 w-full" onClick={runAction}>{current.action.label}</button>
          )}
          <div className="mt-3 flex items-center justify-between gap-2">
            <button className="btn-ghost px-2" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
              <ChevronLeft className="h-4 w-4" aria-hidden /> Atrás
            </button>
            <div className="flex gap-1">
              {step < TOUR_STEPS.length - 1 ? (
                <>
                  <button className="btn-ghost px-2" onClick={next} title="Pasar al siguiente paso sin realizar la acción">
                    <SkipForward className="h-4 w-4" aria-hidden /> Omitir
                  </button>
                  <button className="btn-secondary px-3" onClick={next}>
                    Siguiente <ChevronRight className="h-4 w-4" aria-hidden />
                  </button>
                </>
              ) : (
                <button className="btn-secondary px-3" onClick={finish}>Finalizar</button>
              )}
            </div>
          </div>
        </section>
      )}
    </TourCtx.Provider>
  );
}
