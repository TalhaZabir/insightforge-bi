"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { MoneyBars, TrendChart } from "@/components/charts/charts";
import { RankTable } from "@/components/charts/tables";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/kpi";
import { ChartSkeleton } from "@/components/ui/skeleton";

type P = {
  product_id: string;
  product_name: string;
  category: string;
  revenue: number;
  profit: number;
  margin: number;
  orders: number;
  units?: number;
  low_margin?: boolean;
};

type Products = {
  best_sellers: P[];
  highest_profit: P[];
  lowest_margin: P[];
  by_category: { category: string; revenue: number; profit: number; margin: number; orders: number }[];
  trend: { grain: string; points: { date?: string; revenue: number; profit: number; orders: number }[] };
};

export default function ProductsPage() {
  const { queryString } = useFilters();
  const [detail, setDetail] = useState<P | null>(null);
  const q = useQuery({
    queryKey: ["products", queryString],
    queryFn: () => apiGet<Products>(`/analytics/products${queryString}`),
  });

  if (q.isPending)
    return (
      <div className="space-y-4">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    );
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;
  if (q.data.best_sellers.length === 0) return <EmptyState title="No products in this selection" />;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <CardTitle>Category performance</CardTitle>
          <div className="mt-2">
            <MoneyBars data={q.data.by_category} nameKey="category" />
          </div>
        </Card>
        <Card className="p-5">
          <CardTitle>Product revenue trend</CardTitle>
          <div className="mt-2">
            <TrendChart points={q.data.trend.points} />
          </div>
        </Card>
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        {(
          [
            ["Best sellers", q.data.best_sellers, "Units drive this list via revenue rank"],
            ["Highest profit", q.data.highest_profit, "Top contributors to gross profit"],
            ["Lowest margin", q.data.lowest_margin, "Review pricing, cost or discount"],
          ] as const
        ).map(([title, rows, hint]) => (
          <Card key={title} className="p-5">
            <CardTitle>{title}</CardTitle>
            <CardHint>{hint} · click a row for detail</CardHint>
            <div className="mt-2" onClick={(e) => {
              const t = (e.target as HTMLElement).closest("tr");
              if (!t) return;
              const idx = Array.from(t.parentElement?.children ?? []).indexOf(t) - 1;
              if (idx >= 0 && rows[idx]) setDetail(rows[idx] ?? null);
            }}>
              <RankTable rows={rows} name={(r) => String(r.product_name)} />
            </div>
          </Card>
        ))}
      </div>
      {detail && (
        <Card className="border-teal-200 p-5">
          <div className="flex items-center justify-between">
            <CardTitle>Product drilldown — {detail.product_name}</CardTitle>
            <button onClick={() => setDetail(null)} className="text-xs text-slate-500 hover:underline">
              Close
            </button>
          </div>
          <dl className="mt-2 grid grid-cols-2 gap-2 text-xs sm:grid-cols-4">
            {(
              [
                ["SKU", detail.product_id],
                ["Category", detail.category],
                ["Revenue", `$${detail.revenue.toLocaleString()}`],
                ["Profit", `$${detail.profit.toLocaleString()}`],
                ["Margin", `${(detail.margin * 100).toFixed(1)}%`],
                ["Orders", String(detail.orders)],
              ] as const
            ).map(([k, v]) => (
              <div key={k} className="rounded bg-slate-50 px-2 py-1.5">
                <dt className="uppercase tracking-wide text-slate-500" style={{ fontSize: 10 }}>{k}</dt>
                <dd className="font-semibold">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>
      )}
    </div>
  );
}
