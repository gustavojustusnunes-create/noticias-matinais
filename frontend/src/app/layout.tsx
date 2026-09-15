import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "All News Journal | Jornalismo Autônomo & Inteligência Artificial",
  description:
    "Edições diárias matinais curadas e resumidas por agentes de IA, com podcast apresentado pelas vozes neurais Leo e Ana.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className="dark scroll-smooth">
      <body className="bg-[#0a0a0c] text-zinc-100 antialiased selection:bg-teal-400 selection:text-black min-h-screen flex flex-col">
        {children}
      </body>
    </html>
  );
}
