'use strict';
const fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {spawnSync}=require('node:child_process');
const {pathToFileURL}=require('node:url');
const root=path.resolve(process.env.MCIS_SOURCE_ROOT||path.resolve(__dirname,'../..'));
const required=['MCIS_NODE_MODULES','MCIS_HOST_PYTHON','MCIS_HAPPY_DOM_PATH'];
if(required.some(k=>!process.env[k])){
 console.error('Required existing dependencies: '+required.join(', '));
 process.exit(2);
}
const modules=path.resolve(process.env.MCIS_NODE_MODULES);
const python=path.resolve(process.env.MCIS_HOST_PYTHON);
const happy=process.env.MCIS_HAPPY_DOM_PATH.startsWith('file:')?process.env.MCIS_HAPPY_DOM_PATH:pathToFileURL(path.resolve(process.env.MCIS_HAPPY_DOM_PATH)).href;
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'mcis-w19-exact-'));
try{
 const out=path.join(tmp,'check.mjs');
 require(path.join(modules,'esbuild')).buildSync({
  entryPoints:[path.join(root,'web/tests/knowledge-exact-card-reopen.tsx')],outfile:out,
  bundle:true,platform:'node',format:'esm',jsx:'automatic',nodePaths:[modules],
  banner:{js:"import {createRequire} from 'node:module'; const require=createRequire(import.meta.url);"},
 });
 const r=spawnSync(process.execPath,[out],{encoding:'utf8',timeout:40000,maxBuffer:1000000,env:{
  ...process.env,NODE_PATH:modules,MCIS_HOST_PYTHON:python,MCIS_HAPPY_DOM_PATH:happy,
  MCIS_HOST_SERVICE:path.join(root,'service'),MCIS_VERSION_HOST:path.join(__dirname,'host.py'),PYTHONDONTWRITEBYTECODE:'1',
 }});
 if(r.stdout)process.stdout.write(r.stdout);
 if(r.stderr)process.stderr.write(r.stderr);
 if(r.error)throw r.error;
 process.exitCode=r.status??1;
}finally{fs.rmSync(tmp,{recursive:true,force:true})}
