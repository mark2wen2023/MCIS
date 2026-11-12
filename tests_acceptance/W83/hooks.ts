export type Instance={slots:any[];cursor:number;pending:(()=>void)[];clean:(()=>void)[]}
let active:Instance
export const instance=():Instance=>({slots:[],cursor:0,pending:[],clean:[]})
export function render(i:Instance,fn:()=>any){active=i;i.cursor=0;const out=fn();for(const e of i.pending.splice(0))e();return out}
export function unmount(i:Instance){for(const e of i.clean)e();i.clean=[]}
export function useState(initial:any){const i=active,n=i.cursor++;if(!(n in i.slots))i.slots[n]=initial;return [i.slots[n],(v:any)=>{i.slots[n]=typeof v==='function'?v(i.slots[n]):v}]}
export function useRef(initial:any){const i=active,n=i.cursor++;if(!(n in i.slots))i.slots[n]={current:initial};return i.slots[n]}
export function useEffect(fn:()=>any,deps:any[]){const i=active,n=i.cursor++;if(!(n in i.slots)){i.slots[n]=deps;i.pending.push(()=>{const clean=fn();if(clean)i.clean.push(clean)})}}
export const jsx=(type:any,props:any,key:any)=>({type,props:props||{},key});export const jsxs=jsx;export const Fragment='fragment'
