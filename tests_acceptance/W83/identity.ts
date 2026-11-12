let role='Investigator',operator='独立验收';const listeners=new Set<()=>void>()
export const getRole=()=>role;export const getOperator=()=>operator
export const onIdentityChange=(f:()=>void)=>{listeners.add(f);return()=>listeners.delete(f)}
export const setIdentity=(r:string)=>{role=r;for(const f of listeners)f()}
export class ApiError extends Error {constructor(public status:number,public code:string,message:string,public detail:any){super(message)}}
