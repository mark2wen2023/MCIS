/** Display domain only. No timestamp rewriting, uncertainty inference or clock correction. */
export function timelineDomain(
  fictional: boolean,
  events: readonly { timeSec: number; endTimeSec?: number | null }[],
  cpa: readonly { timeSec: number }[],
  conflicts: readonly { timeSec?: number | null }[],
): { min: number; max: number } {
  let min = 0
  let max = fictional ? 780 : 60
  const include = (value: unknown) => {
    if (typeof value !== 'number' || !Number.isFinite(value)) return
    min = Math.min(min, value)
    max = Math.max(max, value)
  }
  for (const event of events) {
    include(event.timeSec)
    // Legacy reversed intervals are not repaired or turned into uncertainty ranges.
    if (Number.isFinite(event.timeSec) && typeof event.endTimeSec === 'number' && event.endTimeSec >= event.timeSec) include(event.endTimeSec)
  }
  for (const point of cpa) include(point.timeSec)
  for (const conflict of conflicts) include(conflict.timeSec)
  return { min, max }
}

/** The exact production x-axis option, shared with render regression tests. */
export function timelineAxis(domain: { min: number; max: number }, epoch: string, offsetMinutes: number) {
  const epochMs = Date.parse(epoch)
  const displayMs = (seconds: number) => epochMs + seconds * 1000 + offsetMinutes * 60000
  const invalid = !Number.isFinite(domain.max - domain.min) || domain.max <= domain.min ||
    !Number.isFinite(epochMs) || !Number.isFinite(offsetMinutes) ||
    [domain.min, domain.max].some(value => !Number.isFinite(value) || !Number.isFinite(new Date(displayMs(value)).getTime()))
  if (invalid) return { ok: false as const, message: '时间范围超出可视化支持范围，未绘制时间线；原始证据和时间未修改，请核查时间范围。' }
  return { ok: true as const, axis: {
    type: 'value' as const, min: domain.min, max: domain.max, splitNumber: 8,
    axisLabel: { color: '#8da4c4', fontSize: 10, formatter: (value: number) => {
      const date = new Date(displayMs(value))
      const pad = (n: number) => String(n).padStart(2, '0')
      const clock = `${pad(date.getUTCHours())}:${pad(date.getUTCMinutes())}`
      return domain.max - domain.min >= 86400 ? `${date.getUTCFullYear()}-${pad(date.getUTCMonth()+1)}-${pad(date.getUTCDate())} ${clock}` : clock
    } },
    axisLine: { lineStyle: { color: 'rgba(59,227,255,.3)' } },
    splitLine: { lineStyle: { color: 'rgba(141,164,196,.08)' } },
  } }
}
