/** Python-parent protocol child. Receives NO credential, environment key or prompt. */
import {openSync,writeSync,fsyncSync,closeSync} from 'node:fs';
import {runBlind} from './blind-runner.mjs';
console.log=console.warn=console.error=()=>{};
let fd,closed=false,buffer='',total=0,waiter=null;const queue=[];
const fail=()=>{if(waiter){waiter.reject(Error('BLIND_FAILED'));waiter=null}closed=true};
process.stdin.setEncoding('utf8');process.stdin.on('data',chunk=>{if(closed)return;total+=Buffer.byteLength(chunk);buffer+=chunk;if(total>8*1024*1024||Buffer.byteLength(buffer)>1024*1024){fail();return}let p;while((p=buffer.indexOf('\n'))>=0){const line=buffer.slice(0,p);buffer=buffer.slice(p+1);try{const v=JSON.parse(line);if(waiter){const w=waiter;waiter=null;w.resolve(v)}else{queue.push(v);if(queue.length>2)fail()}}catch{fail()}}});process.stdin.on('end',fail);process.stdin.on('error',fail);
const read=()=>{if(closed)return Promise.reject(Error('BLIND_FAILED'));if(queue.length)return Promise.resolve(queue.shift());return new Promise((resolve,reject)=>{if(waiter)return reject(Error('BLIND_FAILED'));waiter={resolve,reject}})};
let commands=0;const send=v=>new Promise((resolve,reject)=>{if(++commands>96||Buffer.byteLength(JSON.stringify(v))>1024*1024)return reject(Error('BLIND_FAILED'));process.stdout.write(JSON.stringify(v)+'\n',err=>err?reject(Error('BLIND_FAILED')):resolve())});
let runId,attempts=0;const append=(phase,meta={})=>{const value={version:1,phase,...(runId?{runId}:{}),...meta};writeSync(fd,JSON.stringify(value)+'\n');fsyncSync(fd)};
const watchdog=setTimeout(()=>{try{if(fd!==undefined)append('failed_unknown')}catch{}process.exit(1)},185000);
try{
 const argv=process.argv.slice(2);if(argv.length!==3||!['--fixture','--approved-blind'].includes(argv[0])||argv[1]!=='--receipt'||!argv[2]||argv[2].includes('\0'))throw Error('BLIND_FAILED');
 fd=openSync(argv[2],'wx',0o600);append('created');
 const ready=await read();if(ready?.mode!==(argv[0]==='--fixture'?'fixture':'remote-deepseek')||typeof ready.runId!=='string'||! /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(ready.runId))throw Error('BLIND_FAILED');for(const k of ['manifestDigest','inputDigest','corpusSha256'])if(typeof ready[k]!=='string'||ready[k].length!==64||!/^[0-9a-f]{64}$/.test(ready[k]))throw Error('BLIND_FAILED');if(ready.model!=='deepseek-v4-pro')throw Error('BLIND_FAILED');runId=ready.runId;append('ready',{transportMocked:argv[0]==='--fixture',manifestDigest:ready.manifestDigest,inputDigest:ready.inputDigest,corpusSha256:ready.corpusSha256,model:'deepseek-v4-pro',piVersion:'1.5.2'});
 const host={call:async c=>{await send(c);return await read()}};
 const r=await runBlind({host,ready,recordAttempt:async a=>{attempts=a.attempt;append('request_attempt_started',{attempt:a.attempt,realRequest:a.realRequest})}});
 append('predictions_validated',{models:r.models,tools:r.tools});const cleanup=await host.call({op:'close'});if(cleanup?.closed!==true)throw Error('BLIND_FAILED');append('cleanup_verified');
 await send({op:'node_complete',models:r.models,tools:r.tools});append('node_protocol_complete',{models:r.models,tools:r.tools});closeSync(fd);fd=undefined;clearTimeout(watchdog);process.exit(0);
}catch{try{if(fd!==undefined){append('failed_unknown',{attempts});closeSync(fd)}}catch{}clearTimeout(watchdog);process.stderr.write('BLIND_FAILED\n');process.exit(1)}
