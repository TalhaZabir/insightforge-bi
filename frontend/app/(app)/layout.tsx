"use client";

import { AppShell } from "@/components/layout/appshell";
import { AuthGuard } from "@/components/layout/guard";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
