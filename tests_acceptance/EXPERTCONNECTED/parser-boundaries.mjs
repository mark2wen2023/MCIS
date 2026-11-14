import assert from 'node:assert/strict'
import {readFileSync} from 'node:fs'
import {build} from '../../web/node_modules/esbuild/lib/main.js'
const built=await build({entryPoints:['research/expert_workbench/meeting.ts'],bundle:true,write:false,format:'esm',platform:'node'})
const {parseMeeting}=await import('data:text/javascript;base64,'+Buffer.from(built.outputFiles[0].text).toString('base64'))
const original=JSON.parse(readFileSync(0,'utf8'));let failures=0
const cases=[
 ['completed role calls exceed received',d=>{d.meetingPhase='stopped_unknown';Object.assign(d.rounds[1].roles[1],{status:'unknown',modelCalls:1,toolCalls:0,reviews:[]});Object.assign(d.budget,{totalModels:10,totalTools:6,received:8,unknown:1})}],
 ['not_started role has model calls',d=>{d.meetingPhase='stopped_unknown';d.rounds=d.rounds.slice(0,1);Object.assign(d.rounds[0].roles[1],{status:'not_started',modelCalls:1,toolCalls:0,reviews:[]});Object.assign(d.budget,{totalModels:4,totalTools:2,received:3,unknown:1})}],
 ['ready has completed rounds',d=>d.meetingPhase='ready'],
 ['round_review has two completed rounds',d=>d.meetingPhase='round_review'],
 ['round_open has all roles completed',d=>d.meetingPhase='round_open'],
]
for(const [name,mutate] of cases){const d=structuredClone(original);mutate(d);try{assert.throws(()=>parseMeeting(new TextEncoder().encode(JSON.stringify(d))));console.log('PASS '+name)}catch{failures++;console.log('FAIL '+name)}}
console.log(`${cases.length-failures}/${cases.length} parser boundary cases passed`);if(failures)process.exitCode=1
