"use client";

import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtCurrency } from "@/lib/format";

export const label = (v: string | null | undefined) => v ?? "Unspecified";

const NAVY = "#0F1F3A";
const TEAL = "#0D9488";
const SLATE = "#94A3B8";
const AMBER = "#D97706";
const RED = "#DC2626";
const GREEN = "#059669";

export const PALETTE = [NAVY, TEAL, AMBER, "#7C3AED", RED, GREEN, "#0891B2", "#BE123C"];

const moneyTick = (v: number) =>
  v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(1)}M` : v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`;

export function TrendChart({
  points,
  height = 260,
}: {
  points: { date?: string; year?: number; month?: number; revenue: number; profit: number; orders: number }[];
  height?: number;
}) {
  const data = points.map((p) => ({
    x: p.date ?? `${p.year}-${String(p.month).padStart(2, "0")}`,
    revenue: Math.round(p.revenue),
    profit: Math.round(p.profit),
  }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
        <XAxis dataKey="x" tick={{ fontSize: 11 }} minTickGap={28} />
        <YAxis tickFormatter={moneyTick} tick={{ fontSize: 11 }} width={64} />
        <Tooltip formatter={(v) => fmtCurrency(Number(v))} />
        <Legend />
        <Area type="monotone" dataKey="revenue" name="Revenue" fill={`${TEAL}33`} stroke={TEAL} strokeWidth={2} />
        <Line type="monotone" dataKey="profit" name="Profit" stroke={NAVY} strokeWidth={2} dot={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function MoneyBars({
  data,
  nameKey,
  height = 240,
  horizontal = false,
}: {
  data: { revenue: number; profit: number; [k: string]: unknown }[];
  nameKey: string;
  height?: number;
  horizontal?: boolean;
}) {
  const rows = data.slice(0, 10).map((r) => ({ ...r, [nameKey]: label(r[nameKey] as string) }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout={horizontal ? "vertical" : "horizontal"} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
        {horizontal ? (
          <>
            <XAxis type="number" tickFormatter={moneyTick} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey={nameKey} tick={{ fontSize: 11 }} width={110} />
          </>
        ) : (
          <>
            <XAxis dataKey={nameKey} tick={{ fontSize: 11 }} interval={0} angle={-18} dy={8} height={52} />
            <YAxis tickFormatter={moneyTick} tick={{ fontSize: 11 }} width={64} />
          </>
        )}
        <Tooltip formatter={(v) => fmtCurrency(Number(v))} />
        <Legend />
        <Bar dataKey="revenue" name="Revenue" fill={TEAL} radius={[4, 4, 0, 0]} />
        <Bar dataKey="profit" name="Profit" fill={NAVY} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function MixPie({
  data,
  nameKey,
  height = 240,
}: {
  data: { revenue: number; [k: string]: unknown }[];
  nameKey: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data as Record<string, unknown>[]}
          dataKey="revenue"
          nameKey={nameKey}
          innerRadius={52}
          outerRadius={88}
          paddingAngle={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip formatter={(v) => fmtCurrency(Number(v))} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function channelColor(i: number) {
  return PALETTE[i % PALETTE.length];
}
