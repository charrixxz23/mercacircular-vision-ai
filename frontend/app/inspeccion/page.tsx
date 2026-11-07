"use client";

import { Camera, ImageUp, Images, Loader2, Plus, ScanSearch } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { AnalysisDetails, InspectionImage, RecommendationPanel } from "@/components/analysis";
import { DecisionForm, WeightField } from "@/components/lot";
import { useOperator } from "@/components/Shell";
import { useTourAction } from "@/components/tour";
import { Badge, ErrorBox, LotTag, Notice, PageHeader, Spinner, StatusBadge, useToast } from "@/components/ui";
import { api, errorText } from "@/lib/api";
import { useCatalog } from "@/lib/catalog";
import { kg } from "@/lib/format";
import { emitTourDone } from "@/lib/tour";
import type { ImageInfo, Inspection, LotDetail, LotSummary } from "@/lib/types";

type Sample = { archivo: string; producto: string; url: string; proposito: string; cambios: string };
type Picked = { blob: Blob; name: string; source: "camera" | "upload" | "sample"; preview: string };
type ModelInfo = { loaded: boolean; error: string | null; samples: Sample[] };

const OPEN_STATUSES = "registrado,pendiente_inspeccion,inspeccionado,revision_comercial";
const MAX_MB = 10;

function CameraCapture({ onCapture }: { onCapture: (p: Picked) => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string | null>(null);
  const supported = typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

  const start = async () => {
    setError(null);
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } }, audio: false });
      setStream(s);
      if (video.current) video.current.srcObject = s;
    } catch (e) {
      setError(e instanceof DOMException && e.name === "NotAllowedError"
        ? "Permiso de cámara denegado. Habilítelo en el navegador o use «Archivo»."
        : "No se pudo abrir la cámara. Use «Archivo» o, en el teléfono, «Tomar foto con el teléfono».");
    }
  };
  const stop = useCallback(() => { stream?.getTracks().forEach((t) => t.stop()); setStream(null); }, [stream]);
  useEffect(() => () => stream?.getTracks().forEach((t) => t.stop()), [stream]);

  const shoot = () => {
    const v = video.current;
    if (!v) return;
    const c = document.createElement("canvas");
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    c.getContext("2d")?.drawImage(v, 0, 0);
    c.toBlob((b) => {
      if (b) onCapture({ blob: b, name: "captura.jpg", source: "camera", preview: URL.createObjectURL(b) });
      stop();
    }, "image/jpeg", 0.92);
  };

  if (!supported) {
    return <Notice tone="info">Este navegador no permite usar la cámara aquí (requiere https o localhost). Use «Archivo»: en un teléfono abre directamente la cámara.</Notice>;
  }
  return (
    <div className="space-y-3">
      <div className="flex aspect-video items-center justify-center overflow-hidden rounded-lg bg-sunken">
        <video ref={video} autoPlay playsInline muted className={stream ? "h-full w-full object-contain" : "hidden"} />
        {!stream && <p className="px-6 text-center text-sm text-muted">Centre el producto sobre una superficie lisa y bien iluminada.</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        {!stream ? (
          <button type="button" className="btn-secondary" onClick={start}><Camera className="h-4 w-4" aria-hidden /> Abrir cámara</button>
        ) : (
          <>
            <button type="button" className="btn-primary" onClick={shoot}><Camera className="h-4 w-4" aria-hidden /> Tomar foto</button>
            <button type="button" className="btn-ghost" onClick={stop}>Cerrar cámara</button>
          </>
        )}
      </div>
      {error && <ErrorBox message={error} />}
    </div>
  );
}

function QuickLot({ onCreated }: { onCreated: (code: string) => void }) {
  const { catalog } = useCatalog();
  const { operator } = useOperator();
  const [product, setProduct] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const create = async () => {
    if (!catalog || !product) return;
    setBusy(true);
    setError(null);
    try {
      const lot = await api<LotDetail>("/api/lots", {
        method: "POST",
        json: { product_id: Number(product), merchant_id: catalog.merchants[0].id, area_id: catalog.areas[0].id, registered_by: operator.name || null },
      });
      onCreated(lot.code);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="rounded-lg border border-dashed border-line p-3">
      <p className="text-sm font-medium">Lote rápido</p>
      <p className="text-xs text-muted">Crea un lote con el producto elegido; complete los demás datos luego en su ficha.</p>
      <div className="mt-2 flex flex-wrap gap-2">
        <label className="sr-only" htmlFor="ql-prod">Producto</label>
        <select id="ql-prod" className="input w-auto" value={product} onChange={(e) => setProduct(e.target.value)}>
          <option value="">Producto…</option>
          {catalog?.products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <button type="button" className="btn-secondary" onClick={create} disabled={!product || busy}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <Plus className="h-4 w-4" aria-hidden />} Crear lote
        </button>
      </div>
      {error && <div className="mt-2"><ErrorBox message={error} /></div>}
    </div>
  );
}

function InspectionWorkspace() {
  const params = useSearchParams();
  const router = useRouter();
  const toast = useToast();
  const { catalog } = useCatalog();
  const { operator } = useOperator();
  const [code, setCode] = useState(params.get("lote") || "");
  const [options, setOptions] = useState<LotSummary[] | null>(null);
  const [lot, setLot] = useState<LotDetail | null>(null);
  const [lotError, setLotError] = useState<string | null>(null);
  const [model, setModel] = useState<ModelInfo | null>(null);
  const [tab, setTab] = useState<"camera" | "file" | "samples">("samples");
  const [picked, setPicked] = useState<Picked | null>(null);
  const [mode, setMode] = useState<"ia" | "demo">("ia");
  const [scenario, setScenario] = useState("manchas_leves");
  const [step, setStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inspection, setInspection] = useState<Inspection | null>(null);

  useEffect(() => { setCode(params.get("lote") || ""); }, [params]);
  useEffect(() => {
    api<{ items: LotSummary[] }>(`/api/lots?status=${OPEN_STATUSES}&limit=100`).then((r) => setOptions(r.items)).catch(() => setOptions([]));
    api<ModelInfo>("/api/model").then((m) => { setModel(m); if (!m.loaded) setMode("demo"); }).catch(() => setModel({ loaded: false, error: "Sin conexión", samples: [] }));
  }, []);
  useEffect(() => {
    setLot(null);
    setInspection(null);
    setLotError(null);
    if (!code) return;
    api<LotDetail>(`/api/lots/${code}`).then(setLot).catch((e) => setLotError(errorText(e)));
  }, [code]);

  const selectLot = (c: string) => router.replace(c ? `/inspeccion?lote=${c}` : "/inspeccion");

  const pickFile = (file: File | undefined, source: "upload" | "camera" = "upload") => {
    setError(null);
    if (!file) return;
    if (!file.type.startsWith("image/")) return setError("El archivo no es una imagen. Use JPG, PNG o WebP.");
    if (file.size > MAX_MB * 1024 * 1024) return setError(`La imagen supera ${MAX_MB} MB.`);
    setPicked({ blob: file, name: file.name, source, preview: URL.createObjectURL(file) });
    setInspection(null);
    emitTourDone("image-ready");
  };

  const pickSample = async (s: Sample) => {
    setError(null);
    try {
      const res = await fetch(s.url);
      if (!res.ok) throw new Error("No se pudo cargar la imagen de ejemplo.");
      const blob = await res.blob();
      setPicked({ blob, name: s.archivo, source: "sample", preview: URL.createObjectURL(blob) });
      setInspection(null);
      emitTourDone("image-ready");
    } catch (e) {
      setError(errorText(e));
    }
  };

  const analyze = async () => {
    if (!lot) return setError("Elija o cree un lote primero.");
    if (mode === "ia" && !picked) return setError("Para el modo IA real necesita una imagen (cámara, archivo o ejemplo).");
    setError(null);
    try {
      let imageId: number | null = null;
      if (picked) {
        setStep("Guardando la imagen…");
        const fd = new FormData();
        fd.append("file", picked.blob, picked.name);
        fd.append("source", picked.source);
        if (operator.name) fd.append("actor", operator.name);
        const img = await api<ImageInfo>(`/api/lots/${lot.code}/images`, { method: "POST", body: fd });
        imageId = img.id;
      }
      setStep(mode === "ia" ? "Analizando: calidad, segmentación, identificación y manchas…" : "Aplicando el escenario demostrativo…");
      const insp = await api<Inspection>(`/api/lots/${lot.code}/inspections`, {
        method: "POST", json: { mode, image_id: imageId, scenario_id: mode === "demo" ? scenario : null, actor: operator.name || null },
      });
      setInspection(insp);
      setPicked(null);
      setLot(await api<LotDetail>(`/api/lots/${lot.code}`));
      toast(`Análisis guardado en el lote ${lot.code}.`);
      emitTourDone("analysis-done");
      setTimeout(() => document.getElementById("resultado")?.scrollIntoView({ block: "start" }), 50);
    } catch (e) {
      setError(errorText(e));
    } finally {
      setStep(null);
    }
  };

  useTourAction({
    "load-sample": () => {
      setTab("samples");
      const s = model?.samples.find((x) => x.archivo === "tomate_manchas_sinteticas.jpg") ?? model?.samples[0];
      if (s) pickSample(s);
    },
    "run-analysis": () => { setMode(model?.loaded ? "ia" : "demo"); analyze(); },
  });

  const closed = lot?.status === "cerrado";

  return (
    <>
      <PageHeader
        title="Inspección visual"
        description="Elija el lote, capture o cargue una foto y ejecute el análisis. El resultado es una recomendación: la decisión la toma una persona."
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1fr)_380px] [&>*]:min-w-0">
        <div className="space-y-6">
          {/* 1. Lote */}
          <section className="panel p-5" aria-labelledby="s1">
            <h2 id="s1" className="text-lg font-semibold">1. Lote y producto</h2>
            <div className="mt-3 grid gap-4 md:grid-cols-2">
              <div>
                <label className="label" htmlFor="lot-select">Lote a inspeccionar</label>
                <select id="lot-select" className="input" value={code} onChange={(e) => selectLot(e.target.value)}>
                  <option value="">Elija un lote abierto…</option>
                  {code && !options?.some((o) => o.code === code) && <option value={code}>{code}</option>}
                  {options?.map((o) => (
                    <option key={o.code} value={o.code}>{o.code} · {o.product.name} · {o.status_label}{o.is_demo ? " (demostrativo)" : ""}</option>
                  ))}
                </select>
                <p className="hint">¿Lote nuevo? <Link className="font-medium text-field-ink underline" href="/lotes/nuevo">Regístrelo con todos los datos</Link> o use el lote rápido.</p>
              </div>
              <QuickLot onCreated={(c) => { selectLot(c); emitTourDone("lot-created", { code: c }); }} />
            </div>
            {lotError && <div className="mt-3"><ErrorBox message={lotError} /></div>}
            {lot && (
              <div className="mt-4 flex flex-wrap items-center gap-3 rounded-lg bg-sunken px-4 py-3 text-sm">
                <LotTag code={lot.code} href={`/lotes/${lot.code}`} />
                <span>Producto declarado: <strong>{lot.product.name}</strong></span>
                <span>Peso: <strong>{kg(lot.weight_kg)}</strong></span>
                <StatusBadge status={lot.status} label={lot.status_label} />
                {lot.is_demo && <Badge>Demostrativo</Badge>}
                {catalog && !catalog.products.find((p) => p.id === lot.product.id)?.in_model && (
                  <Badge tone="warn">Producto fuera del modelo</Badge>
                )}
              </div>
            )}
            {closed && <div className="mt-3"><Notice tone="warn">Este lote está cerrado y no admite nuevas inspecciones.</Notice></div>}
          </section>

          {/* 2. Imagen */}
          <section data-tour="capture" className="panel p-5" aria-labelledby="s2">
            <h2 id="s2" className="text-lg font-semibold">2. Imagen</h2>
            <div role="tablist" aria-label="Origen de la imagen" className="mt-3 inline-flex rounded-lg border border-line p-1">
              {([["camera", "Cámara", Camera], ["file", "Archivo", ImageUp], ["samples", "Ejemplos", Images]] as const).map(([k, l, Icon]) => (
                <button key={k} role="tab" aria-selected={tab === k} className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm ${tab === k ? "bg-sunken font-semibold" : "text-muted"}`} onClick={() => setTab(k)}>
                  <Icon className="h-4 w-4" aria-hidden /> {l}
                </button>
              ))}
            </div>
            <div className="mt-4">
              {tab === "camera" && <CameraCapture onCapture={(p) => { setPicked(p); setInspection(null); emitTourDone("image-ready"); }} />}
              {tab === "file" && (
                <div className="space-y-3">
                  <label className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed border-line px-6 py-10 text-center hover:bg-sunken">
                    <ImageUp className="h-6 w-6 text-muted" aria-hidden />
                    <span className="text-sm font-medium">Elegir una foto</span>
                    <span className="text-xs text-muted">JPG, PNG o WebP de hasta {MAX_MB} MB. Se eliminan los metadatos (p. ej. ubicación).</span>
                    <input type="file" accept="image/*" className="sr-only" onChange={(e) => pickFile(e.target.files?.[0])} />
                  </label>
                  <label className="btn-secondary cursor-pointer sm:hidden">
                    <Camera className="h-4 w-4" aria-hidden /> Tomar foto con el teléfono
                    <input type="file" accept="image/*" capture="environment" className="sr-only" onChange={(e) => pickFile(e.target.files?.[0], "camera")} />
                  </label>
                </div>
              )}
              {tab === "samples" && (
                <div>
                  <p className="mb-3 text-sm text-muted">Imágenes de prueba derivadas de Fruits-360 (CC BY-SA 4.0), de grupos que el modelo no vio al entrenar.</p>
                  <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                    {model?.samples.map((s) => (
                      <li key={s.archivo}>
                        <button className="w-full overflow-hidden rounded-lg border border-line text-left hover:border-field" onClick={() => pickSample(s)}>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img src={s.url} alt="" className="aspect-square w-full bg-sunken object-cover" />
                          <span className="block px-2 py-1.5 text-xs leading-snug">{s.proposito}</span>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
            {picked && (
              <div className="mt-4 flex items-center gap-3 rounded-lg bg-sunken p-3 text-sm">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={picked.preview} alt="Imagen seleccionada" className="h-16 w-16 rounded object-cover" />
                <span className="min-w-0 flex-1 truncate">{picked.name}</span>
                <button className="btn-ghost" onClick={() => setPicked(null)}>Quitar</button>
              </div>
            )}
          </section>

          {/* 3. Análisis */}
          <section className="panel p-5" aria-labelledby="s3">
            <h2 id="s3" className="text-lg font-semibold">3. Análisis</h2>
            <fieldset className="mt-3 grid gap-2 md:grid-cols-2">
              <legend className="sr-only">Modo de análisis</legend>
              <label className={`flex cursor-pointer gap-3 rounded-lg border px-3 py-3 text-sm ${mode === "ia" ? "border-field bg-leaf/50" : "border-line"} ${!model?.loaded ? "opacity-60" : ""}`}>
                <input type="radio" name="mode" checked={mode === "ia"} onChange={() => setMode("ia")} disabled={!model?.loaded} className="mt-0.5" />
                <span><strong>Modo IA real</strong><span className="block text-muted">Validación de calidad, segmentación OpenCV, clasificador entrenado y detector de manchas.</span>
                  {model && !model.loaded && <span className="block text-crit">Modelo no disponible: {model.error}</span>}</span>
              </label>
              <label className={`flex cursor-pointer gap-3 rounded-lg border px-3 py-3 text-sm ${mode === "demo" ? "border-warn bg-warn-bg/60" : "border-line"}`}>
                <input type="radio" name="mode" checked={mode === "demo"} onChange={() => setMode("demo")} className="mt-0.5" />
                <span><strong>Modo demostrativo</strong><span className="block text-muted">Resultado predefinido de un escenario. No analiza la imagen.</span></span>
              </label>
            </fieldset>
            {mode === "demo" && (
              <div className="mt-3 max-w-md">
                <label className="label" htmlFor="scenario">Escenario</label>
                <select id="scenario" className="input" value={scenario} onChange={(e) => setScenario(e.target.value)}>
                  {catalog?.scenarios.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
                </select>
              </div>
            )}
            {error && <div className="mt-4"><ErrorBox message={error} /></div>}
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button data-tour="analyze" className="btn-primary" onClick={analyze} disabled={!!step || !lot || closed}>
                {step ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : <ScanSearch className="h-4 w-4" aria-hidden />}
                {mode === "ia" ? "Analizar imagen" : "Aplicar escenario"}
              </button>
              {step && <span role="status" className="text-sm text-muted">{step}</span>}
            </div>
          </section>

          {inspection && (
            <section id="resultado" className="scroll-mt-6 space-y-4" aria-labelledby="res-h">
              <h2 id="res-h" className="text-xl font-semibold">Resultado</h2>
              <InspectionImage inspection={inspection} />
              <div className="panel p-5"><AnalysisDetails inspection={inspection} /></div>
            </section>
          )}
        </div>

        <aside className="space-y-6" aria-label="Recomendación y decisión">
          {!lot && <div className="panel p-5 text-sm text-muted">Elija un lote para ver su recomendación y registrar la decisión.</div>}
          {lot && (
            <>
              {lot.current_recommendation ? (
                <RecommendationPanel rec={lot.current_recommendation} />
              ) : (
                <div data-tour="recommendation" className="panel p-5 text-sm text-muted">La recomendación aparecerá después del análisis.</div>
              )}
              <WeightField lot={lot} onSaved={setLot} />
              <DecisionForm lot={lot} onDone={setLot} />
              <Link className="btn-secondary w-full" href={`/lotes/${lot.code}`}>Ver ficha y trazabilidad</Link>
            </>
          )}
        </aside>
      </div>
    </>
  );
}

export default function InspectionPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <InspectionWorkspace />
    </Suspense>
  );
}
