"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { fmtCurrency, fmtNum } from "@/lib/format";
import { MixPie } from "@/components/charts/charts";
import { RankTable } from "@/components/charts/tables";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState, KpiCard } from "@/components/ui/kpi";
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
  rfm?: {
    customers: { customer_id: string; customer_name: string; r: number; f: number; m: number; rfm_score: number; rfm_label: string; revenue: number; orders: number }[];
    segments: { label: string; customers: number; revenue: number }[];
    scoring?: { method: string; labels: string };
  };
  cohorts?: { cohorts: { cohort: string; size: number; retention: (number | null)[] }[]; note: string };
  declining?: { customer_id: string; customer_name: string; first_half: number; second_half: number; decline_pct: number }[];
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
        <KpiCard label="Total customers" hint="Distinct customers in period" format={(v) => fmtNum(v)} data={{ value: m.total }} />
        <KpiCard label="New" hint="First purchase in period (lifetime definition)" format={(v) => fmtNum(v)} data={{ value: m.new }} />
        <KpiCard label="Returning" hint="Purchased before and in period" format={(v) => fmtNum(v)} data={{ value: m.returning }} />
        <KpiCard label="Repeat rate" hint="Returning share (lifetime definition)" format={(v) => (v === null || v === undefined ? "N/A" : `${v.toFixed(1)}%`)} data={{ value: m.repeat_rate }} />
        <KpiCard label="Avg revenue / customer" hint="Revenue per active customer" format={(v) => fmtCurrency(v)} data={{ value: m.avg_revenue }} />
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
      {q.data.rfm && q.data.rfm.segments.length > 0 && (
        <Card className="p-5">
          <CardTitle>RFM segmentation</CardTitle>
          <CardHint>{q.data.rfm.scoring?.method} {q.data.rfm.scoring?.labels}</CardHint>
          <div className="mt-2 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-left text-slate-500">
                  {["Segment", "Customers", "Revenue"].map((h) => (
                    <th key={h} className="px-2 py-1.5 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {q.data.rfm.segments.map((s) => (
                  <tr key={s.label} className="border-t border-slate-100">
                    <td className="px-2 py-1.5 font-medium">{s.label}</td>
                    <td className="px-2 py-1.5 text-right">{fmtNum(s.customers)}</td>
                    <td className="px-2 py-1.5 text-right">{fmtCurrency(s.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-left text-slate-500">
                  {["Customer", "R", "F", "M", "Score", "Label", "Revenue"].map((h) => (
                    <th key={h} className="px-2 py-1.5 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {q.data.rfm.customers.slice(0, 15).map((c) => (
                  <tr key={c.customer_id} className="border-t border-slate-100">
                    <td className="max-w-[160px] truncate px-2 py-1.5">{c.customer_name ?? c.customer_id}</td>
                    <td className="px-2 py-1.5 text-right">{c.r}</td>
                    <td className="px-2 py-1.5 text-right">{c.f}</td>
                    <td className="px-2 py-1.5 text-right">{c.m}</td>
                    <td className="px-2 py-1.5 text-right font-medium">{c.rfm_score}</td>
                    <td className="px-2 py-1.5">{c.rfm_label}</td>
                    <td className="px-2 py-1.5 text-right">{fmtCurrency(c.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {q.data.cohorts && q.data.cohorts.cohorts.length > 0 && (
        <Card className="p-5">
          <CardTitle>Monthly acquisition cohorts</CardTitle>
          <CardHint>{q.data.cohorts.note}</CardHint>
          <div className="mt-2 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-2 py-1.5 font-medium">Cohort</th>
                  <th className="px-2 py-1.5 font-medium">Size</th>
                  {q.data.cohorts.cohorts[0].retention.map((_, i) => (
                    <th key={i} className="px-2 py-1.5 font-medium">M{i}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {q.data.cohorts.cohorts.slice(0, 12).map((c) => (
                  <tr key={c.cohort} className="border-t border-slate-100">
                    <td className="px-2 py-1.5 font-mono">{c.cohort}</td>
                    <td className="px-2 py-1.5 text-right">{c.size}</td>
                    {c.retention.map((v, i) => (
                      <td
                        key={i}
                        className="px-2 py-1.5 text-right"
                        style={v === null ? undefined : { backgroundColor: `rgba(13,148,136,${Math.min(0.85, v)})` }}
                        title={v === null ? "Incomplete month" : `${(v * 100).toFixed(1)}% retained`}
                      >
                        {v === null ? "—" : `${(v * 100).toFixed(0)}%`}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {q.data.declining && q.data.declining.length > 0 && (
        <Card className="p-5">
          <CardTitle>Declining customers</CardTitle>
          <CardHint>Second-half revenue below 70% of first-half (dated ranges only)</CardHint>
          <div className="mt-2 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-left text-slate-500">
                  {["Customer", "First half", "Second half", "Change"].map((h) => (
                    <th key={h} className="px-2 py-1.5 font-medium">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {q.data.declining.map((d) => (
                  <tr key={d.customer_id} className="border-t border-slate-100">
                    <td className="px-2 py-1.5">{d.customer_name ?? d.customer_id}</td>
                    <td className="px-2 py-1.5 text-right">{fmtCurrency(d.first_half)}</td>
                    <td className="px-2 py-1.5 text-right">{fmtCurrency(d.second_half)}</td>
                    <td className="px-2 py-1.5 text-right text-red-600">{d.decline_pct.toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
