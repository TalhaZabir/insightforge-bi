"use client";

import { useQuery } from "@tanstack/react-query";
import { TrendingDown, TrendingUp } from "lucide-react";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/cn";
import { fmtGrowth } from "@/lib/format";

export type KpiDatum = {
  value: number | null;
  previous?: number | null;
  growth_pct?: number | null;
  delta_pp?: number | null;
};

export function KpiCard({
  label,
  hint,
  format,
  data,
  invert = false,
}: {
  label: string;
  hint?: string;
  format: (v: number | null | undefined) => string;
  data?: KpiDatum;
  invert?: boolean;
}) {
  const delta = data?.growth_pct ?? data?.delta_pp ?? null;
  const good = delta === null ? null : invert ? delta < 0 : delta >= 0;
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm" title={hint}>
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-[#0A1628]">
        {data ? format(data.value) : "—"}
      </p>
      <p className="mt-1 flex items-center gap-1 text-xs">
        {delta !== null && (
          <span
            className={cn(
              "inline-flex items-center gap-0.5 font-semibold",
              good ? "text-emerald-600" : "text-red-600"
            )}
          >
            {delta >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            {fmtGrowth(delta)}
          </span>
        )}
        <span className="text-slate-400">vs prev. period</span>
      </p>
    </div>
  );
}

export function EmptyState({
  title,
  hint,
  action,
}: {
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
      <p className="text-sm font-semibold text-slate-700">{title}</p>
      {hint && <p className="mt-1 max-w-md text-xs text-slate-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 px-6 py-14 text-center">
      <p className="text-sm font-semibold text-red-800">Something went wrong</p>
      <p className="mt-1 max-w-md text-xs text-red-600">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 rounded-lg border border-red-300 bg-white px-4 py-2 text-xs font-medium text-red-700"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function useFacets() {
  return useQuery({
    queryKey: ["facets"],
    queryFn: () =>
      apiGet<Record<string, string[]>>("/analytics/facets"),
    staleTime: 5 * 60_000,
  });
}
