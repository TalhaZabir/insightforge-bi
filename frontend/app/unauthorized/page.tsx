import Link from "next/link";

export default function Unauthorized() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4 text-center">
      <p className="text-4xl font-bold text-[#0A1628]">401</p>
      <p className="mt-2 text-sm font-semibold">Sign-in required</p>
      <p className="mt-1 text-xs text-slate-500">Please sign in to continue.</p>
      <Link href="/login" className="mt-4 rounded-lg bg-[#0F1F3A] px-4 py-2 text-sm text-white">
        Go to sign in
      </Link>
    </div>
  );
}
