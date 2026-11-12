import * as esbuild from '../../web/node_modules/esbuild/lib/main.js'
import path from 'node:path'
const root=path.dirname(new URL(import.meta.url).pathname)
await esbuild.build({entryPoints:[root+'/lifecycle.tsx'],bundle:true,platform:'node',format:'cjs',outfile:root+'/.tmp-lifecycle.cjs',jsx:'automatic',loader:{'.css':'empty'},plugins:[{name:'test-hooks',setup(b){b.onResolve({filter:/^(react|react\/jsx-runtime)$/},()=>({path:root+'/hooks.ts'}));b.onResolve({filter:/^\.\.\/api$/},()=>({path:root+'/identity.ts'}))}}]})
