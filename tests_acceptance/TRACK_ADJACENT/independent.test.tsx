import assert from 'node:assert/strict'
import React,{act} from 'react'
import {TrackView} from '../../web/src/tracks/TrackView'
import {parseSnapshot} from '../../web/src/tracks/model'
async function main(){
 const {Window}=await import(process.env.MCIS_HAPPY_DOM!)
 const window=new Window()
 for(const k of ['window','document','HTMLElement','Element','Event','MouseEvent'])Object.defineProperty(globalThis,k,{value:k==='window'?window:window[k],configurable:true,writable:true})
 ;(globalThis as any).IS_REACT_ACT_ENVIRONMENT=true
 const {createRoot}=await import('react-dom/client')
 const raw=Array.from({length:205},(_,i)=>({vesselId:'V',timeSec:i*5,utc:new Date(Date.UTC(2026,0,1)+i*5000).toISOString(),latDeg:30,lonDeg:120,sogKn:1,cogDeg:0,provenance:i%2?'Interpolated':'Measured',source:i===201?'<script>PREVIOUS</script>':'source-'+i}))
 const snapshot=parseSnapshot('C',{caseId:'C',title:'Synthetic',isFictionalDemo:true,caseEpochUtc:'2026-01-01T00:00:00Z'},[{caseId:'C',vesselId:'V',name:'v'}],{caseId:'C',tracks:[{vesselId:'V',points:raw}]})
 const original=JSON.stringify(snapshot);const root=createRoot(document.body.appendChild(document.createElement('div')))
 await act(async()=>root.render(<TrackView snapshot={snapshot}/>))
 const detail=()=>document.querySelector('[aria-label="选中点详情"]')
 const button=(text:string)=>[...document.querySelectorAll('button')].find(b=>b.textContent===text)!
 const filter=document.querySelector('select[value="all"]')||[...document.querySelectorAll('select')].find(s=>[...s.options].some(o=>o.value==='Measured'))!
 await act(async()=>{(filter as HTMLSelectElement).value='Measured';filter.dispatchEvent(new window.Event('change',{bubbles:true}))})
 await act(async()=>button('下一页').click())
 const target=document.querySelector('[aria-label="查看筛选结果第 102 点"]') as HTMLButtonElement
 assert(target);await act(async()=>target.click())
 assert(detail()!.textContent!.includes('原始返回序号：第 203 点'));assert(detail()!.textContent!.includes('筛选结果序号：第 102 点'));assert(document.querySelector('th')!.textContent==='筛选结果序号')
 assert(detail()!.textContent!.includes('5 s'));assert(detail()!.textContent!.includes('00:16:45.000Z'))
 assert(detail()!.textContent!.includes('<script>PREVIOUS</script>'));assert.equal(detail()!.querySelector('script'),null)
 await act(async()=>{(filter as HTMLSelectElement).value='Interpolated';filter.dispatchEvent(new window.Event('change',{bubbles:true}))})
 assert.equal(detail(),null)
 const circle=document.querySelector('svg circle')!;await act(async()=>circle.dispatchEvent(new window.MouseEvent('click',{bubbles:true})))
 assert(detail()!.textContent!.includes('原始返回序号：第 2 点'));assert(detail()!.textContent!.includes('source-0'))
 assert.equal(JSON.stringify(snapshot),original)
 await act(async()=>root.unmount())
 console.log('PASS mounted HappyDOM: real provenance filter, pagination selection, unfiltered previous, escaped source, filter reset, plot selection, input immutability; not browser')
}
main().then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)})
