// Simulated DOM with a captured production request; replay against real service separately.
import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import { Window } from 'happy-dom'

async function main() {
  const win = new Window({url:'http://localhost/recommendations'})
  const {document} = win
  for (const key of ['window','document','navigator','localStorage','HTMLElement','HTMLInputElement','HTMLTextAreaElement','Event','MouseEvent','IS_REACT_ACT_ENVIRONMENT']) {
    Object.defineProperty(globalThis,key,{configurable:true,writable:true,value:key === 'window' ? win : key === 'IS_REACT_ACT_ENVIRONMENT' ? true : (win as any)[key]})
  }
  win.localStorage.setItem('mcis.role','LeadInvestigator')
  const caseId='SYN-W7-CREATE-BODY'
  const calls: {method:string,path:string,data?:any}[]=[]
  globalThis.fetch = (async (path,init) => {
    const url=String(path), method=init?.method??'GET'
    const data=init?.body ? JSON.parse(String(init.body)) : undefined
    calls.push({method,path:url,data})
    let payload:unknown
    if (method==='POST') payload={id:'SR-2099-77',status:'Draft'}
    else if (method==='GET'&&url.endsWith('/recommendations:board')) payload={columns:[],allowed:{}}
    else if (method==='GET'&&url.endsWith('/'+caseId)) payload={isFictionalDemo:true}
    else if (method==='GET'&&(/\/audit\?|\/consultation\/rounds$/.test(url))) payload=[]
    else throw Error('unexpected request: '+method+' '+url)
    return new Response(JSON.stringify(payload),{status:method==='POST'?201:200,headers:{'Content-Type':'application/json'}})
  }) as typeof fetch
  const React=await import('react')
  const {createRoot}=await import('react-dom/client')
  const {MemoryRouter}=await import('react-router-dom')
  const {RecommendationsPage}=await import('../src/pages/RecommendationsPage')
  const root=createRoot(document.body as any)
  const button=(text:string)=>[...document.querySelectorAll<HTMLButtonElement>('button')].find(b=>b.textContent?.trim()===text)!
  const click=async(text:string)=>React.act(async()=>{button(text).click()})
  const fill=async(el:any,value:string)=>{
    const proto=el.tagName==='TEXTAREA'?win.HTMLTextAreaElement.prototype:win.HTMLInputElement.prototype
    await React.act(async()=>{
      Object.getOwnPropertyDescriptor(proto,'value')!.set!.call(el,value)
      el.dispatchEvent(new win.Event('input',{bubbles:true}))
    })
  }
  try {
    await React.act(async()=>root.render(<MemoryRouter initialEntries={['/recommendations?case='+caseId]}><RecommendationsPage/></MemoryRouter>))
    const typed='  第一段：整改建议，保留段落和空格。\n\n第二段：核验措施。  '
    for(const [n,body] of [typed,''].entries()) {
      await click('＋ 新建安全建议')
      const control=document.querySelector('textarea')!
      assert.ok(control?.closest('label')?.textContent?.includes('建议正文（可选）'))
      assert.equal(control.value,'')
      if(n===0) await fill(control,body)
      await fill(document.querySelector('input[placeholder="建议标题"]'), '合成建议 '+n)
      await fill(document.querySelector('input[placeholder="建议对象"]'), '合成对象')
      await fill(document.querySelector('input[type="date"]'), '2099-06-30')
      assert.equal(button('保存').disabled,false)
      await click('保存')
      assert.equal(document.querySelector('textarea'),null)
    }
    const writes=calls.filter(c=>c.method!=='GET')
    assert.deepEqual(writes,[typed,''].map((body,n)=>({method:'POST',path:'/api/v1/cases/'+caseId+'/recommendations',
      data:{title:'合成建议 '+n,addressee:'合成对象',causeNodeIds:['COLREG-R19'],dueUtc:'2099-06-30T15:59:59Z',isInterim:false,body}})))
    const paths=new Set(calls.filter(c=>c.method==='GET').map(c=>c.path))
    for(const path of ['/recommendations:board','/audit?category=SafetyRec&order=desc&limit=14','/audit?category=Consultation&order=desc&limit=6',''])
      assert.ok(paths.has('/api/v1/cases/'+caseId+path),path)
    writeFileSync(process.argv[2],JSON.stringify(writes))
    console.log('PASS RecommendationsPage creation via DOM: exact Chinese/paragraphs, empty compatible, original GETs and no additional writes')
  } finally { await React.act(async()=>root.unmount()); await win.happyDOM.close() }
}
main().then(() => process.exit(0), error => { console.error(error); process.exit(1) })
