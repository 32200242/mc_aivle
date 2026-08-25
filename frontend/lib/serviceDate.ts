export function serviceDateInSeoul(now = new Date()): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(now);
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}


export function serviceDayAppointment(hour = 9, minute = 0): string {
  return `${serviceDateInSeoul()}T${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}:00+09:00`;
}


export function isServiceDateOrLater(value?: string | null): boolean {
  if (!value) return false;
  const appointment = new Date(value);
  if (Number.isNaN(appointment.getTime())) return false;
  const dateKey = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(appointment);
  return dateKey >= serviceDateInSeoul();
}


export function isServiceDate(value?: string | null): boolean {
  if (!value) return false;
  const appointment = new Date(value);
  if (Number.isNaN(appointment.getTime())) return false;
  const dateKey = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(appointment);
  return dateKey === serviceDateInSeoul();
}
