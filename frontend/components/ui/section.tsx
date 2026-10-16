import { Card, CardHint, CardTitle } from "@/components/ui/card";

export function SectionPage({ title, hint }: { title: string; hint: string }) {
  return (
    <Card className="p-6">
      <CardTitle>{title}</CardTitle>
      <CardHint>{hint}</CardHint>
      <p className="mt-4 text-sm text-slate-500">
        This section is under construction in Part 8 — charts and tables land next.
      </p>
    </Card>
  );
}
