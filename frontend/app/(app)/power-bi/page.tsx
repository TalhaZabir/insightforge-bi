"use client";

import { useState } from "react";
import { toast } from "sonner";
import { downloadFile } from "@/lib/api";
import { useFilters } from "@/hooks/useFilters";
import { Button } from "@/components/ui/button";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/kpi";

const TABLES = [
  ["fact_sales", "One row per order line. Keys join to dimensions; date_key is YYYYMMDD."],
  ["dim_date", "Calendar 2023–2026 with year/quarter/month/weekday flags."],
  ["dim_customer", "customer_id → name and segment."],
  ["dim_product", "product_id → name, category, subcategory."],
  ["dim_region", "region + country."],
  ["dim_channel", "Online / Retail Store / Wholesale."],
  ["dim_sales_rep", "Sales representative names."],
];

export default function PowerBIPage() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { queryString } = useFilters();

  const download = async () => {
    setBusy(true);
    setError(null);
    try {
      await downloadFile(`/exports/power-bi${queryString}`, "insightforge_powerbi.zip");
      toast.success("Power BI bundle downloaded");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Export failed";
      setError(msg);
      toast.error("Export failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <Card className="p-5">
        <CardTitle>Power BI export bundle</CardTitle>
        <CardHint>Filtered star-schema CSVs (fact + dimensions) + DAX + manifest in one ZIP. Set filters on any analytics page first — this export respects the current filter context.</CardHint>
        <div className="mt-3">
          <Button disabled={busy} onClick={() => void download()}>
            {busy ? "Preparing…" : "Download bundle (.zip)"}
          </Button>
          {error && <ErrorState message={error} onRetry={() => void download()} />}
        </div>
      </Card>
      <Card className="p-5">
        <CardTitle>Star schema</CardTitle>
        <ul className="mt-2 space-y-1.5 text-xs text-slate-600">
          {TABLES.map(([t, d]) => (
            <li key={t} className="rounded bg-slate-50 px-2 py-1.5">
              <span className="font-mono font-medium text-slate-800">{t}</span> — {d}
            </li>
          ))}
        </ul>
      </Card>
      <Card className="p-5">
        <CardTitle>Connect Power BI in 5 steps</CardTitle>
        <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs text-slate-600">
          <li>Download the bundle above and extract the CSVs.</li>
          <li>Power BI Desktop → Get Data → Text/CSV → load all 7 files.</li>
          <li>Model view: drag <span className="font-mono">fact_sales[customer_key]</span> →{" "}
            <span className="font-mono">dim_customer[id]</span> (repeat for product, region,
            channel, rep; <span className="font-mono">date_key → dim_date[date_key]</span>).</li>
          <li>Set each relationship cardinality to Many-to-One, single direction.</li>
          <li>Paste the DAX measures from <span className="font-mono">docs/powerbi.md</span> (Part 9)
            into a measures table and build the recommended dashboard.</li>
        </ol>
        <p className="mt-3 text-xs text-slate-500">
          DirectQuery alternative: connect Power BI to PostgreSQL with the documented SQL views
          (<span className="font-mono">database/views/*.sql</span>) for always-fresh data.
        </p>
      </Card>
    </div>
  );
}
