const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),assert=require('node:assert/strict');
function harness(kind){const dir=path.join(__dirname,kind);const src=fs.readFileSync(path.join(dir,'fixed-handler.test.cjs'),'utf8').split('(async()=>{')[0];const ctx={require,__dirname:dir};vm.createContext(ctx);vm.runInContext(src+';globalThis.make=env',ctx);return ctx.make;}
const create=harness('create'),reply=harness('reply');
(async()=>{
 let c=create(),r=reply();let cp=c.ctx.respond(),rp=r.ctx.respond();await c.ctx.respond();await r.ctx.respond();assert.equal(c.calls,1);assert.equal(r.calls,1);
 c.reject(new Error('lost'));await cp;r.resolve({});await rp;assert.equal(c.states.at(-1),'unknown');assert.equal(r.states.at(-1),'idle');await c.ctx.respond();assert.equal(c.calls,1);assert.equal(r.changed,1);
 c=create();r=reply();cp=c.ctx.respond();rp=r.ctx.respond();r.reject(new Error('lost'));await rp;c.resolve({caseId:'C',id:'SR-2026-99'});await cp;assert.equal(c.states.at(-1),'created');assert.equal(r.states.at(-1),'unknown');await r.ctx.respond();assert.equal(r.calls,1);await c.ctx.respond();assert.equal(c.calls,1);
 c=create();r=reply();cp=c.ctx.respond();rp=r.ctx.respond();c.unmount();r.unmount();c.resolve({caseId:'C',id:'SR-2026-99'});r.resolve({});await Promise.all([cp,rp]);assert.equal(c.changed,0);assert.equal(r.changed,0);assert.equal(c.states.at(-1),'sending');assert.equal(r.states.at(-1),'sending');
 console.log('3 combined-source cross-handler scenarios passed: independent locks, success/unknown isolation, late unmount. Synthetic hooks, not mounted-page DOM.');
})().catch(e=>{console.error(e);process.exitCode=1});
