import type { Metadata } from "next";
import { Toaster } from "sonner";
import { AuthProvider } from "@/lib/auth";
import { RQProvider } from "@/lib/query";
import "./globals.css";

export const metadata: Metadata = {
  title: "InsightForge BI",
  description: "End-to-end retail analytics platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <RQProvider>
          <AuthProvider>
            {children}
            <Toaster richColors position="top-right" />
          </AuthProvider>
        </RQProvider>
      </body>
    </html>
  );
}
