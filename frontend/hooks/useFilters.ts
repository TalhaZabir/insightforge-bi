"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

export const FILTER_KEYS = [
  "from",
  "to",
  "region",
  "country",
  "category",
  "subcategory",
  "channel",
  "segment",
  "status",
] as const;

export type Filters = Record<(typeof FILTER_KEYS)[number], string>;

const EMPTY: Filters = {
  from: "",
  to: "",
  region: "",
  country: "",
  category: "",
  subcategory: "",
  channel: "",
  segment: "",
  status: "",
};

export function useFilters() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const filters: Filters = useMemo(() => {
    const f = { ...EMPTY };
    for (const k of FILTER_KEYS) f[k] = params.get(k) ?? "";
    return f;
  }, [params]);

  const set = useCallback(
    (patch: Partial<Filters>) => {
      const next = new URLSearchParams(params.toString());
      for (const [k, v] of Object.entries(patch)) {
        if (v) next.set(k, v as string);
        else next.delete(k);
      }
      router.replace(`${pathname}?${next.toString()}`, { scroll: false });
    },
    [params, pathname, router]
  );

  const reset = useCallback(() => {
    router.replace(pathname, { scroll: false });
  }, [pathname, router]);

  const activeCount = useMemo(
    () => FILTER_KEYS.filter((k) => filters[k]).length,
    [filters]
  );

  const queryString = useMemo(() => {
    const q = new URLSearchParams();
    for (const k of FILTER_KEYS) if (filters[k]) q.set(k, filters[k]);
    const s = q.toString();
    return s ? `?${s}` : "";
  }, [filters]);

  return { filters, set, reset, activeCount, queryString };
}
