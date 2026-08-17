import type { Metadata } from "next";
import "@/styles/simulation.module.css";

export const metadata: Metadata = {
  title: "信義商圈政策沙盒",
  description: "Simulation frontend shell"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-Hant">
      <body>{children}</body>
    </html>
  );
}
