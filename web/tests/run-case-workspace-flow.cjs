// Offline actual component SSR only; no app imports or network.
const {buildSync}=require('esbuild'),Module=require('node:module'),path=require('node:path')
const result=buildSync({entryPoints:['tests/case-workspace-flow.test.tsx'],bundle:true,platform:'node',format:'cjs',jsx:'automatic',packages:'external',loader:{'.css':'empty'},write:false})
const filename=path.resolve('tests/.case-workspace-flow.cjs'),test=new Module(filename,module)
test.filename=filename;test.paths=Module._nodeModulePaths(path.dirname(filename))
const previous=global.fetch;global.fetch=()=>{throw new Error('Network forbidden')}
try{test._compile(result.outputFiles[0].text,filename)}finally{global.fetch=previous}
