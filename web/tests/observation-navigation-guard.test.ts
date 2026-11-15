// Real installed router state machine, synthetic predicates/events; no browser UI.
import assert from 'node:assert/strict'
import {createMemoryRouter} from 'react-router-dom'
import {registerObservationDraft,hasObservationDraft,guardObservationUnload} from '../src/timeline/observationDraftGuard'
let assertions=0
const ok=(value:unknown)=>{assert.ok(value);assertions++}
async function main(){
 let dirty=false
 const remove=registerObservationDraft(()=>dirty)
 ok(!hasObservationDraft());dirty=true;ok(hasObservationDraft())
 let prevented=0
 const event={preventDefault:()=>{prevented++},returnValue:'unchanged'} as unknown as BeforeUnloadEvent
 guardObservationUnload(event);ok(prevented===1&&event.returnValue==='')
 dirty=false;guardObservationUnload(event);ok(prevented===1)
 const router=createMemoryRouter([{path:'*',element:null}],{initialEntries:['/lobby','/evidence?case=A'],initialIndex:1})
 router.getBlocker('observations',()=>hasObservationDraft())
 dirty=true
 await router.navigate('/report?case=A')
 ok(router.state.location.pathname==='/evidence');ok(router.state.blockers.get('observations')?.state==='blocked')
 router.state.blockers.get('observations')?.reset?.()
 ok(router.state.location.pathname==='/evidence')
 await router.navigate('/evidence?case=B')
 ok(router.state.location.search==='?case=A');ok(router.state.blockers.get('observations')?.location?.search==='?case=B')
 router.state.blockers.get('observations')?.reset?.()
 await router.navigate(-1)
 ok(router.state.blockers.get('observations')?.state==='blocked');ok(router.state.location.pathname==='/evidence')
 router.state.blockers.get('observations')?.reset?.()
 await router.navigate('/report?case=A');router.state.blockers.get('observations')?.proceed?.()
 await new Promise(resolve=>setTimeout(resolve,0))
 ok(router.state.location.pathname==='/report')
 dirty=false;await router.navigate('/evidence?case=A');ok(router.state.location.pathname==='/evidence')
 const removeSecond=registerObservationDraft(()=>true);ok(hasObservationDraft());removeSecond();ok(!hasObservationDraft())
 dirty=true;remove();ok(!hasObservationDraft());router.dispose()
 console.log(`${assertions} synthetic events/real memory-router assertions passed; no browser`)
}
main().catch(e=>{console.error(e);process.exitCode=1})
