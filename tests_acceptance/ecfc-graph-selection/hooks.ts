// Handwritten hook slots for actual Editor callbacks. Not React DOM/effects scheduling.
let slots:any[]=[],cursor=0
export function reset(){slots=[];cursor=0}
export function begin(){cursor=0}
export function useState(initial:any){const i=cursor++;if(!(i in slots))slots[i]=typeof initial==='function'?initial():initial;return [slots[i],(v:any)=>{slots[i]=typeof v==='function'?v(slots[i]):v}]}
export function useRef(initial:any){return useState(()=>({current:initial}))[0]}
export function useId(){return 'synthetic-id'}
export function useEffect(){} // no claim that effects have run
