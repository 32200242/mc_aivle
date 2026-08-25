import type { HTMLAttributes } from "react";

export function Panel({ children, className = "", ...props }: HTMLAttributes<HTMLElement>) {
  return <section className={`panel ${className}`} {...props}>{children}</section>;
}

export function MetricCard({ label, value, note, tone = "pink" }: { label: string; value: string; note: string; tone?: string }) {
  return <div className={`metric-card ${tone}`}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}

export function Tag({ children, tone = "pink" }: { children: React.ReactNode; tone?: string }) {
  return <span className={`tag ${tone}`}>{children}</span>;
}
