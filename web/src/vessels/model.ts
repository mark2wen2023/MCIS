export const fields = [
  ['name','船名','text'], ['nameCn','中文船名','text'], ['mmsi','MMSI（9 位数字）','text'],
  ['imoNumber','IMO 编号','text'], ['callSign','呼号','text'], ['flagState','船旗国','text'],
  ['vesselTypeCode','船舶类型','text'], ['loaM','总长（m）','positive'], ['beamM','型宽（m）','positive'],
  ['draftForeM','首吃水（m）','nonnegative'], ['draftAftM','尾吃水（m）','nonnegative'],
  ['displacementTons','排水量（t）','positive'], ['loadingCondition','装载状态','text'],
] as const
export type Field = typeof fields[number][0]
export type Source = {sourceLabel:string;kind:'Direct'|'Derived'|'Estimated'}
export const kinds = {Direct:'直接',Derived:'推算',Estimated:'估计'} as const
export type VesselRecord = {caseId:string;vesselId:string;name:string;parameterSources?:Partial<Record<Field,Source>>;[key:string]:unknown}
export type VesselForm = {vesselId:string;values:Record<Field,string>;sources:Record<Field,Source>}
export function emptyVesselForm():VesselForm {
  return {vesselId:'',values:Object.fromEntries(fields.map(([key])=>[key,''])) as Record<Field,string>,sources:Object.fromEntries(fields.map(([key])=>[key,{sourceLabel:'',kind:'Direct'}])) as Record<Field,Source>}
}
export function canCreateVessel(role:string) {return ['LeadInvestigator','Investigator'].includes(role)}
export function buildVessel(form:VesselForm,caseId:string,fictional:boolean):VesselRecord {
  const vesselId=form.vesselId.trim()
  if(!vesselId)throw Error('请填写船舶编号。')
  const body:VesselRecord={caseId,vesselId,name:''}
  const sources:Partial<Record<Field,Source>>={}
  for(const [key,label,type] of fields) {
    const value=form.values[key].trim()
    if(!value){if(key==='name')throw Error('请填写船名。');continue}
    if(type!=='text') {
      const n=Number(value)
      if(!/^[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value)||!Number.isFinite(n)||(type==='positive'?n<=0:n<0))throw Error(label+'须为有效的'+(type==='positive'?'正数。':'非负数。'))
      body[key]=n
    } else body[key]=value
    if(key==='mmsi'&&!/^\d{9}$/.test(value))throw Error('MMSI 必须是 9 位数字。')
    const source=form.sources[key]
    if(!fictional&&!source.sourceLabel.trim())throw Error('请填写'+label+'的资料来源。')
    if(source.sourceLabel.trim())sources[key]={sourceLabel:source.sourceLabel.trim(),kind:source.kind}
  }
  if(Object.keys(sources).length)body.parameterSources=sources
  return body
}
export function parseVessels(value:unknown,caseId:string):VesselRecord[] {
  if(!Array.isArray(value))throw Error('船舶列表格式无效')
  const seen=new Set<string>()
  return value.map(v=>{
    if(!v||typeof v!=='object'||v.caseId!==caseId||typeof v.vesselId!=='string'||!v.vesselId||seen.has(v.vesselId)||typeof v.name!=='string')throw Error('船舶记录格式无效')
    for(const [key,,type] of fields)if(v[key]!==undefined&&(type==='text'?typeof v[key]!=='string':typeof v[key]!=='number'||!Number.isFinite(v[key])))throw Error('船舶参数格式无效')
    if(v.parameterSources!==undefined){
      if(!v.parameterSources||typeof v.parameterSources!=='object'||Array.isArray(v.parameterSources))throw Error('来源格式无效')
      for(const [key,s] of Object.entries(v.parameterSources)){
        const source=s as Source
        if(!fields.some(([k])=>k===key)||!source||typeof source.sourceLabel!=='string'||!Object.hasOwn(kinds,source.kind))throw Error('来源格式无效')
      }
    }
    seen.add(v.vesselId);return v as VesselRecord
  })
}
export function matchesVessel(value:unknown,expected:VesselRecord):boolean {
  try {
    const actual=parseVessels([value],expected.caseId)[0]!
    for(const key of ['caseId','vesselId',...fields.map(([k])=>k)])if(actual[key]!==expected[key])return false
    for(const [key] of fields){const a=actual.parameterSources?.[key],b=expected.parameterSources?.[key];if(a?.kind!==b?.kind||a?.sourceLabel!==b?.sourceLabel)return false}
    return true
  }catch{return false}
}
