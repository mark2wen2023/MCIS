const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),cp=require('node:child_process');
const root=path.resolve(__dirname,'../..'),deps=process.env.MCIS_NODE_MODULES;
if(!deps||!fs.existsSync(path.join(deps,'esbuild')))throw Error('Set MCIS_NODE_MODULES to existing offline dependencies');
const esbuild=require(path.join(deps,'esbuild')),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'ecfc-graph-check-'));
(async()=>{try{const out=path.join(tmp,'check.cjs');await esbuild.build({entryPoints:[path.join(__dirname,'check.tsx')],outfile:out,bundle:true,platform:'node',format:'cjs',packages:'external',jsx:'automatic',loader:{'.css':'empty'},plugins:[{name:'explicit-test-boundary',setup(b){
 b.onResolve({filter:/^react$/},a=>/ecfcDrafts\/(Panel|Graph)\.tsx$/.test(a.importer)?{path:path.join(__dirname,'hooks.ts')}:undefined);
 b.onResolve({filter:/^\.\/api$/},a=>a.importer.endsWith('/ecfcDrafts/Panel.tsx')?{path:path.join(__dirname,'api.ts')}:undefined);
 b.onLoad({filter:/ecfcDrafts\/Panel\.tsx$/},a=>({contents:fs.readFileSync(a.path,'utf8')+'\nexport {Editor};',loader:'tsx'}));
 }}]});const pre=path.join(tmp,'pre.cjs');fs.writeFileSync(pre,"const store=()=>{const m=new Map();return {getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,v),removeItem:k=>m.delete(k)}};global.localStorage=store();global.sessionStorage=store();global.fetch=()=>{throw Error('network forbidden')};\n");
 const r=cp.spawnSync(process.execPath,['-r',pre,out],{cwd:path.join(root,'web'),env:{...process.env,NODE_PATH:deps},stdio:'inherit'});process.exitCode=r.status??1;
}finally{fs.rmSync(tmp,{recursive:true,force:true})}})().catch(e=>{console.error(e);process.exitCode=1});
