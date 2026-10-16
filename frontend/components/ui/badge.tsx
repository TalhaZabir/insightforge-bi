import { cn } from "@/lib/cn";

export function Badge({
  tone = "slate",
  className,
  ...p
}: React.HTMLAttributes<HTMLSpanElement> & {
  tone?: "slate" | "green" | "red" | "amber" | "blue" | "teal";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        tone === "slate" && "bg-slate-100 text-slate-700",
        tone === "green" && "bg-emerald-50 text-emerald-700",
        tone === "red" && "bg-red-50 text-red-700",
        tone === "amber" && "bg-amber-50 text-amber-800",
        tone === "blue" && "bg-blue-50 text-blue-700",
        tone === "teal" && "bg-teal-50 text-teal-700",
        className
      )}
      {...p}
    />
  );
}
