import { forwardRef } from "react";

import { cn } from "@/lib/cn";

export const Input = forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(function Input({ className, ...p }, ref) {
  return (
    <input
      ref={ref}
      className={cn(
        "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm",
        "placeholder:text-slate-400 focus:border-[#0F1F3A] focus:outline-none focus:ring-1 focus:ring-[#0F1F3A]",
        className
      )}
      {...p}
    />
  );
});

export function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return <p className="mt-1 text-xs text-red-600">{message}</p>;
}
