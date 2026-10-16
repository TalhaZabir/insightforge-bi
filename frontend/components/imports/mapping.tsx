"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { CANONICAL_FIELDS, REQUIRED, type PreviewData } from "./types";

export function PreviewStep({
  preview,
  sheet,
  onSheet,
  mapping,
  onMapping,
}: {
  preview: PreviewData;
  sheet: string | null;
  onSheet: (s: string | null) => void;
  mapping: Record<string, string>;
  onMapping: (m: Record<string, string>) => void;
}) {
  const cols = preview.columns;
  const rows = preview.rows.slice(0, 8);

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <CardTitle>File structure</CardTitle>
        <p className="mt-1 text-xs text-slate-500">
          {preview.total_rows.toLocaleString()} rows detected · {cols.length} columns
        </p>
        {preview.sheets && preview.sheets.length > 1 && (
          <label className="mt-3 flex max-w-xs flex-col gap-1 text-xs font-medium text-slate-600">
            Worksheet
            <select
              value={sheet ?? ""}
              onChange={(e) => onSheet(e.target.value || null)}
              className="rounded-lg border border-slate-300 px-2 py-1.5 text-sm"
            >
              {preview.sheets.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        )}
        <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full text-xs">
            <thead className="bg-slate-50">
              <tr>
                {cols.map((c) => (
                  <th key={c} className="whitespace-nowrap px-3 py-2 text-left font-medium text-slate-600">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-t border-slate-100">
                  {cols.map((c) => (
                    <td key={c} className="max-w-[180px] truncate px-3 py-1.5 text-slate-700">
                      {r[c] ?? ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="p-5">
        <CardTitle>Column mapping</CardTitle>
        <p className="mt-1 text-xs text-slate-500">
          Map file columns to the business schema. Suggestions come from known header aliases —
          adjust any row. Required fields are marked.
        </p>
        <div className="mt-3 grid grid-cols-1 gap-2 md:grid-cols-2">
          {CANONICAL_FIELDS.map((field) => (
            <label key={field} className="flex items-center gap-2 text-xs">
              <span className="w-36 shrink-0 font-mono text-slate-600">
                {field}
                {REQUIRED.includes(field) && <span className="text-red-500"> *</span>}
              </span>
              <select
                value={mapping[field] ?? ""}
                onChange={(e) => onMapping({ ...mapping, [field]: e.target.value })}
                className="min-w-0 flex-1 rounded-lg border border-slate-300 px-2 py-1.5 text-xs"
              >
                <option value="">— not mapped —</option>
                {cols.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
              {mapping[field] && <Badge tone="teal">mapped</Badge>}
            </label>
          ))}
        </div>
      </Card>
    </div>
  );
}
