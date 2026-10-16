"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { Badge } from "@/components/ui/badge";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/kpi";
import { Skeleton } from "@/components/ui/skeleton";

type Insight = {
  category: "trend" | "opportunity" | "risk" | "quality";
  severity: "positive" | "neutral" | "warning" | "critical";
  headline: string;
  explanation: string;
  metric: { label: string; value: number; unit: string };
  action: string;
  dimension: { type: string; value: string } | null;
};

const sevTone = (s: Insight["severity"]) =>
  s === "positive" ? "green" : s === "critical" ? "red" : s === "warning" ? "amber" : "slate";
const catTone = (c: Insight["category"]) =>
  c === "opportunity" ? "teal" : c === "risk" ? "red" : c === "quality" ? "amber" : "blue";

const ORDER: Insight["category"][] = ["risk", "opportunity", "trend", "quality"];

export default function InsightsPage() {
  const { queryString } = useFilters();
  const q = useQuery({
    queryKey: ["insights", queryString],
    queryFn: () => apiGet<{ insights: Insight[]; generated_at: string }>(`/insights${queryString}`),
  });

  if (q.isPending)
    return (
      <div className="space-y-2">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;
  if (q.data.insights.length === 0) return <EmptyState title="No insights for this selection" />;

  const groups = ORDER.map((c) => ({
    cat: c,
    items: q.data.insights.filter((i) => i.category === c),
  })).filter((g) => g.items.length > 0);

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <CardTitle>Executive summary</CardTitle>
        <CardHint>
          Deterministic commentary computed from live metrics ·{" "}
          {new Date(q.data.generated_at).toLocaleString()} · every insight traces to a
          calculated value, never fabricated.
        </CardHint>
      </Card>
      {groups.map((g) => (
        <section key={g.cat} aria-label={g.cat}>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            {g.cat} ({g.items.length})
          </h2>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {g.items.map((i, k) => (
              <Card key={k} className="p-4">
                <p className="flex flex-wrap items-center gap-1.5 text-sm font-semibold text-slate-900">
                  <Badge tone={catTone(i.category)}>{i.category}</Badge>
                  <Badge tone={sevTone(i.severity)}>{i.severity}</Badge>
                  {i.headline}
                </p>
                <p className="mt-1.5 text-xs text-slate-600">{i.explanation}</p>
                <p className="mt-1.5 font-mono text-xs text-slate-700">
                  {i.metric.label}: {i.metric.value.toLocaleString()}
                  {i.metric.unit}
                </p>
                {i.dimension && (
                  <p className="mt-0.5 text-xs text-slate-500">
                    Related {i.dimension.type}: <span className="font-medium">{i.dimension.value}</span>
                  </p>
                )}
                <p className="mt-2 rounded-lg bg-teal-50 px-2.5 py-1.5 text-xs text-teal-900">
                  <span className="font-semibold">Recommended: </span>
                  {i.action}
                </p>
              </Card>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
