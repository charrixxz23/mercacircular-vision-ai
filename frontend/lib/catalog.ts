"use client";

import { useEffect, useState } from "react";
import { api } from "./api";
import type { Catalog } from "./types";

let cache: Promise<Catalog> | null = null;

/** Catálogo (productos, comerciantes, áreas, roles…) con caché en memoria. */
export function useCatalog() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    cache ??= api<Catalog>("/api/catalog");
    cache.then(setCatalog).catch((e) => {
      cache = null;
      setError(e instanceof Error ? e.message : String(e));
    });
  }, []);
  return { catalog, error };
}
