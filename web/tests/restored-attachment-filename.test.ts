import assert from 'node:assert/strict'
Object.defineProperty(globalThis,'localStorage',{value:{getItem:()=>null}})
async function main(){
 const {historicalFileName,downloadHistory}=await import('../src/evidenceIntake/history')
 const {caseIdentity}=await import('../src/cases/identity')
 const prefix=`attachment; filename="historical-source.bin"; filename*=UTF-8''`
 const encoded=(name:string)=>encodeURIComponent(name).replace(/[!'()*]/g,c=>'%'+c.charCodeAt(0).toString(16).toUpperCase())
 let n=0
 for(const name of ['😀'.repeat(123)+'.docx','report.pdf','报告 “副本” 😀.docx','report";evil=.pdf',"quote'%file.zip"]){assert.equal(historicalFileName(prefix+encoded(name),'EV-001'),name);n++}
 assert.equal(historicalFileName('attachment; filename="historical-source.bin"','EV-001'),'historical-EV-001.bin');n++
 for(const value of ['../a.pdf','a/b.pdf','a\\b.pdf','a:b.pdf','a\r\nX-Hack:yes.pdf','', ' ', 'a'.repeat(129)]){assert.throws(()=>historicalFileName(prefix+encoded(value),'EV-001'));n++}
 for(const value of [prefix+'%FF',prefix+'%QZ',prefix+'%ED%A0%80',prefix+'x.pdf; filename*=UTF-8\'\'other.pdf',prefix+'x.pdf; extra=1']){assert.throws(()=>historicalFileName(value,'EV-001'));n++}
 const bytes=new TextEncoder().encode('synthetic opaque attachment')
 const sha=Buffer.from(await crypto.subtle.digest('SHA-256',bytes)).toString('hex')
 let headers:Record<string,string>={'Content-Disposition':prefix+encoded('报告.pdf'),'Cache-Control':'no-store','X-Sha256':sha}
 globalThis.fetch=async()=>new Response(bytes,{headers})
 const result=await downloadHistory('SYNTHETIC','EV-001',caseIdentity(),new AbortController().signal)
 assert.equal(result.fileName,'报告.pdf');assert.deepEqual(new Uint8Array(result.bytes),bytes);n++
 headers={...headers,'X-Sha256':'0'.repeat(64)}
 await assert.rejects(downloadHistory('SYNTHETIC','EV-001',caseIdentity(),new AbortController().signal));n++
 headers={...headers,'X-Sha256':sha,'Content-Disposition':prefix+'%2Fbad.pdf'}
 await assert.rejects(downloadHistory('SYNTHETIC','EV-001',caseIdentity(),new AbortController().signal));n++
 headers={...headers,'Content-Disposition':prefix+'a.pdf','Cache-Control':'public'}
 await assert.rejects(downloadHistory('SYNTHETIC','EV-001',caseIdentity(),new AbortController().signal));n++
 console.log(`${n} restored attachment filename checks passed (synthetic fetch)`)
}
main().catch(e=>{console.error(e);process.exitCode=1})
