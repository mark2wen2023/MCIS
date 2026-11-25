'use strict'
const {createHash}=require('node:crypto')
const {mkdtempSync,mkdirSync,readFileSync,rmSync}=require('node:fs')
const {tmpdir}=require('node:os')
const {dirname,isAbsolute,join,resolve}=require('node:path')
const {spawnSync}=require('node:child_process')
const {parseArgs}=require('node:util')

function main(){
 const {values:v}=parseArgs({options:{repo:{type:'string'},python:{type:'string'},'happy-dom':{type:'string'},'node-modules':{type:'string'}}})
 if(!v.repo||!v.python||!v['happy-dom'])throw Error('Usage: node run.cjs --repo /candidate --python /venv/bin/python --happy-dom /installed/happy-dom/lib/index.js [--node-modules /existing/web/node_modules]')
 const repo=resolve(v.repo), python=resolve(v.python), happy=resolve(v['happy-dom']), nm=resolve(v['node-modules']||join(repo,'web/node_modules'))
 const pins=JSON.parse(readFileSync(join(__dirname,'pins.json'),'utf8'))
 for(const [file,expected] of Object.entries(pins)){
   if(isAbsolute(file)||file.split('/').includes('..'))throw Error('invalid pin path')
   const bytes=readFileSync(join(repo,file))
   if(createHash('sha1').update('blob '+bytes.length+'\0').update(bytes).digest('hex')!==expected)
     throw Error('product or dependency pin mismatch: '+file)
 }
 console.log('Pinned product files: '+Object.keys(pins).length)
 const work=mkdtempSync(join(tmpdir(),'w7-deadline-fullflow-'))
 try{
   const store=join(work,'db'), bundle=join(work,'check.cjs')
   mkdirSync(store)
   const environment={...process.env,NODE_PATH:nm,PYTHONDONTWRITEBYTECODE:'1',PYTHONPATH:join(repo,'service')}
   function run(exe,args){
     const r=spawnSync(exe,args,{cwd:work,env:environment,stdio:'inherit',timeout:60000})
     if(r.error)throw r.error
     if(r.status!==0)throw Error(exe+' exited '+r.status+(r.signal?' ('+r.signal+')':''))
   }
   run(join(nm,'.bin/esbuild'),[join(__dirname,'check.tsx'),'--bundle','--platform=node','--format=cjs','--jsx=automatic','--loader:.css=empty','--log-level=warning','--outfile='+bundle,'--alias:happy-dom='+happy,'--alias:w7-pinned-page='+join(repo,'web/src/pages/RecommendationsPage.tsx')])
   run(process.execPath,[bundle,python,join(__dirname,'bridge.py'),store])
 }finally{rmSync(work,{recursive:true,force:true})}
}
try{main()}catch(e){console.error('W7 flow: '+e.message);process.exitCode=1}
