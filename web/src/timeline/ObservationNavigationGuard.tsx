import {useEffect} from 'react'
import {useBlocker} from 'react-router-dom'
import {guardObservationUnload,hasObservationDraft,LEAVE_OBSERVATION_MESSAGE} from './observationDraftGuard'
export function ObservationNavigationGuard({children}:{children:React.ReactNode}){
  const blocker=useBlocker(()=>hasObservationDraft())
  useEffect(()=>{
    window.addEventListener('beforeunload',guardObservationUnload)
    return()=>window.removeEventListener('beforeunload',guardObservationUnload)
  },[])
  useEffect(()=>{
    if(blocker.state==='blocked'){
      if(window.confirm(LEAVE_OBSERVATION_MESSAGE))blocker.proceed()
      else blocker.reset()
    }
  },[blocker])
  return children
}
