"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { fmtCurrency, fmtNum } from "@/lib/format";
import { MixPie } from "@/components/charts/charts";
import { RankTable } from "@/components/charts/tables";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/kpi";
import { ChartSkeleton } from "@/components/ui/skeleton";

type Customers = {
  metrics: {
    total: number;
    new: number;
    returning: number;
    repeat_rate: number;
    avg_revenue: number;
    avg_order_value: number;
  };
  top_customers: {
    customer_id: string;
    customer_name: string;
    segment: string;
    revenue: number;
    profit: number;
    margin: number;
    orders: number;
    aov: number;
  }[];
  segment_mix: { segment: string; revenue: number; profit: number; margin: number; orders: number }[];
  revenue_concentration_top3: number;
  revenue_distribution: { bucket: string; customers: number; revenue: number }[];
};

export default function CustomersPage() {
  const { queryString } = useFilters();
  const q = useQuery({
    queryKey: ["customers", queryString],
    queryFn: () => apiGet<Customers>(`/analytics/customers${queryString}`),
  });

  if (q.isPending)
    return (
      <div className="space-y-4">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    );
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;
  const m = q.data.metrics;
  if (m.total === 0) return <EmptyState title="No customers in this selection" />;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        {[
          ["Total customers", fmtNum(m.total)],
          ["New", fmtNum(m.new)],
          ["Returning", fmtNum(m.returning)],
          ["Repeat rate", `${m.repeat_rate.toFixed(1)}%`],
          ["Avg revenue / customer", fmtCurrency(m.avg_revenue)],
        ].map(([k, v]) => (
          <Card key={k} className="p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{k}</p>
            <p className="mt-1 text-xl font-semibold">{v}</p>
          </Card>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <CardTitle>Customer segmentation</CardTitle>
          <CardHint>Revenue share by segment</CardHint>
          <div className="mt-2">
            <MixPie data={q.data.segment_mix} nameKey="segment" />
          </div>
        </Card>
        <Card className="p-5">
          <CardTitle>Revenue distribution</CardTitle>
          <CardHint>Customers per lifetime-revenue bucket · top-3 concentration{" "}
            {(q.data.revenue_concentration_top3 * 100).toFixed(1)}%</CardHint>
          <div className="mt-2">
            <MixPie
              data={q.data.revenue_distribution.map((d) => ({ revenue: d.revenue, segment: d.bucket }))}
              nameKey="segment"
            />
          </div>
        </Card>
      </div>
      <Card className="p-5">
        <CardTitle>Top customers by lifetime value</CardTitle>
        <div className="mt-2">
          <RankTable rows={q.data.top_customers} name={(r) => String(r.customer_name ?? r.customer_id)} />
        </div>
      </Card>
    </div>
  );
}
