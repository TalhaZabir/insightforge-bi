"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { fmtCurrency, fmtMargin } from "@/lib/format";
import { MoneyBars, TrendChart } from "@/components/charts/charts";
import { RankTable } from "@/components/charts/tables";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState, ErrorState, KpiCard } from "@/components/ui/kpi";
import { ChartSkeleton } from "@/components/ui/skeleton";

type Profit = {
  kpis: { revenue: number; profit: number; margin: number };
  trend: { grain: string; points: { date?: string; revenue: number; profit: number; orders: number }[] };
  by_category: { category: string; revenue: number; profit: number; margin: number; orders: number; avg_discount?: number }[];
  by_product: Product[];
  low_margin_products: Product[];
  discount_buckets: { bucket: string; revenue: number; profit: number; margin: number; orders: number }[];
};

type Product = {
  product_id: string;
  product_name: string;
  category: string;
  revenue: number;
  profit: number;
  margin: number;
  orders: number;
  low_margin?: boolean;
};

export default function ProfitPage() {
  const { queryString } = useFilters();
  const q = useQuery({
    queryKey: ["profit", queryString],
    queryFn: () => apiGet<Profit>(`/analytics/profitability${queryString}`),
  });

  if (q.isPending)
    return (
      <div className="space-y-4">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    );
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;
  if (q.data.kpis.revenue === 0) return <EmptyState title="No data in this selection" />;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <KpiCard label="Gross profit" hint="Revenue minus COGS and shipping" format={(v) => fmtCurrency(v)} data={{ value: q.data.kpis.profit }} />
        <KpiCard label="Profit margin" hint="Profit divided by revenue (weighted)" format={fmtMargin} data={{ value: q.data.kpis.margin }} />
        <KpiCard label="Total cost" hint="Revenue minus profit (COGS + shipping)" format={(v) => fmtCurrency(v)} data={{ value: q.data.kpis.revenue - q.data.kpis.profit }} />
      </div>

      {q.data.low_margin_products.length > 0 && (
        <Card className="border-amber-200 bg-amber-50/60 p-5">
          <CardTitle>Low-margin alerts</CardTitle>
          <CardHint>High-revenue products earning under 10% margin</CardHint>
          <ul className="mt-2 space-y-1 text-xs">
            {q.data.low_margin_products.slice(0, 5).map((p) => (
              <li key={p.product_id} className="flex items-center gap-2">
                <Badge tone="red">low margin</Badge>
                <span className="font-medium">{p.product_name}</span>
                <span className="text-slate-500">
                  {fmtCurrency(p.revenue)} at {fmtMargin(p.margin)}
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card className="p-5">
        <CardTitle>Cost vs revenue trend</CardTitle>
        <div className="mt-2">
          <TrendChart points={q.data.trend.points} />
        </div>
      </Card>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <CardTitle>Profit by category</CardTitle>
          <div className="mt-2">
            <MoneyBars data={q.data.by_category} nameKey="category" />
          </div>
        </Card>
        <Card className="p-5">
          <CardTitle>Discount vs margin</CardTitle>
          <CardHint>none / low (≤10%) / high (&gt;10%) discount buckets</CardHint>
          <div className="mt-2">
            <MoneyBars data={q.data.discount_buckets} nameKey="bucket" />
          </div>
        </Card>
      </div>
      <Card className="p-5">
        <CardTitle>Product profitability</CardTitle>
        <div className="mt-2">
          <RankTable rows={q.data.by_product} name={(r) => String(r.product_name)} />
        </div>
      </Card>
    </div>
  );
}
