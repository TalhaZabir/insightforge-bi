"use client";

import { useCallback, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiGet, apiPost, ApiError, type UploadResult } from "@/lib/api";
import { fmtCurrency } from "@/lib/format";
import { AuthGuard } from "@/components/layout/guard";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { Dropzone } from "@/components/imports/dropzone";
import { ImportHistory } from "@/components/imports/history";
import { PreviewStep } from "@/components/imports/mapping";
import { QualityStep } from "@/components/imports/quality";
import type { JobStats, PreviewData } from "@/components/imports/types";

type Phase = "upload" | "map" | "quality" | "confirming" | "done";

const STEPS = ["Upload", "Map columns", "Validate & clean", "Confirm", "Done"];

function Wizard() {
  const qc = useQueryClient();
  const [file, setFile] = useState<UploadResult | null>(null);
  const [sheet, setSheet] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [jobId, setJobId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("upload");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);

  const loadPreview = useCallback(async (fileId: string, sh: string | null) => {
    const p = await apiPost<PreviewData>(`/uploads/${fileId}/preview`, { sheet: sh, limit: 20 });
    setPreview(p);
    setMapping((m) => (Object.keys(m).length ? m : p.suggested_mapping));
  }, []);

  const onUploaded = async (r: UploadResult) => {
    setFile(r);
    setJobId(null);
    setFailed(null);
    const sh = r.sheets && r.sheets.length > 0 ? r.sheets[0] : null;
    setSheet(sh);
    try {
      await loadPreview(r.file_id, sh);
      setPhase("map");
      toast.success(`Uploaded ${r.filename}`);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Preview failed");
    }
    void qc.invalidateQueries({ queryKey: ["uploads"] });
  };

  const onSheet = async (sh: string | null) => {
    if (!file) return;
    setSheet(sh);
    try {
      await loadPreview(file.file_id, sh);
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Sheet preview failed");
    }
  };

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  };

  const doValidate = () =>
    run(async () => {
      if (!file) return;
      const r = await apiPost<{ job_id: string }>(`/uploads/${file.file_id}/validate`, {
        sheet,
        mapping: Object.fromEntries(Object.entries(mapping).filter(([, v]) => v)),
      });
      setJobId(r.job_id);
      setPhase("quality");
      toast.success("Validation complete");
      void qc.invalidateQueries({ queryKey: ["uploads"] });
    });

  const doClean = () =>
    run(async () => {
      if (!file || !jobId) return;
      await apiPost(`/uploads/${file.file_id}/clean`, { job_id: jobId });
      toast.success("Cleaning complete — review the summary");
      await qc.invalidateQueries({ queryKey: ["quality", jobId] });
    });

  const doConfirm = () =>
    run(async () => {
      if (!file || !jobId) return;
      await apiPost(`/uploads/${file.file_id}/confirm`, { job_id: jobId });
      setPhase("confirming");
    });

  // poll while confirming
  useEffect(() => {
    if (phase !== "confirming" || !jobId) return;
    const t = setInterval(async () => {
      try {
        const s = await apiGet<{ status: string }>(`/imports/${jobId}/status`);
        if (s.status === "confirmed") {
          clearInterval(t);
          setPhase("done");
          toast.success("Import confirmed — dashboards updated");
          void qc.invalidateQueries({ queryKey: ["uploads"] });
          void qc.invalidateQueries({ queryKey: ["quality", jobId] });
        } else if (s.status === "failed") {
          clearInterval(t);
          setFailed("Import failed during load. Fix the error and retry validation.");
          setPhase("quality");
        }
      } catch {
        /* keep polling */
      }
    }, 1000);
    return () => clearInterval(t);
  }, [phase, jobId, qc]);

  const openExisting = async (fileId: string) => {
    try {
      const f = await apiGet<{
        file_id: string;
        filename: string;
        size_bytes: number;
        sheets: string[] | null;
      }>(`/uploads/${fileId}`);
      setFile({ file_id: f.file_id, filename: f.filename, size_bytes: f.size_bytes, sheets: f.sheets });
      setJobId(null);
      setFailed(null);
      const sh = f.sheets && f.sheets.length > 0 ? f.sheets[0] : null;
      setSheet(sh);
      await loadPreview(f.file_id, sh);
      setPhase("map");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Could not open file");
    }
  };

  const stepIndex = { upload: 0, map: 1, quality: 2, confirming: 3, done: 4 }[phase];

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <CardTitle>Import wizard</CardTitle>
        <CardHint>Upload → preview → map → validate → clean → confirm</CardHint>
        <ol className="mt-3 flex flex-wrap gap-1.5" aria-label="Progress">
          {STEPS.map((s, i) => (
            <li key={s}>
              <Badge tone={i < stepIndex ? "teal" : i === stepIndex ? "blue" : "slate"}>
                {i + 1}. {s}
              </Badge>
            </li>
          ))}
        </ol>
      </Card>

      {phase === "upload" && <Dropzone onUploaded={(r) => void onUploaded(r)} />}

      {phase !== "upload" && file && (
        <Card className="p-4 text-xs text-slate-600">
          Working on <span className="font-medium text-slate-800">{file.filename}</span>{" "}
          ({(file.size_bytes / 1024).toFixed(0)} KB)
          <Button size="sm" variant="ghost" className="ml-3" onClick={() => setPhase("upload")}>
            New upload
          </Button>
        </Card>
      )}

      {phase === "map" && preview && (
        <>
          <PreviewStep preview={preview} sheet={sheet} onSheet={(s) => void onSheet(s)} mapping={mapping} onMapping={setMapping} />
          <div className="flex gap-2">
            <Button disabled={busy} onClick={() => void doValidate()}>
              {busy ? "Validating…" : "Run validation"}
            </Button>
          </div>
        </>
      )}

      {(phase === "quality" || phase === "confirming") && jobId && (
        <>
          {failed && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700" role="alert">
              {failed}
            </p>
          )}
          <QualityStep jobId={jobId} />
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => void doValidate()}>
              Re-run validation
            </Button>
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => void doClean()}>
              {busy ? "Working…" : "Apply cleaning"}
            </Button>
            <Button disabled={busy || phase === "confirming"} onClick={() => void doConfirm()}>
              {phase === "confirming" ? "Importing…" : "Confirm & import"}
            </Button>
          </div>
          {phase === "confirming" && (
            <p className="text-xs text-slate-500" aria-live="polite">
              Loading cleaned data into PostgreSQL… this polls the job status until it confirms.
            </p>
          )}
        </>
      )}

      {phase === "done" && jobId && <Completion jobId={jobId} />}

      <ImportHistory onPick={(id) => void openExisting(id)} />
    </div>
  );
}

function Completion({ jobId }: { jobId: string }) {
  const [stats, setStats] = useState<JobStats | null>(null);
  useEffect(() => {
    apiGet<{ stats: JobStats }>(`/imports/${jobId}/status`)
      .then((s) => setStats(s.stats))
      .catch(() => undefined);
  }, [jobId]);
  const v = stats?.validation;
  const c = stats?.cleaning;
  const cf = stats?.confirmation;
  if (!v || !cf) return null;
  const rows: [string, string][] = [
    ["Rows detected", v.total_rows.toLocaleString()],
    ["Valid rows", (c?.valid_rows ?? v.valid_rows).toLocaleString()],
    ["Rows cleaned", (c?.rows_cleaned ?? 0).toLocaleString()],
    ["Duplicates removed", (c?.duplicates_removed ?? v.duplicate_rows).toLocaleString()],
    ["Rows rejected", v.rejected_rows.toLocaleString()],
    ["Revenue after cleaning", fmtCurrency(cf.revenue_total)],
    ["Date range", `${cf.date_min} → ${cf.date_max}`],
    ["Customers", cf.customers.toLocaleString()],
    ["Products", cf.products.toLocaleString()],
    ["Regions", cf.regions.toLocaleString()],
  ];
  return (
    <Card className="border-emerald-200 bg-emerald-50/50 p-5">
      <CardTitle>Import complete</CardTitle>
      <dl className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-5">
        {rows.map(([k, val]) => (
          <div key={k} className="rounded-lg bg-white px-3 py-2">
            <dt className="text-[11px] uppercase tracking-wide text-slate-500">{k}</dt>
            <dd className="text-sm font-semibold text-[#0A1628]">{val}</dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}

export default function Page() {
  return (
    <AuthGuard roles={["admin", "analyst"]}>
      <Wizard />
    </AuthGuard>
  );
}
