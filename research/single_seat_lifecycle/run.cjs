const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto'),{pathToFileURL}=require('node:url'),Module=require('node:module')
const root=path.resolve(__dirname,'../..')
const web=path.resolve(process.argv[2]||path.join(root,'web/node_modules'))
const dom=path.resolve(process.argv[3]||path.join(web,'happy-dom/lib/index.js'))
async function main(){
 for(const [name,pin] of Object.entries({
 'research/single_seat_card/Card.tsx':'fcc6bab4e474bf30b62804c80b587bfeb85d9f3f',
 'research/single_seat_preview/result.json':'6a0653b1f6881213009bbc35bd6aa93d147f3ca1'})){
  const raw=fs.readFileSync(path.join(root,name));if(crypto.createHash('sha1').update('blob '+raw.length+'\0').update(raw).digest('hex')!==pin)throw Error('PIN_MISMATCH:'+name)
 }
 const {Window}=await import(pathToFileURL(dom).href)
 const window=new Window({url:'http://127.0.0.1/'})
 Object.assign(globalThis,{window,document:window.document,HTMLElement:window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true})
 const denied=()=>{throw Error('network/storage forbidden')}
 globalThis.fetch=denied;window.fetch=denied
 for(const store of [window.localStorage,window.sessionStorage]){store.setItem=denied;store.removeItem=denied;store.clear=denied}
 try{
  const esbuild=require(path.join(web,'esbuild'))
  const out=await esbuild.build({entryPoints:[path.join(__dirname,'check.tsx')],bundle:true,platform:'node',format:'cjs',jsx:'automatic',write:false,nodePaths:[web]})
  const m=new Module(path.join(__dirname,'in-memory.cjs'),module)
  m.filename=path.join(__dirname,'in-memory.cjs');m.paths=module.paths
  m._compile(out.outputFiles[0].text,m.filename)
  await m.exports.run()
 }finally{await window.happyDOM.close()}
}
main().then(()=>process.exit(0),e=>{console.error(e);process.exit(1)})
