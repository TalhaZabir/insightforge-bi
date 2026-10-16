"use client";

import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { ApiError, uploadFile, type UploadResult } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export function Dropzone({
  onUploaded,
  disabled,
}: {
  onUploaded: (r: UploadResult) => void;
  disabled?: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = async (file: File) => {
    setBusy(true);
    setError(null);
    try {
      onUploaded(await uploadFile("/uploads", file));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files?.[0];
          if (f && !disabled && !busy) void send(f);
        }}
        onClick={() => !disabled && !busy && input.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
          drag ? "border-teal-500 bg-teal-50" : "border-slate-300 bg-white hover:border-slate-400"
        )}
        role="button"
        aria-label="Upload sales file"
      >
        <UploadCloud className="text-slate-400" size={32} />
        <p className="mt-2 text-sm font-medium text-slate-700">
          {busy ? "Uploading…" : "Drag & drop your sales file here"}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          CSV or XLSX · up to 25 MB · UTF-8 or Western encodings · multi-sheet workbooks supported
        </p>
        <div className="mt-3" onClick={(e) => e.stopPropagation()}>
          <Button size="sm" variant="secondary" disabled={disabled || busy} onClick={() => input.current?.click()}>
            Choose file
          </Button>
        </div>
        <input
          ref={input}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void send(f);
            e.target.value = "";
          }}
        />
      </div>
      {error && (
        <p className="mt-2 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
