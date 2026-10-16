"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPut, API_URL, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthGuard } from "@/components/layout/guard";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/kpi";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { fmtCurrency } from "@/lib/format";

type Target = { month: string; revenue_target: number; profit_target: number };
type Tracking = {
  available: boolean;
  month?: string;
  reason?: string;
  actual?: { revenue: number; profit: number };
  target?: { revenue: number; profit: number };
  variance?: { revenue_abs: number; revenue_pct: number | null; profit_abs: number; profit_pct: number | null };
  progress?: { revenue_pct_of_target: number | null; required_daily_revenue: number | null };
};

function SettingsInner() {
  const { user } = useAuth();
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () => apiGet<User[]>("/auth/users"),
    enabled: user?.role === "admin",
  });

  return (
    <div className="space-y-4">
      <Card className="p-6">
        <CardTitle>Workspace</CardTitle>
        <CardHint>Backend API: {API_URL || "Same origin (/api)"}</CardHint>
        <p className="mt-2 text-sm text-slate-600">
          Signed in as <span className="font-mono">{user?.email}</span> ({user?.role})
        </p>
      </Card>
      <Card className="p-6">
        <CardTitle>Users (admin)</CardTitle>
        <CardHint>Role-based access: admin, analyst, viewer</CardHint>
        {users.isPending ? (
          <Skeleton className="mt-3 h-20 w-full" />
        ) : users.isError ? (
          <div className="mt-3">
            <ErrorState message={users.error.message} onRetry={() => users.refetch()} />
          </div>
        ) : (
          <ul className="mt-3 divide-y divide-slate-100 text-sm">
            {users.data.map((u) => (
              <li key={u.id} className="flex items-center justify-between py-2">
                <span className="font-mono text-slate-700">{u.email}</span>
                <span className="capitalize text-slate-500">{u.role}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <TargetsCard />
    </div>
  );
}

function TargetsCard() {
  const qc = useQueryClient();
  const t = useQuery({ queryKey: ["targets"], queryFn: () => apiGet<Target[]>("/analytics/targets") });
  const tr = useQuery({ queryKey: ["target-tracking"], queryFn: () => apiGet<Tracking>("/analytics/targets/tracking") });
  const [month, setMonth] = useState("");
  const [rev, setRev] = useState("");
  const [prof, setProf] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const save = async () => {
    setMsg(null);
    if (!/^\d{4}-\d{2}$/.test(month)) {
      setMsg("Month must be YYYY-MM.");
      return;
    }
    try {
      await apiPut(`/analytics/targets/${month}`, {
        revenue_target: Number(rev) || 0,
        profit_target: Number(prof) || 0,
      });
      setMsg(`Target saved for ${month}.`);
      setMonth("");
      setRev("");
      setProf("");
      void qc.invalidateQueries({ queryKey: ["targets"] });
      void qc.invalidateQueries({ queryKey: ["target-tracking"] });
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    }
  };

  return (
    <Card className="p-6">
      <CardTitle>Monthly targets</CardTitle>
      <CardHint>Actual vs target with variance and required daily run-rate</CardHint>
      {tr.data?.available ? (
        <p className="mt-2 text-xs text-slate-600">
          {tr.data.month}: actual {fmtCurrency(tr.data.actual?.revenue)} vs target{" "}
          {fmtCurrency(tr.data.target?.revenue)} (
          {tr.data.variance?.revenue_pct === null || tr.data.variance?.revenue_pct === undefined
            ? "N/A"
            : `${tr.data.variance.revenue_pct.toFixed(1)}%`}
          ) · progress {tr.data.progress?.revenue_pct_of_target?.toFixed(1) ?? "N/A"}% · required daily{" "}
          {tr.data.progress?.required_daily_revenue === null || tr.data.progress?.required_daily_revenue === undefined
            ? "N/A"
            : fmtCurrency(tr.data.progress.required_daily_revenue)}
        </p>
      ) : (
        <p className="mt-2 text-xs text-slate-500">{tr.data?.reason ?? "Loading…"}</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <input value={month} onChange={(e) => setMonth(e.target.value)} placeholder="YYYY-MM" aria-label="Target month" className="w-28 rounded-lg border border-slate-300 px-2 py-1.5" />
        <input value={rev} onChange={(e) => setRev(e.target.value)} placeholder="Revenue target" aria-label="Revenue target" inputMode="decimal" className="w-36 rounded-lg border border-slate-300 px-2 py-1.5" />
        <input value={prof} onChange={(e) => setProf(e.target.value)} placeholder="Profit target" aria-label="Profit target" inputMode="decimal" className="w-36 rounded-lg border border-slate-300 px-2 py-1.5" />
        <Button size="sm" onClick={() => void save()}>Save target</Button>
      </div>
      {msg && <p className="mt-2 text-xs text-slate-600">{msg}</p>}
      <div className="mt-3">
        {t.isPending ? (
          <Skeleton className="h-16 w-full" />
        ) : (
          <ul className="divide-y divide-slate-100 text-xs">
            {(t.data ?? []).map((r) => (
              <li key={r.month} className="flex justify-between py-1.5">
                <span className="font-mono">{r.month}</span>
                <span>
                  {fmtCurrency(r.revenue_target)} rev · {fmtCurrency(r.profit_target)} profit
                </span>
              </li>
            ))}
            {(t.data ?? []).length === 0 && <li className="py-1.5 text-slate-500">No targets yet.</li>}
          </ul>
        )}
      </div>
    </Card>
  );
}

export default function Page() {
  return (
    <AuthGuard roles={["admin", "analyst"]}>
      <SettingsInner />
    </AuthGuard>
  );
}
