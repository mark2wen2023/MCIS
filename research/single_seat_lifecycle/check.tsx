import React,{act} from 'react'
import {createRoot} from 'react-dom/client'
import assert from 'node:assert/strict'
import {SingleSeatCard} from '../single_seat_card/Card'
import fixed from '../single_seat_preview/result.json'
export async function run(){
 const container=document.createElement('div');document.body.append(container)
 const root=createRoot(container)
 const render=async(value:unknown)=>act(async()=>{root.render(<SingleSeatCard preview={value}/>)})
 const clone=()=>JSON.parse(JSON.stringify(fixed.preview))
 const original=JSON.stringify(fixed.preview);let phases=0
 const pointer=()=>Array.from(container.querySelectorAll('code')).find(e=>e.textContent?.includes('/sampling/missingIntervals/1'))!
 const checkValid=()=>{
  assert(pointer()?.isConnected)
  assert(container.textContent?.includes('证据不足以判断任一船舶是否转向'))
  assert(container.textContent?.includes('待人工审核'))
  assert(!container.querySelector('a,button,input,form'))
 }
 const checkRemoved=(old:Element,summary:HTMLElement)=>{
  assert(!old.isConnected&&!summary.isConnected)
  assert(!container.contains(old)&&!container.contains(summary))
  assert(!container.textContent?.includes('SYN-E-A'))
  assert(!container.textContent?.includes('/sampling/missingIntervals/1'))
  assert(container.querySelector('[role="alert"]'))
  ;(old as HTMLElement).focus();assert.notEqual(document.activeElement,old)
  summary.focus();assert.notEqual(document.activeElement,summary)
 }
 try{
  await render(clone());checkValid();phases++
  const old=pointer(),summary=container.querySelector('summary')!
  await render(null);checkRemoved(old,summary);phases++
  await render(clone());checkValid();assert.notEqual(pointer(),old);phases++
  const second=pointer(),secondSummary=container.querySelector('summary')!
  const changed=clone();changed.alignedUtc='2026-02-01T12:01:40.000Z'
  await render(changed);checkRemoved(second,secondSummary);phases++
  await render(clone());checkValid();assert.notEqual(pointer(),second);phases++
  const third=pointer(),thirdSummary=container.querySelector('summary')!
  await render(undefined);checkRemoved(third,thirdSummary);phases++
  await render(clone());checkValid();assert.notEqual(pointer(),third);phases++
  assert.equal(JSON.stringify(fixed.preview),original)
  console.log(JSON.stringify({result:'PASS',renderer:'ReactDOM client + happy-dom',roots:1,phases,
    clearedInputs:['null','unsupported changed time/version','undefined'],detachedPointerAndSummary:true,
    detachedFocusRejected:true,independentValidCopiesRestored:true,realRevocation:false,browser:false,model:false}))
 }finally{await act(async()=>root.unmount());container.remove()}
}
