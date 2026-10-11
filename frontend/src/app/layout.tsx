import "@fontsource-variable/jetbrains-mono";
import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "FSP Talent",
  description: "Платформа подбора ИТ-специалистов по подтверждённым навыкам ФСП"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ru"><body>{children}</body></html>;
}
