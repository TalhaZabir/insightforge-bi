"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { toast } from "sonner";
import { z } from "zod";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { FieldError, Input } from "@/components/ui/input";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

type Form = z.infer<typeof schema>;

const DEMO = [
  { email: "admin@insightforge.io", password: "Admin123!", role: "Administrator" },
  { email: "analyst@insightforge.io", password: "Analyst123!", role: "Analyst" },
  { email: "viewer@insightforge.io", password: "Viewer123!", role: "Viewer" },
];

export default function LoginPage() {
  const { user, ready, login } = useAuth();
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<Form>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (ready && user) router.replace("/overview");
  }, [ready, user, router]);

  const onSubmit = async (data: Form) => {
    setPending(true);
    try {
      await login(data.email, data.password);
      toast.success("Signed in");
      router.replace("/overview");
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : "Sign-in failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0A1628] px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-500 font-bold text-white">
            IF
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[#0A1628]">InsightForge BI</h1>
            <p className="text-xs text-slate-500">Sign in to your workspace</p>
          </div>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <div>
            <label className="text-xs font-medium text-slate-600" htmlFor="email">
              Email
            </label>
            <Input id="email" type="email" autoComplete="username" {...register("email")} />
            <FieldError message={errors.email?.message} />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600" htmlFor="password">
              Password
            </label>
            <Input id="password" type="password" autoComplete="current-password" {...register("password")} />
            <FieldError message={errors.password?.message} />
          </div>
          <Button type="submit" disabled={pending} className="w-full">
            {pending ? "Signing in…" : "Sign in"}
          </Button>
        </form>
        <div className="mt-6 border-t border-slate-200 pt-4">
          <p className="text-xs font-medium text-slate-500">Demo accounts</p>
          <div className="mt-2 space-y-1.5">
            {DEMO.map((d) => (
              <button
                key={d.email}
                onClick={() => {
                  setValue("email", d.email);
                  setValue("password", d.password);
                }}
                className="flex w-full items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-xs hover:bg-slate-100"
              >
                <span className="font-medium text-slate-700">{d.role}</span>
                <span className="font-mono text-slate-500">{d.email}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
