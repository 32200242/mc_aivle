"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getStoredUser, logout } from "@/lib/api";
import type { User } from "@/lib/types";

type Props = { children: React.ReactNode; title: string; subtitle?: string; referenceDate?: string };

const counselorMenu = [
  ["⌂", "메인", "/counselor"],
  ["♙", "내담자 관리", "/counselor/clients"],
  ["✦", "상담 코파일럿", "/counselor/copilot"],
  ["◇", "페르소나 교육", "/training"],
];
const adminMenu = [
  ["⌂", "통합 대시보드", "/admin/dashboard"],
  ["⌁", "분석 및 예측", "/admin/analytics"],
  ["▤", "보고서", "/admin/reports"],
];

export default function AppShell({ children, title, subtitle, referenceDate }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  useEffect(() => {
    const stored = getStoredUser();
    if (!stored) router.replace("/login");
    else setUser(stored);
  }, [router]);
  if (!user) return <div className="center-loading">사용자 정보를 확인하고 있습니다.</div>;
  const isAdmin = user.role === "central_admin";
  const menu = isAdmin ? adminMenu : counselorMenu;
  const displayDate = formatDisplayDate(referenceDate ?? todayInSeoul());
  const signOut = () => { logout(); router.replace("/login"); };
  const isActive = (href: string) => {
    if (href.includes("#")) return false;
    const path = href.split("#")[0];
    if (path === "/counselor") return pathname === path;
    return pathname === path || pathname.startsWith(`${path}/`);
  };
  return (
    <div className={`app-frame ${isAdmin ? "admin-frame" : "counselor-frame"}`}>
      <aside className={`sidebar ${isAdmin ? "admin-sidebar" : "counselor-sidebar"}`}>
        <Link className="brand" href={isAdmin ? "/admin/dashboard" : "/counselor"}>
          <img className="brand-logo" src={isAdmin ? "/brand/kihf-logo.png" : "/brand/family-center-logo.png"} alt={isAdmin ? "한국건강가정진흥원" : "가족센터"} />
          <span>{isAdmin ? <><b>한국건강가정진흥원</b><small>통합 성과관리 시스템</small></> : <><b>가족센터</b><small>상담지원 시스템</small></>}</span>
        </Link>
        <nav>
          {menu.map(([icon, label, href]) => (
            <Link key={href} href={href} className={isActive(href) ? "active" : ""}>
              <span>{icon}</span><b>{label}</b>
              {isAdmin && label === "분석 및 예측" && <small>종합 결과 및 예측</small>}
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <button className="sidebar-help">{isAdmin ? "♧ 알림 센터" : "◉ 도움말"}</button>
          {isAdmin && <button className="sidebar-settings">⚙ 설정</button>}
          {isAdmin && <button className="sidebar-logout" onClick={signOut}>⇥ 로그아웃</button>}
        </div>
      </aside>
      <main className="main-area">
        <header className={`topbar ${isAdmin ? "admin-topbar" : "counselor-topbar"}`}>
          {isAdmin
            ? <div className="admin-context"><span className="menu-mark">☰</span><span className="center-switch">가족센터 →</span></div>
            : <div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>}
          <div className="top-actions">
            <span className="period-pill">{isAdmin ? `기준일　▦　${displayDate}` : `4회기 · ${displayDate}`}</span>
            <div className="user-chip"><span className="avatar-dot">{user.name.slice(0, 1)}</span><span><b>{user.name}</b><small>{user.center_name}</small></span></div>
            {!isAdmin && <button className="ghost" onClick={signOut}>로그아웃</button>}
          </div>
        </header>
        <div className="page-content">
          {isAdmin && <div className="admin-page-heading"><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>}
          {children}
        </div>
      </main>
    </div>
  );
}

function todayInSeoul() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date());
  const value = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${value.year}-${value.month}-${value.day}`;
}

function formatDisplayDate(value: string) {
  return value.replaceAll("-", ".");
}
