const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),crypto=require('node:crypto'),{createRequire}=require('node:module'),{spawnSync}=require('node:child_process');
const web=path.resolve(process.argv[2]||path.join(__dirname,'../../web'));
const dependencies=createRequire(path.join(web,'package.json'));
const input=path.join(__dirname,'../single_seat_preview/result.json');
if(crypto.createHash('sha256').update(fs.readFileSync(input)).digest('hex')!=='ab3543be14e7e2271790a1a0cb03d61a3a779adb0f3682ef56f32050317f3dc9')throw Error('Fixed preview bytes changed');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'single-seat-ssr-'));
try{
 dependencies('esbuild').buildSync({entryPoints:[path.join(__dirname,'check.tsx')],outfile:path.join(temp,'check.cjs'),bundle:true,platform:'node',format:'cjs',jsx:'automatic',nodePaths:[path.join(web,'node_modules')],logLevel:'warning'});
 const r=spawnSync(process.execPath,[path.join(temp,'check.cjs')],{encoding:'utf8'});process.stdout.write(r.stdout||'');process.stderr.write(r.stderr||'');process.exitCode=r.status===null?1:r.status;
}finally{fs.rmSync(temp,{recursive:true,force:true})}
