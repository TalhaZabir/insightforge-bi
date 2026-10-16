"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api";
import { QualityStep } from "@/components/imports/quality";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/kpi";

type Uploads = {
  file_id: string;
  filename: string;
  jobs: { id: string; status: string }[];
}[];

export default function QualityPage() {
  const q = useQuery({ queryKey: ["uploads"], queryFn: () => apiGet<Uploads>("/uploads") });
  const jobs = (q.data ?? []).flatMap((f) =>
    f.jobs.map((j) => ({ ...j, file: f.filename }))
  );
  const [jobId, setJobId] = useState<string | null>(null);
  const active = jobId ?? jobs.find((j) => j.status === "confirmed")?.id ?? jobs[0]?.id ?? null;

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <CardTitle>Data quality reports</CardTitle>
        <CardHint>Pick an import job to inspect validation, cleaning and rejections</CardHint>
        {jobs.length === 0 ? (
          <p className="mt-2 text-xs text-slate-500">No import jobs yet.</p>
        ) : (
          <select
            value={active ?? ""}
            onChange={(e) => setJobId(e.target.value)}
            className="mt-2 w-full max-w-md rounded-lg border border-slate-300 px-2 py-1.5 text-xs"
          >
            {jobs.map((j) => (
              <option key={j.id} value={j.id}>
                {j.file} · {j.status} · {j.id.slice(0, 8)}
              </option>
            ))}
          </select>
        )}
      </Card>
      {active ? (
        <QualityStep key={active} jobId={active} />
      ) : (
        <EmptyState title="Nothing to show" hint="Validate a file in Data Imports first." />
      )}
    </div>
  );
}
