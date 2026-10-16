"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { fmtCurrency, fmtNum } from "@/lib/format";
import { MoneyBars, TrendChart } from "@/components/charts/charts";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, KpiCard } from "@/components/ui/kpi";
import { ChartSkeleton, KpiSkeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type Sales = {
  kpis: { revenue: number; profit: number; orders: number; units: number; aov: number };
  trend: { grain: string; points: { date?: string; revenue: number; profit: number; orders: number }[] };
  by_channel: { channel: string; revenue: number; profit: number; margin: number; orders: number; revenue_growth?: number | null }[];
  by_region: { region: string; revenue: number; profit: number; margin: number; orders: number }[];
  by_category: { category: string; revenue: number; profit: number; margin: number; orders: number }[];
};

type Forecast = {
  available: boolean;
  reason?: string;
  history: { month: string; revenue: number }[];
  validation?: { months: string[]; actual: number[]; predicted: number[] };
  accuracy?: { model: string; mae: number | null; rmse: number | null; wape: number | null; validation_months: number };
  forecast?: { month: string; revenue: number }[];
  horizon: number;
  assumptions?: string;
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
  const fc = useQuery({
    queryKey: ["forecast", queryString],
    queryFn: () => apiGet<Forecast>(`/analytics/forecast${queryString}${queryString ? "&" : "?"}horizon=3`),
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
        <KpiCard label="Revenue" hint="Net sales, cancelled excluded" format={(v) => fmtCurrency(v)} data={{ value: q.data.kpis.revenue }} />
        <KpiCard label="Orders" hint="Distinct order IDs" format={(v) => fmtNum(v)} data={{ value: q.data.kpis.orders }} />
        <KpiCard label="Units" hint="Sum of quantities" format={(v) => fmtNum(v)} data={{ value: q.data.kpis.units }} />
        <KpiCard label="AOV" hint="Revenue divided by orders" format={(v) => fmtCurrency(v, 2)} data={{ value: q.data.kpis.aov }} />
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
        <div className="mt-2 overflow-x-auto" aria-busy={t.isPending}>
          {t.isPending ? (
            <ChartSkeleton />
          ) : (
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
          )}
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
      <Card className="p-5">
        <CardTitle>Revenue forecast</CardTitle>
        <CardHint>Baseline models (naive / seasonal-naive / moving-average) with chronological backtest</CardHint>
        <div className="mt-2 text-xs text-slate-600">
          {fc.isPending && <p>Loading forecast…</p>}
          {fc.isError && <p className="text-red-600">Forecast unavailable: {fc.error.message}</p>}
          {fc.data && !fc.data.available && <p>{fc.data.reason} Showing history only.</p>}
          {fc.data?.available && (
            <>
              <p>
                Best model: <span className="font-medium">{fc.data.accuracy?.model}</span> · MAE{" "}
                {fc.data.accuracy?.mae?.toLocaleString() ?? "N/A"} · RMSE{" "}
                {fc.data.accuracy?.rmse?.toLocaleString() ?? "N/A"} · WAPE{" "}
                {fc.data.accuracy?.wape?.toFixed(1) ?? "N/A"}% ({fc.data.accuracy?.validation_months} validation months)
              </p>
              <div className="mt-2 overflow-x-auto">
                <table className="min-w-full text-xs">
                  <thead>
                    <tr className="text-left text-slate-500">
                      <th className="px-2 py-1 font-medium">Month</th>
                      <th className="px-2 py-1 font-medium">Type</th>
                      <th className="px-2 py-1 font-medium">Revenue</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fc.data.history.slice(-6).map((h) => (
                      <tr key={h.month} className="border-t border-slate-100">
                        <td className="px-2 py-1 font-mono">{h.month}</td>
                        <td className="px-2 py-1">actual</td>
                        <td className="px-2 py-1 text-right">{fmtCurrency(h.revenue)}</td>
                      </tr>
                    ))}
                    {(fc.data.forecast ?? []).map((h) => (
                      <tr key={h.month} className="border-t border-teal-100 bg-teal-50/50">
                        <td className="px-2 py-1 font-mono">{h.month}</td>
                        <td className="px-2 py-1">forecast</td>
                        <td className="px-2 py-1 text-right">{fmtCurrency(h.revenue)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-[11px] text-slate-500">{fc.data.assumptions}</p>
            </>
          )}
        </div>
      </Card>
    </div>
  );
}
