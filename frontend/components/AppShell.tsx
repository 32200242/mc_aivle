"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getStoredUser, logout } from "@/lib/api";
import type { User } from "@/lib/types";

type Props = { children: React.ReactNode; title: string; subtitle?: string };

const counselorMenu = [
  ["⌂", "메인", "/counselor"],
  ["♙", "내담자 관리", "/counselor/clients"],
  ["✦", "상담 코파일럿", "/counselor/copilot"],
  ["◇", "페르소나 교육", "/training"],
];
const adminMenu = [
  ["⌂", "통합 대시보드", "/admin/dashboard"],
  ["⌁", "분석 및 예측", "/admin/analytics"],
  ["▤", "보고서", "/admin/dashboard#reports"],
];

export default function AppShell({ children, title, subtitle }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    const stored = getStoredUser();
    if (!stored) router.replace("/login");
    else setUser(stored);
  }, [router]);
  if (!user) return <div className="center-loading">사용자 정보를 확인하고 있습니다.</div>;
  const menu = user.role.includes("admin") ? adminMenu : counselorMenu;
  return (
    <div className="app-frame">
      <aside className="sidebar">
        <Link className="brand" href={user.role.includes("admin") ? "/admin/dashboard" : "/counselor"}>
          <img className="brand-logo" src="/brand/family-center-logo.png" alt="가족센터" />
          <span><b>가족센터</b><small>상담지원 시스템</small></span>
        </Link>
        <nav>
          {menu.map(([icon, label, href]) => (
            <Link key={href} href={href} className={pathname === href ? "active" : ""}>
              <span>{icon}</span>{label}
            </Link>
          ))}
        </nav>
        <button className="sidebar-help">◉ 도움말</button>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
          <div className="top-actions">
            <span className="period-pill">4회기 · 2026.08.02</span>
            <span className="bell">♢<i>2</i></span>
            <div className="user-chip"><span className="avatar-dot">{user.name.slice(0, 1)}</span><span><b>{user.name}</b><small>{user.center_name}</small></span></div>
            <button className="ghost" onClick={() => { logout(); router.replace("/login"); }}>로그아웃</button>
          </div>
        </header>
        <div className="page-content">{children}</div>
      </main>
    </div>
  );
}
