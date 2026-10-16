"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet, API_URL, type User } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { AuthGuard } from "@/components/layout/guard";
import { Card, CardHint, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/kpi";
import { Skeleton } from "@/components/ui/skeleton";

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
    </div>
  );
}

export default function Page() {
  return (
    <AuthGuard roles={["admin"]}>
      <SettingsInner />
    </AuthGuard>
  );
}
