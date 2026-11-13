// Synthetic, in-process orchestration experiment only. Not authentication or a sandbox.
import {createAdapter} from './adapter.mjs';
export const ROLES=Object.freeze(['regulation','navigation','investigation','vessel']);
export function createPanel({actor, snapshot, access, providers, maxCalls=8, turnBudget=2}) {
  if(actor!=='investigator') throw Error('human start required');
  if(snapshot?.synthetic!==true || !snapshot.caseId || !Array.isArray(snapshot.sources) || !snapshot.sources.some(x=>x.kind==='report')) throw Error('synthetic draft required');
  if(!Number.isSafeInteger(turnBudget)||turnBudget<1||turnBudget>32) throw Error('budget');
  const frozen=structuredClone(snapshot), reviews={}, turns=[], agents={}, grants={}, failed=new Set();
  if(new Set(frozen.sources.map(s=>s.id)).size!==frozen.sources.length) throw Error('duplicate source');
  if(new Set(ROLES.map(r=>providers?.[r])).size!==ROLES.length) throw Error('distinct providers required'); let phase='independent', busy=false;
  for (const role of ROLES) {
    if(!Array.isArray(access?.[role])||typeof providers?.[role]!=='function') throw Error('role configuration');
    const allowed=new Set(access[role]); grants[role]=allowed;
    // The trusted host chooses each instance's case and source grants, not the model.
    const scope={...frozen,sources:frozen.sources.filter(s=>allowed.has(s.id))};
    if(!scope.sources.some(s=>s.kind==='report')) throw Error('draft access required');
    agents[role]=createAdapter({scope,streamFn:providers[role],maxCalls});
  }
  // Conservative information-flow rule: a viewer must have all grants of each speaker,
  // not merely the cited source. Still not a semantic DLP or trusted-provider boundary.
  const visible=(viewer,speaker)=>[...grants[speaker]].every(id=>grants[viewer].has(id));
  const peerContext=role=>({reviews:Object.fromEntries(Object.entries(reviews).filter(([speaker])=>visible(role,speaker))),turns:turns.filter(t=>visible(role,t.speaker) && visible(role,t.target))});
  const check=role=>{if(!ROLES.includes(role)) throw Error('role');if(phase==='cancelled')throw Error('cancelled');if(busy)throw Error('busy');};
  return {
    async review(role) {check(role);if(failed.has(role))throw Error('role requires restart after failure');if(phase!=='independent'||reviews[role])throw Error('phase');busy=true;
      try {const r=await agents[role].run(`You are ${role}. Independently review only the authorized synthetic draft and evidence. Submit one candidate with a source reference. Peers are hidden.`);
        if(phase==='cancelled')throw Error('cancelled');
        if(r.status!=='completed'||r.candidates.length!==1) throw Error('no single candidate');
        reviews[role]=structuredClone(r.candidates[0]);if(Object.keys(reviews).length===4)phase='cross_examination';return structuredClone(reviews[role]);
      } catch(e) {failed.add(role);throw e;} finally {busy=false;}
    },
    async challenge(role,target) {check(role);if(failed.has(role))throw Error('role requires restart after failure');if(phase!=='cross_examination'||!ROLES.includes(target)||target===role||!visible(role,target))throw Error('phase or target');busy=true;
      try {const context=JSON.stringify(peerContext(role));const r=await agents[role].run(`Cross-examine ${target} using only this host-approved synthetic peer context: ${context}. Submit one candidate with a source reference.`);
        if(phase==='cancelled')throw Error('cancelled');
        if(r.status!=='completed'||r.candidates.length!==1)throw Error('no single candidate');
        const turn={speaker:role,target,candidate:structuredClone(r.candidates[0])};turns.push(turn);if(turns.length>=turnBudget)phase='budget_exhausted';return structuredClone(turn);
      } catch(e) {failed.add(role);throw e;} finally {busy=false;}
    },
    context(role){check(role);return structuredClone({host:'海青君',phase,...(phase==='independent'?{}:peerContext(role))});},
    cancel(actor){if(actor!=='investigator')throw Error('human cancel required');phase='cancelled';for(const role of ROLES)agents[role].cancel();}
  };
}
