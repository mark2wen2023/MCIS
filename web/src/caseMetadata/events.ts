/** Notification only: subscribers re-read the case, never trust event data as metadata. */
export const CASE_METADATA_CHANGED='mcis:case-metadata-changed'
export function notifyCaseMetadataChanged(caseId:string){window.dispatchEvent(new CustomEvent(CASE_METADATA_CHANGED,{detail:{caseId}}))}
export function onCaseMetadataChanged(caseId:string,refresh:()=>void):()=>void{
 const receive=(event:Event)=>{const d=(event as CustomEvent<unknown>).detail;if(d&&typeof d==='object'&&'caseId' in d&&d.caseId===caseId)refresh()}
 window.addEventListener(CASE_METADATA_CHANGED,receive)
 return()=>window.removeEventListener(CASE_METADATA_CHANGED,receive)
}
