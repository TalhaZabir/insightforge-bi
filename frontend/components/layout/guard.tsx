"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Skeleton } from "@/components/ui/skeleton";

export function AuthGuard({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: string[];
}) {
  const { user, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!ready) return;
    if (!user) router.replace("/login");
    else if (roles && !roles.includes(user.role)) router.replace("/forbidden");
  }, [ready, user, roles, router]);

  if (!ready || !user) {
    return (
      <div className="space-y-3 p-6">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }
  if (roles && !roles.includes(user.role)) return null;
  return <>{children}</>;
}
