"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { fmtCurrency, fmtNum } from "@/lib/format";
import { MoneyBars, TrendChart } from "@/components/charts/charts";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/kpi";
import { ChartSkeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Sales = {
  kpis: { revenue: number; profit: number; orders: number; units: number; aov: number };
  trend: { grain: string; points: { date?: string; revenue: number; profit: number; orders: number }[] };
  by_channel: { channel: string; revenue: number; profit: number; margin: number; orders: number; revenue_growth?: number | null }[];
  by_region: { region: string; revenue: number; profit: number; margin: number; orders: number }[];
  by_category: { category: string; revenue: number; profit: number; margin: number; orders: number }[];
};

type Orders = {
  total: number;
  page: number;
  page_size: number;
  items: {
    order_id: string;
    order_date: string | null;
    customer: string | null;
    product: string | null;
    category: string | null;
    region: string | null;
    channel: string | null;
    quantity: number;
    revenue: number;
    profit: number;
    status: string | null;
  }[];
};

export default function SalesPage() {
  const { queryString } = useFilters();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState("");
  const q = useQuery({
    queryKey: ["sales", queryString],
    queryFn: () => apiGet<Sales>(`/analytics/sales${queryString}`),
  });
  const t = useQuery({
    queryKey: ["orders", queryString, page, applied],
    queryFn: () =>
      apiGet<Orders>(
        `/analytics/sales/orders${queryString}${queryString ? "&" : "?"}page=${page}&page_size=15&sort=order_date&direction=desc&search=${encodeURIComponent(applied)}`
      ),
  });

  if (q.isPending)
    return (
      <div className="space-y-4">
        <ChartSkeleton />
        <ChartSkeleton />
      </div>
    );
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;
  if (q.data.kpis.orders === 0)
    return <EmptyState title="No sales in this selection" hint="Widen the date range or clear filters." />;

  const pages = t.data ? Math.max(1, Math.ceil(t.data.total / t.data.page_size)) : 1;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {[
          ["Revenue", fmtCurrency(q.data.kpis.revenue)],
          ["Orders", fmtNum(q.data.kpis.orders)],
          ["Units", fmtNum(q.data.kpis.units)],
          ["AOV", fmtCurrency(q.data.kpis.aov, 2)],
        ].map(([k, v]) => (
          <Card key={k} className="p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{k}</p>
            <p className="mt-1 text-xl font-semibold">{v}</p>
          </Card>
        ))}
      </div>
      <Card className="p-5">
        <CardTitle>Revenue over time</CardTitle>
        <CardHint>{q.data.trend.grain} grain</CardHint>
        <div className="mt-2">
          <TrendChart points={q.data.trend.points} />
        </div>
      </Card>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card className="p-5">
          <CardTitle>Revenue by channel</CardTitle>
          <div className="mt-2">
            <MoneyBars data={q.data.by_channel} nameKey="channel" />
          </div>
        </Card>
        <Card className="p-5">
          <CardTitle>Revenue by category</CardTitle>
          <div className="mt-2">
            <MoneyBars data={q.data.by_category} nameKey="category" />
          </div>
        </Card>
      </div>
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Detailed orders</CardTitle>
          <form
            className="flex gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setPage(1);
              setApplied(search);
            }}
          >
            <Input
              placeholder="Search order or product…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-56"
            />
            <Button size="sm" variant="secondary" type="submit">
              Search
            </Button>
          </form>
        </div>
        <div className="mt-2 overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="text-left text-slate-500">
                {["Order", "Date", "Customer", "Product", "Region", "Channel", "Qty", "Revenue", "Profit", "Status"].map(
                  (h) => (
                    <th key={h} className="whitespace-nowrap px-2 py-1.5 font-medium">
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {(t.data?.items ?? []).map((r, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-2 py-1.5 font-mono">{r.order_id}</td>
                  <td className="px-2 py-1.5">{r.order_date}</td>
                  <td className="max-w-[140px] truncate px-2 py-1.5">{r.customer ?? "—"}</td>
                  <td className="max-w-[160px] truncate px-2 py-1.5">{r.product ?? "—"}</td>
                  <td className="px-2 py-1.5">{r.region ?? "—"}</td>
                  <td className="px-2 py-1.5">{r.channel ?? "—"}</td>
                  <td className="px-2 py-1.5 text-right">{fmtNum(r.quantity)}</td>
                  <td className="px-2 py-1.5 text-right">{fmtCurrency(r.revenue)}</td>
                  <td className="px-2 py-1.5 text-right">{fmtCurrency(r.profit)}</td>
                  <td className="px-2 py-1.5">{r.status ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
          <span>
            {t.data?.total.toLocaleString() ?? 0} orders · page {page} of {pages}
          </span>
          <div className="flex gap-1.5">
            <Button size="sm" variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
              Prev
            </Button>
            <Button size="sm" variant="secondary" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
              Next
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
