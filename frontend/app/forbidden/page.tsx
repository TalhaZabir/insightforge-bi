import Link from "next/link";

export default function Forbidden() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 text-center">
      <p className="text-4xl font-bold text-[#0A1628]">403</p>
      <p className="mt-2 text-sm font-semibold">Forbidden</p>
      <p className="mt-1 text-xs text-slate-500">Your role cannot access this section.</p>
      <Link href="/overview" className="mt-4 rounded-lg bg-[#0F1F3A] px-4 py-2 text-sm text-white">
        Back to overview
      </Link>
    </div>
  );
}
