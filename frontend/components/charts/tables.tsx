import { fmtCurrency, fmtMargin, fmtNum } from "@/lib/format";
import { label } from "@/components/charts/charts";
import { Badge } from "@/components/ui/badge";

export function RankTable({
  rows,
  name,
  extra,
}: {
  rows: {
    revenue: number;
    profit: number;
    margin: number;
    orders: number;
    revenue_growth?: number | null;
    low_margin?: boolean;
    [k: string]: unknown;
  }[];
  name: (r: Record<string, unknown>) => string;
  extra?: (r: Record<string, unknown>) => React.ReactNode;
}) {
  if (rows.length === 0) return <p className="text-xs text-slate-500">No rows for current filters.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs">
        <thead>
          <tr className="text-left text-slate-500">
            <th className="py-1.5 pr-3 font-medium">#</th>
            <th className="py-1.5 pr-3 font-medium">Name</th>
            <th className="py-1.5 pr-3 text-right font-medium">Revenue</th>
            <th className="py-1.5 pr-3 text-right font-medium">Profit</th>
            <th className="py-1.5 pr-3 text-right font-medium">Margin</th>
            <th className="py-1.5 pr-3 text-right font-medium">Orders</th>
            <th className="py-1.5 text-right font-medium">Growth</th>
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 12).map((r, i) => (
            <tr key={i} className="border-t border-slate-100">
              <td className="py-1.5 pr-3 text-slate-400">{i + 1}</td>
              <td className="max-w-[200px] truncate py-1.5 pr-3 font-medium text-slate-800">
                {label(name(r as Record<string, unknown>))}
                {r.low_margin && (
                  <Badge tone="red" className="ml-1.5">
                    low margin
                  </Badge>
                )}
              </td>
              <td className="py-1.5 pr-3 text-right">{fmtCurrency(r.revenue)}</td>
              <td className="py-1.5 pr-3 text-right">{fmtCurrency(r.profit)}</td>
              <td className="py-1.5 pr-3 text-right">{fmtMargin(r.margin)}</td>
              <td className="py-1.5 pr-3 text-right">{fmtNum(r.orders)}</td>
              <td className="py-1.5 text-right">
                {r.revenue_growth === null || r.revenue_growth === undefined
                  ? "—"
                  : `${r.revenue_growth >= 0 ? "+" : ""}${r.revenue_growth.toFixed(1)}%`}
              </td>
              {extra && <td>{extra(r as Record<string, unknown>)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
