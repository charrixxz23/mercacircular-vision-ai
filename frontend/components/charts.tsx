"use client";

import {
  Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { kg, num, weekLabel } from "@/lib/format";

// Colores de tono medio: legibles en tema claro y oscuro.
export const C = {
  field: "#4E8A2F",
  leaf: "#9CC57A",
  warn: "#E0893B",
  crit: "#C2412D",
  info: "#3A78AE",
  grid: "rgba(128,140,132,0.25)",
  axis: "#86918b",
};

const axis = { tick: { fill: C.axis, fontSize: 12 }, tickLine: false, axisLine: false } as const;
const tooltipStyle = {
  contentStyle: { background: "rgb(var(--surface))", border: "1px solid rgb(var(--line))", borderRadius: 8, color: "rgb(var(--ink))", fontSize: 13 },
  labelStyle: { color: "rgb(var(--ink))", fontWeight: 600 },
  cursor: { fill: "rgba(128,140,132,0.12)" },
};

export function WeeklyTrend({ data }: { data: { semana: string; kg_registrados: number; kg_comercial: number; kg_donacion: number; kg_residuos: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={C.grid} />
        <XAxis dataKey="semana" tickFormatter={weekLabel} {...axis} />
        <YAxis {...axis} width={56} tickFormatter={(v) => num(v)} />
        <Tooltip {...tooltipStyle} labelFormatter={(l) => `Semana del ${weekLabel(String(l))}`} formatter={(v: number) => kg(v)} />
        <Legend wrapperStyle={{ fontSize: 12, color: C.axis }} />
        <Bar dataKey="kg_comercial" name="Comercializado (confirmado)" stackId="d" fill={C.info} />
        <Bar dataKey="kg_donacion" name="Donación (confirmada)" stackId="d" fill={C.field} />
        <Bar dataKey="kg_residuos" name="Residuos (confirmado)" stackId="d" fill={C.warn} radius={[3, 3, 0, 0]} />
        <Line dataKey="kg_registrados" name="Registrado (entrada)" type="monotone" stroke="#6b7a72" strokeWidth={2} strokeDasharray="5 4" dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function HorizontalBars({ data, color = C.field, unit = "kg", height }: { data: { label: string; value: number; color?: string }[]; color?: string; unit?: "kg" | "n"; height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height ?? Math.max(140, data.length * 44)}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, left: 0, bottom: 0 }}>
        <CartesianGrid horizontal={false} stroke={C.grid} />
        <XAxis type="number" {...axis} tickFormatter={(v) => num(v)} />
        <YAxis type="category" dataKey="label" {...axis} width={150} />
        <Tooltip {...tooltipStyle} formatter={(v: number) => (unit === "kg" ? kg(v) : num(v))} />
        <Bar dataKey="value" name={unit === "kg" ? "Kilogramos" : "Total"} radius={[0, 4, 4, 0]} barSize={22}
          fill={color} shape={(props: unknown) => {
            const p = props as { x: number; y: number; width: number; height: number; payload: { color?: string } };
            return <rect x={p.x} y={p.y} width={Math.max(0, p.width)} height={p.height} rx={4} fill={p.payload.color || color} />;
          }} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function CompareBars({ data }: { data: { label: string; actual: number; anterior: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={Math.max(180, data.length * 56)}>
      <BarChart data={data} layout="vertical" margin={{ top: 0, right: 24, left: 0, bottom: 0 }}>
        <CartesianGrid horizontal={false} stroke={C.grid} />
        <XAxis type="number" {...axis} tickFormatter={(v) => num(v)} />
        <YAxis type="category" dataKey="label" {...axis} width={150} />
        <Tooltip {...tooltipStyle} formatter={(v: number) => num(v, 1)} />
        <Legend wrapperStyle={{ fontSize: 12, color: C.axis }} />
        <Bar dataKey="anterior" name="Período anterior" fill={C.leaf} radius={[0, 4, 4, 0]} barSize={14} />
        <Bar dataKey="actual" name="Período actual" fill={C.field} radius={[0, 4, 4, 0]} barSize={14} />
      </BarChart>
    </ResponsiveContainer>
  );
}
