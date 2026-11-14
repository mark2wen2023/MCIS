// Emits a self-contained offline viewer to stdout. Does not read results or run Pi.
import {readFile} from 'node:fs/promises'
import {createHash} from 'node:crypto'
import {build} from '../../web/node_modules/esbuild/lib/main.js'
const base=new URL('.',import.meta.url)
let projection=null
if(process.argv.slice(2).length){
 if(process.argv.slice(2).join(' ')!=='--meeting')throw Error('Unsupported build mode')
 const chunks=[];let size=0;for await(const chunk of process.stdin){size+=chunk.length;if(size>1024*1024)throw Error('Display size limit');chunks.push(chunk)}
 const parser=await build({entryPoints:[new URL('meeting.ts',base).pathname],bundle:true,write:false,format:'esm',platform:'node'})
 const {parseMeeting}=await import('data:text/javascript;base64,'+Buffer.from(parser.outputFiles[0].text).toString('base64'))
 projection=parseMeeting(new Uint8Array(Buffer.concat(chunks)))
}
const sha=bytes=>createHash('sha256').update(bytes).digest('hex')
const packet=await readFile(new URL('../expert_group/public-packet.json',base))
if(sha(packet)!=='1dc5f6ccd93da013863abfd399b8e3f8682d2532e62d335eaa23cd5e18d8790e')throw Error('Frozen public packet changed')
const bundle=await build({entryPoints:[new URL('boot.ts',base).pathname],bundle:true,write:false,format:'iife',platform:'browser',target:'es2022',legalComments:'none',define:{__MCIS_MEETING__:JSON.stringify(projection)}})
const script=bundle.outputFiles[0].text.replace(/<\/script/gi,'<\\/script')
const style=await readFile(new URL('style.css',base),'utf8')
const cspHash=text=>createHash('sha256').update(text).digest('base64')
process.stdout.write(`<!doctype html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'sha256-${cspHash(script)}'; style-src 'sha256-${cspHash(style)}'; connect-src 'none'; form-action 'none'; base-uri 'none'; frame-src 'none'; object-src 'none'"><meta name="referrer" content="no-referrer"><title>MCIS 公开双专家研究工作台</title><style>${style}</style></head><body><main id="app"></main><noscript>此离线查看器需要 JavaScript；不会运行模型。</noscript><script>${script}</script></body></html>`)
