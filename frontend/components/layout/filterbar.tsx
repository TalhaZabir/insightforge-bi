"use client";

import { usePathname } from "next/navigation";
import { useFilters } from "@/hooks/useFilters";
import { useFacets } from "@/components/ui/kpi";
import { Button } from "@/components/ui/button";

const FILTER_ROUTES = [
  "/overview",
  "/sales",
  "/profitability",
  "/customers",
  "/products",
  "/regions",
  "/quality",
  "/insights",
];

export function FilterBar() {
  const pathname = usePathname();
  const { filters, set, reset, activeCount } = useFilters();
  const facets = useFacets();

  if (!FILTER_ROUTES.some((r) => pathname === r || pathname.startsWith(r + "/"))) return null;

  const select = (
    key: "region" | "category" | "channel" | "segment" | "status",
    label: string,
    options: string[] | undefined
  ) => (
    <label className="flex min-w-[130px] flex-col gap-1 text-[11px] font-medium text-slate-500">
      {label}
      <select
        value={filters[key]}
        onChange={(e) => set({ [key]: e.target.value })}
        className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-xs text-slate-800"
      >
        <option value="">All</option>
        {(options ?? []).map((o) => (
          <option key={o} value={o}>
            {o || "(blank)"}
          </option>
        ))}
      </select>
    </label>
  );

  const chips: string[] = [];
  if (filters.from || filters.to)
    chips.push(`Date: ${filters.from || "…"} → ${filters.to || "…"}`);
  for (const k of ["region", "category", "channel", "segment", "status"] as const) {
    if (filters[k]) chips.push(`${k}: ${filters[k]}`);
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-[11px] font-medium text-slate-500">
          From
          <input
            type="date"
            value={filters.from}
            onChange={(e) => set({ from: e.target.value })}
            className="rounded-lg border border-slate-300 px-2 py-1.5 text-xs"
          />
        </label>
        <label className="flex flex-col gap-1 text-[11px] font-medium text-slate-500">
          To
          <input
            type="date"
            value={filters.to}
            onChange={(e) => set({ to: e.target.value })}
            className="rounded-lg border border-slate-300 px-2 py-1.5 text-xs"
          />
        </label>
        {select("region", "Region", facets.data?.regions)}
        {select("category", "Category", facets.data?.categories)}
        {select("channel", "Channel", facets.data?.channels)}
        {select("segment", "Segment", facets.data?.segments)}
        {select("status", "Status", facets.data?.statuses)}
        <Button variant="ghost" size="sm" onClick={reset} disabled={activeCount === 0}>
          Reset all{activeCount > 0 ? ` (${activeCount})` : ""}
        </Button>
      </div>
      {chips.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5" aria-live="polite">
          {chips.map((c) => (
            <span
              key={c}
              className="rounded-full bg-[#0F1F3A]/5 px-2.5 py-0.5 text-[11px] font-medium text-[#0F1F3A]"
            >
              {c}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
