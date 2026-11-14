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
