import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Quotex AI Analyzer",
  description: "Análise técnica e estatística — somente leitura, sem execução automática de operações.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body className="bg-ink text-paper antialiased font-body">{children}</body>
    </html>
  );
}
