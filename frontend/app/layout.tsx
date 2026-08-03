import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "가족센터 AI 상담 통합 플랫폼",
  description: "가족센터 상담사 교육·상담 코파일럿·통합 관리",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko"><body>{children}</body></html>;
}
