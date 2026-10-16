"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BadgeCheck,
  Download,
  Globe2,
  LayoutDashboard,
  Lightbulb,
  LineChart,
  Package,
  Percent,
  Settings,
  Upload,
  Users,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/cn";

export type NavItem = {
  href: string;
  label: string;
  icon: React.ComponentType<{ size?: number | string; className?: string }>;
  roles: string[];
};

export const NAV: NavItem[] = [
  { href: "/overview", label: "Overview", icon: LayoutDashboard, roles: ["admin", "analyst", "viewer"] },
  { href: "/imports", label: "Data Imports", icon: Upload, roles: ["admin", "analyst"] },
  { href: "/sales", label: "Sales Analytics", icon: LineChart, roles: ["admin", "analyst", "viewer"] },
  { href: "/profitability", label: "Profitability", icon: Percent, roles: ["admin", "analyst", "viewer"] },
  { href: "/customers", label: "Customers", icon: Users, roles: ["admin", "analyst", "viewer"] },
  { href: "/products", label: "Products", icon: Package, roles: ["admin", "analyst", "viewer"] },
  { href: "/regions", label: "Regions & Channels", icon: Globe2, roles: ["admin", "analyst", "viewer"] },
  { href: "/quality", label: "Data Quality", icon: BadgeCheck, roles: ["admin", "analyst", "viewer"] },
  { href: "/insights", label: "Executive Insights", icon: Lightbulb, roles: ["admin", "analyst", "viewer"] },
  { href: "/power-bi", label: "Power BI Export", icon: Download, roles: ["admin", "analyst", "viewer"] },
  { href: "/settings", label: "Settings", icon: Settings, roles: ["admin", "analyst"] },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const items = NAV.filter((n) => user && n.roles.includes(user.role));

  return (
    <>
      {open && (
        <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={onClose} aria-hidden />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-[#0A1628] text-slate-200 transition-transform",
          open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="flex items-center gap-3 px-5 py-5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-teal-500 text-sm font-bold text-white">
            IF
          </div>
          <div>
            <p className="text-sm font-semibold text-white">InsightForge BI</p>
            <p className="text-[11px] text-slate-400">Retail analytics</p>
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3" aria-label="Primary">
          {items.map((n) => {
            const active = pathname === n.href || pathname.startsWith(n.href + "/");
            const Icon = n.icon;
            return (
              <Link
                key={n.href}
                href={n.href}
                onClick={onClose}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  active ? "bg-white/10 text-white" : "text-slate-300 hover:bg-white/5 hover:text-white"
                )}
                aria-current={active ? "page" : undefined}
              >
                <Icon size={17} />
                {n.label}
              </Link>
            );
          })}
        </nav>
        <div className="border-t border-white/10 p-4 text-xs">
          <p className="truncate text-slate-300">{user?.email}</p>
          <p className="mt-0.5 capitalize text-slate-500">{user?.role}</p>
          <button
            onClick={() => void logout().then(() => (window.location.href = "/login"))}
            className="mt-2 w-full rounded-lg bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20"
          >
            Sign out
          </button>
        </div>
      </aside>
    </>
  );
}
