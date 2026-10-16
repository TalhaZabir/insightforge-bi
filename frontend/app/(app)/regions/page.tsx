"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { MoneyBars, TrendChart } from "@/components/charts/charts";
import { RankTable } from "@/components/charts/tables";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/kpi";
import { ChartSkeleton } from "@/components/ui/skeleton";

type Regions = {
  ranking: {
    rank: number;
    region: string;
    country: string;
    revenue: number;
    profit: number;
    margin: number;
    orders: number;
    revenue_growth?: number | null;
  }[];
  by_channel: { channel: string; revenue: number; profit: number; margin: number; orders: number; revenue_growth?: number | null }[];
  trend: { grain: string; points: { date?: string; revenue: number; profit: number; orders: number }[] };
};

export default function RegionsPage() {
  const { queryString } = useFilters();
  const q = useQuery({
    queryKey: ["regions", queryString],
    queryFn: () => apiGet<Regions>(`/analytics/regions${queryString}`),
  });

  if (q.isPending)
    return (
      <div className="space-y-4">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    );
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;
  if (q.data.ranking.length === 0) return <EmptyState title="No regional data in this selection" />;

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <CardTitle>Regional ranking</CardTitle>
        <CardHint>Growth compares against the previous equivalent period</CardHint>
        <div className="mt-2">
          <RankTable rows={q.data.ranking} name={(r) => `${r.region ?? "Unspecified"} · ${r.country ?? ""}`} />
        </div>
      </Card>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <CardTitle>Channel comparison</CardTitle>
          <div className="mt-2">
            <MoneyBars data={q.data.by_channel} nameKey="channel" horizontal />
          </div>
        </Card>
        <Card className="p-5">
          <CardTitle>Performance trend</CardTitle>
          <div className="mt-2">
            <TrendChart points={q.data.trend.points} />
          </div>
        </Card>
      </div>
    </div>
  );
}
