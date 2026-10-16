"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet, downloadFile } from "@/lib/api";
import { fmtCurrency } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/kpi";
import { Skeleton } from "@/components/ui/skeleton";
import type { CleaningSummary, Example, Issue, Transformation, ValidationSummary } from "./types";

type Quality = {
  job_id: string;
  status: string;
  validation: ValidationSummary | null;
  cleaning: (CleaningSummary & { transformations: Transformation[]; examples: Example[] }) | null;
  confirmation: unknown;
  issues_by_rule: Record<string, number>;
  issues_sample: Issue[];
};

export function QualityStep({ jobId }: { jobId: string }) {
  const [severity, setSeverity] = useState<string>("");
  const [rule, setRule] = useState<string>("");
  const [appliedRule, setAppliedRule] = useState<string>("");
  const params = new URLSearchParams();
  if (severity) params.set("severity", severity);
  if (appliedRule) params.set("rule", appliedRule);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const q = useQuery({
    queryKey: ["quality", jobId, severity, appliedRule],
    queryFn: () => apiGet<Quality>(`/data-quality/${jobId}${suffix}`),
  });

  if (q.isPending)
    return (
      <div className="space-y-2">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  if (q.isError) return <ErrorState message={q.error.message} onRetry={() => q.refetch()} />;

  const v = q.data.validation;
  if (!v) return <p className="text-sm text-slate-500">No validation data yet.</p>;

  const stat = (label: string, value: string | number, tone?: "green" | "red" | "amber") => (
    <div className="rounded-lg bg-slate-50 px-3 py-2">
      <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="text-lg font-semibold text-[#0A1628]">{value}</p>
      {tone && (
        <Badge tone={tone} className="mt-1">
          {tone === "green" ? "ok" : "attention"}
        </Badge>
      )}
    </div>
  );

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>Validation results</CardTitle>
          <Button
            size="sm"
            variant="secondary"
            onClick={() => void downloadFile(`/data-quality/${jobId}/rejections.csv`, `rejections_${jobId}.csv`)}
          >
            Download rejection report
          </Button>
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
          {stat("Rows detected", v.total_rows.toLocaleString())}
          {stat("Valid rows", v.valid_rows.toLocaleString(), "green")}
          {stat("Rejected", v.rejected_rows.toLocaleString(), v.rejected_rows > 0 ? "red" : "green")}
          {stat("Duplicates", v.duplicate_rows.toLocaleString(), v.duplicate_rows > 0 ? "amber" : "green")}
          {stat("Errors", v.errors, v.errors > 0 ? "red" : "green")}
          {stat("Warnings", v.warnings, v.warnings > 0 ? "amber" : "green")}
        </div>
        {Object.keys(v.invalid_by_column).length > 0 && (
          <p className="mt-3 text-xs text-slate-600">
            Invalid by column:{" "}
            {Object.entries(v.invalid_by_column)
              .map(([c, n]) => `${c} (${n})`)
              .join(", ")}
          </p>
        )}
        {(v.outlier_quantity > 0 || v.outlier_revenue > 0) && (
          <p className="mt-1 text-xs text-slate-600">
            Outliers flagged (kept, not rejected): {v.outlier_quantity} quantity, {v.outlier_revenue}{" "}
            revenue
          </p>
        )}
      </Card>

      {q.data.cleaning && (
        <Card className="p-5">
          <CardTitle>Cleaning summary</CardTitle>
          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
            {stat("Rows cleaned", q.data.cleaning.rows_cleaned.toLocaleString())}
            {stat("Duplicates removed", q.data.cleaning.duplicates_removed.toLocaleString())}
            {stat("Revenue after clean", fmtCurrency(q.data.cleaning.revenue_total))}
            {stat("Date range", `${q.data.cleaning.date_min ?? "—"} → ${q.data.cleaning.date_max ?? "—"}`)}
            {stat(
              "Transformations",
              q.data.cleaning.transformations.length
            )}
          </div>
          {q.data.cleaning.transformations.length > 0 && (
            <ul className="mt-3 space-y-1 text-xs text-slate-600">
              {q.data.cleaning.transformations.map((t) => (
                <li key={t.step} className="rounded bg-slate-50 px-2 py-1">
                  <span className="font-mono font-medium">{t.step}</span> — {t.affected_rows} rows.{" "}
                  {t.detail}
                </li>
              ))}
            </ul>
          )}
          {q.data.cleaning.examples.length > 0 && (
            <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
              <table className="min-w-full text-xs">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Row</th>
                    <th className="px-3 py-2 text-left font-medium">Before</th>
                    <th className="px-3 py-2 text-left font-medium">After</th>
                  </tr>
                </thead>
                <tbody>
                  {q.data.cleaning.examples.map((e, i) => (
                    <tr key={i} className="border-t border-slate-100 align-top">
                      <td className="px-3 py-1.5 font-mono">{e.row_num}</td>
                      <td className="px-3 py-1.5 font-mono text-red-700">{JSON.stringify(e.before)}</td>
                      <td className="px-3 py-1.5 font-mono text-emerald-700">{JSON.stringify(e.after)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      <Card className="p-5">
        <CardTitle>Issues by rule</CardTitle>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          <select
            value={severity}
            onChange={(e) => setSeverity(e.target.value)}
            aria-label="Filter by severity"
            className="rounded-lg border border-slate-300 px-2 py-1 text-xs"
          >
            <option value="">All severities</option>
            <option value="error">Errors (blocking)</option>
            <option value="warning">Warnings (non-blocking)</option>
          </select>
          <form
            className="flex gap-1.5"
            onSubmit={(e) => {
              e.preventDefault();
              setAppliedRule(rule);
            }}
          >
            <input
              value={rule}
              onChange={(e) => setRule(e.target.value)}
              placeholder="Filter by rule…"
              aria-label="Filter by rule"
              className="rounded-lg border border-slate-300 px-2 py-1 text-xs"
            />
            <Button size="sm" variant="secondary" type="submit">
              Filter
            </Button>
          </form>
        </div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {Object.entries(q.data.issues_by_rule).map(([rule, n]) => (
            <Badge key={rule} tone={rule.startsWith("error") ? "red" : "amber"}>
              {rule}: {n}
            </Badge>
          ))}
        </div>
        <div className="mt-3 max-h-72 overflow-auto rounded-lg border border-slate-200">
          <table className="min-w-full text-xs">
            <thead className="sticky top-0 bg-slate-50">
              <tr>
                {["Row", "Severity", "Rule", "Column", "Message"].map((h) => (
                  <th key={h} className="px-3 py-2 text-left font-medium text-slate-600">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {q.data.issues_sample.map((iss, i) => (
                <tr key={i} className="border-t border-slate-100">
                  <td className="px-3 py-1.5 font-mono">{iss.row_num}</td>
                  <td className="px-3 py-1.5">
                    <Badge tone={iss.severity === "error" ? "red" : "amber"}>{iss.severity}</Badge>
                  </td>
                  <td className="px-3 py-1.5 font-mono">{iss.rule}</td>
                  <td className="px-3 py-1.5 font-mono">{iss.column ?? "—"}</td>
                  <td className="px-3 py-1.5 text-slate-600">{iss.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
