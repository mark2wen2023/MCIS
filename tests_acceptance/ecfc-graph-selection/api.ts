export let response:any
export const setResponse=(value:any)=>{response=value}
export async function request(...args:any[]){return structuredClone(typeof response==='function'?response(...args):response)}
export const errorText=()=> '合成错误'
