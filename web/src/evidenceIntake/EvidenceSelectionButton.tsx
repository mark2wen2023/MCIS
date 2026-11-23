/** Selection only: preserves the page's existing invalidation callback. */
export function EvidenceSelectionButton({evidenceId,title,selected,onSelect}:{evidenceId:string;title:string;selected:boolean;onSelect:(id:string)=>void}){
  return <button type="button" className="w42-evidence-select" aria-label={`查看证据 ${evidenceId}：${title}`} aria-pressed={selected}
    onClick={event=>{event.stopPropagation();onSelect(evidenceId)}}>{title}</button>
}
