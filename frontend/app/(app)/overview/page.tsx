"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { fmtCurrency, fmtMargin, fmtNum } from "@/lib/format";
import { MoneyBars, TrendChart } from "@/components/charts/charts";
import { RankTable } from "@/components/charts/tables";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorState, KpiCard, type KpiDatum } from "@/components/ui/kpi";
import { ChartSkeleton, KpiSkeleton } from "@/components/ui/skeleton";

type Overview = {
  period: { from: string | null; to: string | null };
  kpis: Record<string, KpiDatum>;
  customers: { total: number; new: number; returning: number; repeat_rate: number };
  trend: { grain: string; points: { date?: string; revenue: number; profit: number; orders: number }[] };
  by_region: { region: string; revenue: number; profit: number; margin: number; orders: number; revenue_growth?: number | null }[];
  by_category: { category: string; revenue: number; profit: number; margin: number; orders: number }[];
};

type Insight = {
  category: string;
  severity: string;
  headline: string;
  explanation: string;
  metric: { label: string; value: number; unit: string };
};

type Uploads = { file_id: string; filename: string; jobs: { id: string; status: string }[] }[];

const CARDS: { label: string; hint: string; format: (v: number | null | undefined) => string; key: string }[] = [
  { label: "Total revenue", hint: "Sum of line revenue, excluding cancelled orders", format: (v) => fmtCurrency(v), key: "revenue" },
  { label: "Gross profit", hint: "Revenue minus cost of goods and shipping", format: (v) => fmtCurrency(v), key: "profit" },
  { label: "Profit margin", hint: "Profit divided by revenue", format: fmtMargin, key: "margin" },
  { label: "Total orders", hint: "Distinct order IDs in period", format: (v) => fmtNum(v), key: "orders" },
  { label: "Units sold", hint: "Sum of quantities", format: (v) => fmtNum(v), key: "units" },
  { label: "Avg order value", hint: "Revenue divided by orders", format: (v) => fmtCurrency(v, 2), key: "aov" },
  { label: "Repeat rate", hint: "Returning customers share of active customers", format: (v) => `${(v ?? 0).toFixed(1)}%`, key: "repeat_rate" },
  { label: "Revenue growth", hint: "Versus previous equivalent period", format: (v) => (v === null || v === undefined ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`), key: "revenue_growth" },
  { label: "Profit growth", hint: "Versus previous equivalent period", format: (v) => (v === null || v === undefined ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`), key: "profit_growth" },
];

export default function OverviewPage() {
  const { queryString } = useFilters();
  const q = useQuery({
    queryKey: ["overview", queryString],
    queryFn: () => apiGet<Overview>(`/analytics/overview${queryString}`),
  });
  const ins = useQuery({
    queryKey: ["insights-preview", queryString],
    queryFn: () => apiGet<{ insights: Insight[] }>(`/insights${queryString}`),
  });
  const up = useQuery({ queryKey: ["uploads-mini"], queryFn: () => apiGet<Uploads>("/uploads") });

  if (q.isPending) return <KpiSkeleton />;
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;
  const d = q.data;
  if (d.kpis.revenue.value === 0 && d.kpis.orders.value === 0) {
    return (
      <EmptyState
        title="No data for the selected filters"
        hint="Import a file from Data Imports, or widen the date range and clear filters."
      />
    );
  }

  const latestJob = up.data?.flatMap((f) => f.jobs.map((j) => ({ ...j, file: f.filename })))?.[0];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {CARDS.map((c) => (
          <KpiCard key={c.key} label={c.label} hint={c.hint} format={c.format} data={d.kpis[c.key]} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <CardTitle>Revenue vs profit trend</CardTitle>
          <CardHint>{d.trend.grain} grain · tooltips show exact values</CardHint>
          <div className="mt-2">
            <TrendChart points={d.trend.points} />
          </div>
        </Card>
        <Card className="p-5">
          <CardTitle>Sales by region</CardTitle>
          <CardHint>Top regions in the selected period</CardHint>
          <div className="mt-2">
            <MoneyBars data={d.by_region} nameKey="region" horizontal />
          </div>
        </Card>
        <Card className="p-5">
          <CardTitle>Sales by category</CardTitle>
          <CardHint>Revenue and profit per category</CardHint>
          <div className="mt-2">
            <MoneyBars data={d.by_category} nameKey="category" />
          </div>
        </Card>
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <CardTitle>Executive insight preview</CardTitle>
            <Link href="/insights" className="text-xs font-medium text-teal-700 hover:underline">
              All insights →
            </Link>
          </div>
          <div className="mt-3 space-y-2">
            {(ins.data?.insights ?? []).slice(0, 3).map((i, k) => (
              <div key={k} className="rounded-lg bg-slate-50 px-3 py-2">
                <p className="flex items-center gap-2 text-xs font-semibold text-slate-800">
                  <Badge tone={i.severity === "positive" ? "green" : i.severity === "critical" || i.severity === "warning" ? "amber" : "slate"}>
                    {i.category}
                  </Badge>
                  {i.headline}
                </p>
                <p className="mt-0.5 text-xs text-slate-500">{i.explanation}</p>
              </div>
            ))}
            {!ins.data && <p className="text-xs text-slate-400">Loading insights…</p>}
          </div>
          <div className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-500">
            <p>
              Reporting period: {d.period.from && d.period.to ? `${d.period.from} → ${d.period.to}` : "all data"} ·{" "}
              {d.customers.total.toLocaleString()} customers ({d.customers.new.toLocaleString()} new)
            </p>
            {latestJob && (
              <p className="mt-1">
                Latest import: <span className="font-mono">{latestJob.file}</span>{" "}
                <Badge tone={latestJob.status === "confirmed" ? "green" : "slate"}>{latestJob.status}</Badge>
              </p>
            )}
          </div>
        </Card>
      </div>

      <Card className="p-5">
        <div className="flex items-center justify-between">
          <CardTitle>Regional performance</CardTitle>
          <Link href="/regions" className="text-xs font-medium text-teal-700 hover:underline">
            Full ranking →
          </Link>
        </div>
        <div className="mt-2">
          <RankTable rows={d.by_region} name={(r) => String(r.region)} />
        </div>
      </Card>
    </div>
  );
}
