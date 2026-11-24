const path=require('node:path'),{spawnSync}=require('node:child_process');
const fs=require('node:fs'),crypto=require('node:crypto');
const baseline=process.env.MCIS_BASELINE_PAGE;
const plugins=baseline?[{name:'fixed-baseline',setup(b){b.onLoad({filter:/KnowledgePage\.tsx$/},args=>{const raw=fs.readFileSync(baseline);if(crypto.createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex')!=='98efab8c9626c011a881075b5e616d62847a79b3')throw Error('baseline pin mismatch');return {contents:raw.toString(),loader:'tsx',resolveDir:path.dirname(args.path)}})}}]:[];
const root=path.resolve(__dirname,'../..'),modules=process.env.MCIS_NODE_MODULES||path.resolve('mcis-work/web/node_modules');
async function main(){
await require(path.join(modules,'esbuild')).build({entryPoints:[__dirname+'/check.tsx'],outfile:__dirname+'/check.mjs',bundle:true,platform:'node',format:'esm',jsx:'automatic',nodePaths:[modules],loader:{'.css':'empty'},plugins,banner:{js:"import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);"}});
const r=spawnSync(process.execPath,[__dirname+'/check.mjs'],{encoding:'utf8',timeout:20000,env:{...process.env,MCIS_HAPPY_DOM_PATH:process.env.MCIS_HAPPY_DOM_PATH||'file://'+path.resolve('w19-react-1600/node_modules/happy-dom/lib/index.js')}});console.log(JSON.stringify({exit:r.status,stdout:r.stdout,stderr:r.stderr?.slice(-2000),error:r.error?.message}));process.exitCode=r.status??1;

}
main().catch(e=>{console.error(e);process.exitCode=1});
