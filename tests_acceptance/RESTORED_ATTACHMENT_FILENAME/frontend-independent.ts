import assert from 'node:assert/strict'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null}})
async function main(){
 const {historicalFileName,downloadHistory}=await import('../../web/src/evidenceIntake/history')
 const {caseIdentity}=await import('../../web/src/cases/identity')
 const prefix=`attachment; filename="historical-source.bin"; filename*=UTF-8''`
 let checks=0
 for(const name of ['foo%2Fbar.pdf','附件😀 “原稿”.zip','a+b.pdf']){
  assert.equal(historicalFileName(prefix+encodeURIComponent(name),'EV'),name);checks++
 }
 for(const header of [prefix+'%00.pdf',prefix+'%7F.pdf',prefix+'%5c.pdf',prefix+'%3A.pdf',prefix+'%C0%AF.pdf',prefix+'%F4%90%80%80.pdf',prefix+'x; filename=x',prefix+'x\r\nX: y',prefix+'x'.repeat(1600)]){
  assert.throws(()=>historicalFileName(header,'EV'));checks++
 }
 assert.equal(historicalFileName('attachment; filename="legacy.pdf"','../../EV'),'historical-______EV.bin');checks++
 const bytes=new TextEncoder().encode('synthetic fixture')
 const hash=Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex')
 const controller=new AbortController()
 globalThis.fetch=async()=>{
  controller.abort()
  return new Response(bytes,{headers:{'Content-Disposition':prefix+'safe.pdf','Cache-Control':'no-store','X-Sha256':hash}})
 }
 await assert.rejects(downloadHistory('SYNTHETIC','EV',caseIdentity(),controller.signal),{name:'AbortError'});checks++
 console.log(`${checks} independent frontend assertions passed; synthetic fetch, no browser`)
}
main().catch(e=>{console.error(e);process.exitCode=1})
