const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto')
const {execFileSync,spawnSync}=require('node:child_process')
const base='1f76a060dcf30f2cc403b5ef22ccc35f9f1e7d0c'
const root=path.resolve(__dirname,'../../..')
const arg=(flag)=>{const i=process.argv.indexOf(flag);return i<0?undefined:process.argv[i+1]}
const deps=path.resolve(arg('--web-deps')||path.join(root,'web/node_modules'))
const esbuild=require(path.join(deps,'esbuild'))
const original=arg('--baseline-page')?fs.readFileSync(arg('--baseline-page')):execFileSync('git',['show',base+':web/src/pages/KnowledgePage.tsx'],{cwd:root})
const blob=crypto.createHash('sha1').update('blob '+original.length+'\0').update(original).digest('hex')
if(blob!=='28ae58a1a39a39c23397b84f93c6d175b3fa7451')throw Error('BASELINE_PAGE_PIN_MISMATCH')
for(const [name,sha] of Object.entries({
 'fixture.json':'96006172f293802bac0ca7d834a711c643480fc9962b087ca4b77347dfd377fb',
 'results.json':'21668e131a792398c2988fbf5b998ed4d376b31024c104ff6d345db342a3347c'
})){
 const raw=fs.readFileSync(path.join(__dirname,'../version_binding',name))
 if(crypto.createHash('sha256').update(raw).digest('hex')!==sha)throw Error('FIXTURE_PIN_MISMATCH')
}
async function main(){
 const entries=process.argv.includes('--html')?[path.join(__dirname,'render.tsx')]:[path.join(__dirname,'test.tsx'),path.join(root,'web/tests/knowledge-w191.test.tsx'),path.join(root,'web/tests/knowledge-w192.test.tsx')]
 for(const entry of entries){
 const built=await esbuild.build({entryPoints:[entry],bundle:true,platform:'node',format:'cjs',jsx:'automatic',write:false,nodePaths:[deps],loader:{'.css':'empty'},logLevel:'warning',plugins:[{
 name:'fixed-original-page',
 setup(b){b.onResolve({filter:/^w19-baseline-page$/},()=>({path:'baseline',namespace:'pinned'}))
 b.onLoad({filter:/.*/,namespace:'pinned'},()=>({contents:original.toString('utf8'),loader:'tsx',resolveDir:path.join(root,'web/src/pages')}))}
 }]})
 const guard="Object.defineProperty(globalThis,'localStorage',{configurable:true,value:{getItem:()=>null,setItem:()=>{throw Error('storage write forbidden')}}});globalThis.fetch=()=>{throw Error('network forbidden')};"
 const r=spawnSync(process.execPath,['-'],{input:guard+built.outputFiles[0].text,encoding:'utf8',maxBuffer:1024*1024})
 process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'')
 if(r.error)console.error(r.error.message)
 if(r.status!==0)process.exit(r.status||1)
 }
}
main().catch(e=>{console.error(e.message);process.exitCode=1})
