"use client";

import { useState } from "react";
import { Menu } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Sidebar } from "./sidebar";
import { FilterBar } from "./filterbar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const { user } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar open={open} onClose={() => setOpen(false)} />
      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
          <div className="flex items-center gap-3 px-4 py-3 sm:px-6">
            <button
              className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 lg:hidden"
              onClick={() => setOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-[#0A1628]">
                {user ? `${user.role[0].toUpperCase()}${user.role.slice(1)} workspace` : "InsightForge BI"}
              </p>
              <p className="hidden text-xs text-slate-500 sm:block">
                Filters apply across KPIs, charts and tables
              </p>
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-7xl space-y-4 px-4 py-6 sm:px-6">
          <FilterBar />
          {children}
        </main>
      </div>
    </div>
  );
}
