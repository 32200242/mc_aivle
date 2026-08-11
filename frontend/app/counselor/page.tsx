"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import AppShell from "@/components/AppShell";
import { Panel, Tag } from "@/components/UI";
import { listClients } from "@/lib/api";
import type { ClientSummary } from "@/lib/types";

export default function CounselorHome() {
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [today, setToday] = useState<Date | null>(null);
  const [selectedDateKey, setSelectedDateKey] = useState("");
  const [calendarMonth, setCalendarMonth] = useState<Date | null>(null);
  useEffect(() => {
    const currentDate = startOfDay(new Date());
    setToday(currentDate);
    setSelectedDateKey(toDateKey(currentDate));
    setCalendarMonth(new Date(currentDate.getFullYear(), currentDate.getMonth(), 1));
    listClients().then(setClients).catch(() => undefined).finally(() => setLoading(false));
  }, []);
  const appointments = useMemo(() => clients
    .map(client => ({ client, date: parseAppointment(client.next_session_at) }))
    .filter((item): item is { client: ClientSummary; date: Date } => Boolean(item.date))
    .sort((a, b) => a.date.getTime() - b.date.getTime()), [clients]);
  const todayKey = today ? toDateKey(today) : "";
  const todayAppointments = useMemo(() => appointments.filter(item => toDateKey(item.date) === todayKey), [appointments, todayKey]);
  const selectedAppointments = useMemo(() => appointments.filter(item => toDateKey(item.date) === selectedDateKey), [appointments, selectedDateKey]);
  const appointmentCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of appointments) counts.set(toDateKey(item.date), (counts.get(toDateKey(item.date)) ?? 0) + 1);
    return counts;
  }, [appointments]);
  const calendarDays = useMemo(() => calendarMonth ? buildCalendarDays(calendarMonth) : [], [calendarMonth]);
  const selectedDate = selectedDateKey ? fromDateKey(selectedDateKey) : today;
  const firstTodayAppointment = todayAppointments[0];

  function moveMonth(offset: number) {
    if (!calendarMonth) return;
    const nextMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + offset, 1);
    setCalendarMonth(nextMonth);
    setSelectedDateKey(toDateKey(nextMonth));
  }

  function selectToday() {
    if (!today) return;
    setCalendarMonth(new Date(today.getFullYear(), today.getMonth(), 1));
    setSelectedDateKey(todayKey);
  }

  return <AppShell title="안녕하세요, 김지현 상담사님" subtitle="오늘도 따뜻한 상담으로 내담자의 변화를 함께 만들어가요.">
    <div className="counselor-home-grid">
      <div>
        <div className="welcome-banner"><div><b>오늘의 상담 일정</b><strong>{loading || !today ? "-" : `${todayAppointments.length}건`}</strong><span>{loading || !today ? "일정을 불러오는 중입니다." : firstTodayAppointment ? `첫 상담은 ${formatAppointmentTime(firstTodayAppointment.date)} · ${firstTodayAppointment.client.name}` : "오늘 예정된 상담이 없습니다."}</span></div><div className="house-art" aria-hidden="true">◷</div></div>
        <Panel><div className="panel-heading"><h2>내담자 목록</h2><Link href="/counselor/clients">전체 내담자 보기 →</Link></div><div className="search-box">⌕ 이름, 연락처로 검색</div><div className="client-cards">{clients.map(client => <Link href={`/counselor/clients/${client.id}`} key={client.id} className="client-card"><span className="client-icon">♟♟</span><div><b>{client.name}</b><small>{client.primary_issue}</small></div><Tag tone={client.status.includes("준비") || client.status === "상담 시작 전" ? "pink" : "green"}>{client.status}</Tag><strong>{client.session_count}회기</strong></Link>)}</div></Panel>
        <Link href="/training" className="training-banner"><span>◇</span><div><b>페르소나 교육</b><small>가상 내담자와 다양한 상담 상황을 연습하고 역량을 향상시켜 보세요.</small></div><strong>교육 시작하기 →</strong></Link>
      </div>
      <Panel className="schedule-panel">
        <div className="panel-heading"><div><h2>일정 관리</h2><span>날짜를 눌러 상담 일정을 확인하세요.</span></div><button className="schedule-today-button" type="button" onClick={selectToday} disabled={!today}>오늘</button></div>
        <div className="schedule-calendar" aria-label="상담 일정 달력">
          <div className="schedule-calendar-header"><button type="button" onClick={() => moveMonth(-1)} aria-label="이전 달">‹</button><b>{calendarMonth ? formatAppointmentMonth(calendarMonth) : "불러오는 중"}</b><button type="button" onClick={() => moveMonth(1)} aria-label="다음 달">›</button></div>
          <div className="schedule-weekdays" aria-hidden="true">{["일", "월", "화", "수", "목", "금", "토"].map(day => <span key={day}>{day}</span>)}</div>
          <div className="schedule-calendar-days">{calendarDays.map((date, index) => date ? <button
            type="button"
            className={`schedule-calendar-day ${toDateKey(date) === selectedDateKey ? "selected" : ""} ${toDateKey(date) === todayKey ? "today" : ""} ${appointmentCounts.has(toDateKey(date)) ? "has-appointments" : ""}`}
            data-date={toDateKey(date)}
            aria-pressed={toDateKey(date) === selectedDateKey}
            aria-label={`${formatCalendarDateLabel(date)}${appointmentCounts.has(toDateKey(date)) ? `, 상담 ${appointmentCounts.get(toDateKey(date))}건` : ", 상담 없음"}`}
            onClick={() => setSelectedDateKey(toDateKey(date))}
            key={toDateKey(date)}
          ><span>{date.getDate()}</span>{appointmentCounts.has(toDateKey(date)) && <i aria-hidden="true"/>}</button> : <span className="schedule-calendar-blank" key={`blank-${index}`}/>)}</div>
        </div>
        <div className="selected-schedule-heading"><h3>{selectedDate ? formatFullAppointmentDate(selectedDate) : "오늘"}</h3><span>{loading ? "-" : `${selectedAppointments.length}건`}</span></div>
        {loading ? <p className="schedule-empty">상담 일정을 불러오는 중입니다.</p> : selectedAppointments.length === 0 ? <p className="schedule-empty">선택한 날짜에 예정된 상담이 없습니다.</p> : <div className="schedule-list">{selectedAppointments.map(({ client, date }) => <Link className="appointment" href={`/counselor/clients/${client.id}`} key={`${client.id}-${date.toISOString()}`} aria-label={`${client.name} 상담 일정 상세 보기`}>
          <time dateTime={client.next_session_at ?? undefined}><small>{formatAppointmentDate(date)}</small><b>{formatAppointmentTime(date)}</b></time>
          <span><strong>{client.name}</strong><small>{client.primary_issue}</small></span>
          <Tag tone="gray">예정</Tag>
        </Link>)}</div>}
        <Link className="schedule-more-link" href="/counselor/clients">전체 내담자 보기 →</Link>
      </Panel>
    </div>
  </AppShell>;
}


function parseAppointment(value?: string | null): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}


function formatAppointmentMonth(value: Date): string {
  return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "long" }).format(value);
}


function formatAppointmentDate(value: Date): string {
  return new Intl.DateTimeFormat("ko-KR", { month: "2-digit", day: "2-digit", weekday: "short" }).format(value);
}


function formatAppointmentTime(value: Date): string {
  return new Intl.DateTimeFormat("ko-KR", { hour: "2-digit", minute: "2-digit", hour12: false }).format(value);
}


function formatFullAppointmentDate(value: Date): string {
  return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", weekday: "short" }).format(value);
}


function formatCalendarDateLabel(value: Date): string {
  return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "long", day: "numeric", weekday: "long" }).format(value);
}


function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}


function toDateKey(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}


function fromDateKey(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}


function buildCalendarDays(month: Date): Array<Date | null> {
  const year = month.getFullYear();
  const monthIndex = month.getMonth();
  const firstWeekday = new Date(year, monthIndex, 1).getDay();
  const dayCount = new Date(year, monthIndex + 1, 0).getDate();
  const cells: Array<Date | null> = Array.from({ length: firstWeekday }, () => null);
  for (let day = 1; day <= dayCount; day += 1) cells.push(new Date(year, monthIndex, day));
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}
