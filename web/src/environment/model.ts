export const fields = [
  ['windSpeedMps','风速（m/s）'], ['windFromDirDeg','风的来向（° 真北）'],
  ['currentSpeedKn','流速（kn）'], ['currentToDirDeg','水流去向（° 真北）'], ['visibilityNm','能见度（nm）'],
] as const
export type Field = typeof fields[number][0]
export const origins = {Direct:'直接',Derived:'推算',Estimated:'估计'} as const
export type Origin = keyof typeof origins
export type Observation = {
  observationId:string;caseId:string;observedAtUtc:string|null;locationDescription:string|null;
  description:string;sourceLabel:string;valueOrigin:Origin;
} & Partial<Record<Field,number|null>>
export type ObservationForm = {
  observationId:string;observedAtUtc:string;locationDescription:string;description:string;sourceLabel:string;
  valueOrigin:Origin;values:Record<Field,string>;
}
export function emptyForm():ObservationForm {
  return {observationId:'',observedAtUtc:'',locationDescription:'',description:'',sourceLabel:'',valueOrigin:'Direct',values:Object.fromEntries(fields.map(([k])=>[k,''])) as Record<Field,string>}
}
export const canCreate = (role:string) => ['LeadInvestigator','Investigator'].includes(role)
export function validUtc(value:string):boolean {
  if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(value)||value.startsWith('0000'))return false
  const ms=Date.parse(value)
  return Number.isFinite(ms)&&new Date(ms).toISOString()===value.replace('Z','.000Z')
}
function text(value:unknown,label:string,max:number):string {
  if(typeof value!=='string'||!value.trim()||value.length>max)throw Error(`${label}须为 1–${max} 字的非空文字。`)
  return value
}
export function parseObservations(value:unknown,caseId:string):Observation[] {
  if(!Array.isArray(value))throw Error('环境记录列表格式无效。')
  const ids=new Set<string>(),allowed=new Set(['observationId','caseId','observedAtUtc','locationDescription','description','sourceLabel','valueOrigin',...fields.map(([k])=>k)])
  return value.map(raw=>{
    if(!raw||typeof raw!=='object'||Array.isArray(raw)||Object.keys(raw).some(k=>!allowed.has(k)))throw Error('环境记录格式无效。')
    const r=raw as Record<string,unknown>
    if(r.caseId!==caseId||typeof r.observationId!=='string'||!/^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$/.test(r.observationId)||ids.has(r.observationId))throw Error('环境记录案件或编号无效。')
    if(r.observedAtUtc!==null&&(typeof r.observedAtUtc!=='string'||!validUtc(r.observedAtUtc)))throw Error('观测时间须为有效 UTC 秒精度时间，或未知。')
    if(r.locationDescription!==null)text(r.locationDescription,'地点说明',500)
    text(r.description,'原文与说明',4000);text(r.sourceLabel,'来源',1000)
    if(typeof r.valueOrigin!=='string'||!Object.hasOwn(origins,r.valueOrigin))throw Error('请选择来源口径。')
    for(const [k,label] of fields){const n=r[k];if(n!==undefined&&n!==null&&(typeof n!=='number'||!Number.isFinite(n)||n<0||(k.endsWith('Deg')&&n>360)))throw Error(label+'数值无效；方向范围为 0–360，其他数量不可为负。')}
    ids.add(r.observationId);return raw as Observation
  })
}
export function buildObservation(form:ObservationForm,caseId:string):Observation {
  // Preserve source text verbatim; only trim structured ID/time and numeric input.
  const result:Observation={caseId,observationId:form.observationId.trim(),observedAtUtc:form.observedAtUtc.trim()||null,
    locationDescription:form.locationDescription.trim()?form.locationDescription:null,description:form.description,sourceLabel:form.sourceLabel,valueOrigin:form.valueOrigin}
  for(const [key,label] of fields){const s=form.values[key].trim();if(!s)continue
    if(!/^[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(s))throw Error(label+'请填写数字；未知请留空。')
    result[key]=Number(s)
  }
  return parseObservations([result],caseId)[0]!
}
export function matchesObservation(value:unknown,expected:Observation):boolean {
  try{const actual=parseObservations([value],expected.caseId)[0]!;return Object.keys(expected).length===Object.keys(actual).length&&Object.entries(expected).every(([k,v])=>actual[k as keyof Observation]===v)}catch{return false}
}
export function quantity(value:number|null|undefined,unit:string):string {return value===null||value===undefined?'未知':`${value} ${unit}`}
