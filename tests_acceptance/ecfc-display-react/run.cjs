// Existing dependencies only; all build output in an automatically removed temp directory.
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),cp=require('node:child_process');
const deps=process.env.MCIS_NODE_MODULES;
if(!deps||!path.isAbsolute(deps))throw Error('Set MCIS_NODE_MODULES to existing absolute node_modules');
const folder=fs.mkdtempSync(path.join(os.tmpdir(),'ecfc-react-display-'));
try{
 const esbuild=require(path.join(deps,'esbuild'));
 esbuild.buildSync({entryPoints:[path.join(__dirname,'check.tsx')],bundle:true,platform:'node',format:'cjs',jsx:'automatic',nodePaths:[deps],outfile:path.join(folder,'check.cjs'),logLevel:'warning'});
 const result=cp.spawnSync(process.execPath,[path.join(folder,'check.cjs')],{stdio:'inherit'});
 if(result.error)throw result.error;process.exitCode=result.status??1;
}finally{fs.rmSync(folder,{recursive:true,force:true})}
