// Evidence-only display helpers. Stored UTC and shared page formatting remain untouched.

export function toLocal(utc: string | null | undefined, withDate: boolean, offsetMinutes: number): string {
  if (!utc) return '—'
  const d = new Date(new Date(utc).getTime() + offsetMinutes * 60000)
  const p = (n: number) => String(n).padStart(2, '0')
  const t = `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}`
  return withDate ? `${p(d.getUTCMonth() + 1)}-${p(d.getUTCDate())} ${t}` : t
}

export function simToClock(epochUtc: string, sec: number, seconds: boolean, offsetMinutes: number): string {
  const d = new Date(new Date(epochUtc).getTime() + sec * 1000 + offsetMinutes * 60000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getUTCHours())}:${p(d.getUTCMinutes())}` + (seconds ? `:${p(d.getUTCSeconds())}` : '')
}

/** A display label only; never changes stored UTC timestamps. */
export function timeZoneLabel(offsetMinutes: number): string {
  if (!Number.isFinite(offsetMinutes) || !Number.isInteger(offsetMinutes)) return '时区未确认'
  if (offsetMinutes === 0) return 'UTC'
  const absolute = Math.abs(offsetMinutes)
  return `UTC${offsetMinutes > 0 ? '+' : '-'}${String(Math.floor(absolute / 60)).padStart(2,'0')}:${String(absolute % 60).padStart(2,'0')}`
}

export function distanceTooltip(epochUtc: string, timeSec: number, distanceNm: number, offsetMinutes: number): string {
  return `${simToClock(epochUtc, timeSec, true, offsetMinutes)} 距离 ${distanceNm.toFixed(2)} nm`
}
