"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiDelete, apiGet, apiPost, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { fmtCurrency } from "@/lib/format";

type Job = { id: string; status: string; stats: Record<string, unknown> | null };
type FileRow = {
  file_id: string;
  filename: string;
  size_bytes: number;
  sheets: string[] | null;
  created_at: string | null;
  jobs: Job[];
};

const tone = (s: string) =>
  s === "confirmed" ? "green" : s === "failed" ? "red" : s === "processing" ? "blue" : "slate";

export function ImportHistory({ onPick }: { onPick: (fileId: string) => void }) {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [applied, setApplied] = useState("");
  const q = useQuery({
    queryKey: ["uploads", applied],
    queryFn: () => apiGet<FileRow[] | { items: FileRow[] }>(`/uploads${applied ? `?search=${encodeURIComponent(applied)}` : ""}`),
  });
  const rows: FileRow[] = Array.isArray(q.data) ? q.data : (q.data?.items ?? []);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast.success(ok);
      void qc.invalidateQueries({ queryKey: ["uploads"] });
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Action failed");
    }
  };

  if (q.isPending) return <p className="text-xs text-slate-500">Loading history…</p>;
  if (q.isError) return <p className="text-xs text-red-600">History unavailable: {q.error.message}</p>;
  if (rows.length === 0)
    return <p className="text-xs text-slate-500">No uploads yet. Your import history will appear here.</p>;

  return (
    <Card className="p-5">
      <CardTitle>Import history</CardTitle>
      <form
        className="mt-2 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          setApplied(search);
        }}
      >
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by filename…"
          aria-label="Search import history"
          className="w-full max-w-xs rounded-lg border border-slate-300 px-2 py-1.5 text-xs"
        />
        <Button size="sm" variant="secondary" type="submit">
          Search
        </Button>
      </form>
      <div className="mt-3 space-y-3">
        {rows.map((f) => {
          const hasConfirmed = f.jobs.some((j) => j.status === "confirmed");
          const hasProcessing = f.jobs.some((j) => j.status === "processing");
          return (
          <div key={f.file_id} className="rounded-lg border border-slate-200 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-slate-800">{f.filename}</p>
                <p className="text-[11px] text-slate-500">
                  {(f.size_bytes / 1024).toFixed(0)} KB · {f.jobs.length} job(s)
                  {hasConfirmed ? " · includes confirmed data" : ""}
                </p>
              </div>
              <div className="flex gap-1.5">
                <Button size="sm" variant="secondary" onClick={() => onPick(f.file_id)}>
                  Open
                </Button>
                {hasConfirmed ? (
                  <Button
                    size="sm"
                    variant="danger"
                    title={
                      hasProcessing
                        ? "Cannot delete while an import is processing"
                        : "Delete file + all confirmed dashboard rows (cannot be undone)"
                    }
                    disabled={hasProcessing}
                    onClick={() => {
                      if (
                        window.confirm(
                          `Delete "${f.filename}" plus its confirmed dashboard data? This cannot be undone.`
                        )
                      ) {
                        void act(
                          () => apiDelete(`/uploads/${f.file_id}?force=true`),
                          "Upload and confirmed data deleted"
                        );
                      }
                    }}
                  >
                    Delete
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={hasProcessing}
                    title={hasProcessing ? "Cannot discard while processing" : "Discard upload"}
                    onClick={() =>
                      act(() => apiDelete(`/uploads/${f.file_id}`), "Upload discarded")
                    }
                  >
                    Discard
                  </Button>
                )}
              </div>
            </div>
            {f.jobs.length > 0 && (
              <ul className="mt-2 space-y-1.5">
                {f.jobs.map((j) => {
                  const s = (j.stats ?? {}) as {
                    validation?: { valid_rows: number };
                    confirmation?: { confirmed_rows: number; revenue_total: number };
                  };
                  return (
                    <li
                      key={j.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded bg-slate-50 px-2 py-1.5 text-xs"
                    >
                      <span className="flex items-center gap-2">
                        <Badge tone={tone(j.status) as "green" | "red" | "blue" | "slate"}>
                          {j.status}
                        </Badge>
                        <span className="font-mono text-slate-500">{j.id.slice(0, 8)}</span>
                        {s.confirmation && (
                          <span className="text-slate-600">
                            {s.confirmation.confirmed_rows.toLocaleString()} rows ·{" "}
                            {fmtCurrency(s.confirmation.revenue_total)}
                          </span>
                        )}
                      </span>
                      {["validated", "cleaned", "failed"].includes(j.status) && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() =>
                            act(() => apiPost(`/imports/${j.id}/cancel`), "Job cancelled")
                          }
                        >
                          Cancel
                        </Button>
                      )}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
          );
        })}
      </div>
    </Card>
  );
}
