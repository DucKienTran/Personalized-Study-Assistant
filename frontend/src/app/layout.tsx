  import type { Metadata } from "next";
  import { AuthProvider } from "../contexts/AuthContext";
  import "@/polyfills/promise";
  import "./globals.css";
  import { Inter, Lora } from "next/font/google";
  import { cn } from "@/lib/utils";

  const inter = Inter({
    subsets: ["latin", "vietnamese"],
    variable: "--font-sans",
    weight: ["300", "400", "500"],
    display: "swap",
  });

  const lora = Lora({
    subsets: ["latin", "vietnamese"],
    variable: "--font-heading",
    weight: ["400", "500", "600"],
    display: "swap",
  });

  export const metadata: Metadata = {
    title: "Application",
    description: "Web application dashboard",
  };

  export default function RootLayout({
    children,
  }: Readonly<{
    children: React.ReactNode;
  }>) {
    return (
      <html lang="en" className={cn(inter.variable, lora.variable, "font-sans")}>
        <head>
          <link
            rel="stylesheet"
            href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200"
          />
        </head>

        <body>
          <AuthProvider>{children}</AuthProvider>
        </body>
      </html>
    );
  }