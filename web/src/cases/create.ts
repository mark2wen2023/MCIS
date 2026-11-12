/** W8.2 writes the existing Case contract. No evidence or simulation data is invented. */
export type CaseForm = {
  caseId: string; title: string; accidentType: string; incidentTimeUtc: string
  lonDeg: string; latDeg: string; fictional: string; placeName: string
}
export const emptyCaseForm = (): CaseForm => ({caseId:'',title:'',accidentType:'',incidentTimeUtc:'',lonDeg:'',latDeg:'',fictional:'',placeName:''})
export const accidentTypes = [['Collision','碰撞'],['Grounding','搁浅'],['Contact','触碰'],['Foundering','沉没'],['Capsizing','倾覆'],['FireOrExplosion','火灾或爆炸'],['Other','其他']] as const
export interface NewCase {
  caseId: string; schemaVersion: '1.0.0'; title: string; accidentType: string
  incidentTimeUtc: string; caseEpochUtc: string; displayTimeZoneOffsetMinutes: 0
  incidentLocation: {lonDeg: number; latDeg: number}; isFictionalDemo: boolean; placeName?: string
}
export function canCreateCase(role: string): boolean { return role === 'Investigator' || role === 'LeadInvestigator' }
export function buildCase(form: CaseForm): NewCase {
  if (!/^[A-Za-z0-9._-]{3,}$/.test(form.caseId)) throw Error('案号须至少 3 个字符，仅限英文字母、数字、点、下划线和连字符。')
  if (!form.title.trim()) throw Error('请填写案件名称。')
  if (!accidentTypes.some(([value])=>value === form.accidentType)) throw Error('请选择事故类型。')
  // Strict UTC-only input, including round-trip validation to reject calendar rollover.
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z$/.test(form.incidentTimeUtc)) throw Error('事故时间须为 UTC，例如 2026-11-12T08:30:00Z。')
  const normalized = form.incidentTimeUtc.length === 17 ? form.incidentTimeUtc.slice(0,-1)+':00Z' : form.incidentTimeUtc
  const date = new Date(normalized)
  if (normalized.startsWith('0000-') || !Number.isFinite(date.getTime()) || date.toISOString() !== normalized.slice(0,-1)+'.000Z') throw Error('事故 UTC 时间无效，请检查日期和时分秒。')
  const number = (value: string, max: number, name: string) => {
    if (!value.trim() || !/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(value.trim()) || !Number.isFinite(Number(value)) || Math.abs(Number(value)) > max) throw Error(`${name}须为 -${max} 到 ${max} 之间的有限数值。`)
    return Number(value)
  }
  const lonDeg = number(form.lonDeg,180,'经度'), latDeg = number(form.latDeg,90,'纬度')
  if (form.fictional !== 'true' && form.fictional !== 'false') throw Error('请选择虚构演示或非虚构案件。')
  return {caseId:form.caseId,schemaVersion:'1.0.0',title:form.title,accidentType:form.accidentType,incidentTimeUtc:normalized,caseEpochUtc:normalized,displayTimeZoneOffsetMinutes:0,incidentLocation:{lonDeg,latDeg},isFictionalDemo:form.fictional==='true',...(form.placeName.trim()?{placeName:form.placeName}:{})}
}
/** Server may add fields, but every submitted field must be present and identical. */
export function matchesCreatedCase(actual: unknown, expected: NewCase): boolean {
  function match(a: unknown, e: unknown): boolean {
    if (e !== null && typeof e === 'object') {
      if (a === null || typeof a !== 'object' || Array.isArray(a)) return false
      return Object.entries(e).every(([key,value])=>Object.hasOwn(a,key) && match((a as Record<string,unknown>)[key],value))
    }
    return a === e
  }
  return match(actual,expected)
}
