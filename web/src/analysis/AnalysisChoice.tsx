import type { ReactNode } from 'react'

/** Native activation; delegates to the page's existing selection callback. */
export function AnalysisChoice({value,selected,onSelect,children}:{value:string;selected:boolean;onSelect:(value:string)=>void;children:ReactNode}) {
  return <button type="button" className={selected?'an-choice on':'an-choice'} aria-pressed={selected} onClick={()=>onSelect(value)}>{children}</button>
}
