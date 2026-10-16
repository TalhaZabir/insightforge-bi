"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
  observed?: number | null;
  baseline?: number | null;
  pct_change?: number | null;
  calculation?: string | null;
  limitations?: string | null;
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
  const [dismissed, setDismissed] = useState<string[]>(() => {
    try {
      return JSON.parse(localStorage.getItem("if_dismissed_insights") ?? "[]");
    } catch {
      return [];
    }
  });
  const dismiss = (headline: string) => {
    const next = [...dismissed, headline];
    setDismissed(next);
    try {
      localStorage.setItem("if_dismissed_insights", JSON.stringify(next));
    } catch {
      /* ignore */
    }
  };

  if (q.isPending)
    return (
      <div className="space-y-2">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;
  const visible = q.data.insights.filter((i) => !dismissed.includes(i.headline));
  if (visible.length === 0) return <EmptyState title="No insights for this selection" />;

  const groups = ORDER.map((c) => ({
    cat: c,
    items: visible.filter((i) => i.category === c),
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
                {(i.calculation || i.limitations) && (
                  <p className="mt-1 text-[11px] text-slate-500">
                    {i.calculation && <span>How: {i.calculation} </span>}
                    {i.limitations && <span>Limit: {i.limitations}</span>}
                  </p>
                )}
                <p className="mt-2 rounded-lg bg-teal-50 px-2.5 py-1.5 text-xs text-teal-900">
                  <span className="font-semibold">Recommended: </span>
                  {i.action}
                </p>
                <div className="mt-2">
                  <Button size="sm" variant="ghost" onClick={() => dismiss(i.headline)}>
                    Dismiss
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
