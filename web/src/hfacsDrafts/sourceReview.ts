/** UI review lifecycle only; no evidence verification or authorization. */
export type SourceReviewState={refreshed:boolean;acknowledged:boolean}
export type SourceReviewAction={type:'refresh'}|{type:'loaded'}|{type:'acknowledge';checked:boolean}
export function sourceReviewInitial(status:'none'|'unchanged'|'changed'):SourceReviewState{
 const ready=status!=='changed'
 return {refreshed:ready,acknowledged:ready}
}
export function sourceReviewReducer(state:SourceReviewState,action:SourceReviewAction):SourceReviewState{
 switch(action.type){
  // Failure has no completion transition: the start state remains unavailable.
  case 'refresh':return {refreshed:false,acknowledged:false}
  case 'loaded':return {refreshed:true,acknowledged:false}
  case 'acknowledge':return {refreshed:state.refreshed,acknowledged:state.refreshed&&action.checked}
 }
}
