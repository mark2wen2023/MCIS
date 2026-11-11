// 时间显示：一律按案件显示时区（北京时间 UTC+8）。
export const TZ_MIN = 480

export function toLocal(utc: string | null | undefined, withDate = true): string {
  if (!utc) return '—'
  const d = new Date(new Date(utc).getTime() + TZ_MIN * 60000)
  const p = (n: number) => String(n).padStart(2, '0')
  const t = `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`
  return withDate ? `${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${t}` : t
}

export function simToClock(epochUtc: string, sec: number, seconds = true): string {
  const d = new Date(new Date(epochUtc).getTime() + sec * 1000 + TZ_MIN * 60000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}` + (seconds ? `:${p(d.getUTCSeconds())}` : '')
}

export const shortHash = (h: string) => (h ? `${h.slice(0, 6)}…${h.slice(-4)}` : '—')

export function daysUntil(utc: string): number {
  return Math.ceil((new Date(utc).getTime() - Date.now()) / 86400000)
}
