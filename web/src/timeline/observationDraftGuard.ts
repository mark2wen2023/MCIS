// Page-memory predicates only: no text, identifiers, browser storage or network.
const drafts=new Set<()=>boolean>()
export const LEAVE_OBSERVATION_MESSAGE='观察文字尚未确认保存，离开后本页草稿会丢失。请求可能仍在处理，离开不会撤销提交；是否仍要离开？'
export function registerObservationDraft(pending:()=>boolean){drafts.add(pending);return()=>{drafts.delete(pending)}}
export function hasObservationDraft(){return [...drafts].some(pending=>pending())}
export function guardObservationUnload(event:BeforeUnloadEvent){
  if(hasObservationDraft()){event.preventDefault();event.returnValue=''}
}
