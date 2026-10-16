import { describe, expect, it } from "vitest";
import { fmtCurrency, fmtGrowth, fmtMargin, fmtNum, fmtPct } from "@/lib/format";
import { cn } from "@/lib/cn";

describe("format utils", () => {
  it("formats currency with zero decimals by default", () => {
    expect(fmtCurrency(1234.5)).toBe("$1,235");
    expect(fmtCurrency(1234.567, 2)).toBe("$1,234.57");
  });

  it("renders em-dash for missing values", () => {
    expect(fmtCurrency(null)).toBe("—");
    expect(fmtCurrency(undefined)).toBe("—");
    expect(fmtNum(Number.NaN)).toBe("—");
    expect(fmtPct(undefined)).toBe("—");
  });

  it("formats margin fractions as percent", () => {
    expect(fmtMargin(0.375)).toBe("37.5%");
  });

  it("signs growth values", () => {
    expect(fmtGrowth(12.34)).toBe("+12.3%");
    expect(fmtGrowth(-3.21)).toBe("-3.2%");
    expect(fmtGrowth(null)).toBe("—");
  });
});

describe("cn", () => {
  it("merges tailwind classes, later wins", () => {
    expect(cn("px-2 py-1", "px-4")).toBe("py-1 px-4");
    expect(cn("a", false && "b", "c")).toBe("a c");
  });
});
