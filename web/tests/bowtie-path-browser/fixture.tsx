import {createRoot} from 'react-dom/client'
import {BowtieForm} from '../../src/bowtiePreview/BowtieForm'
import {getOperator,setIdentity} from '../../src/api'
import {inputHash,type Input} from '../../src/bowtiePreview/model'
const caseId='SYN-NAV', sources=[{evidenceId:'SYN-E1',title:'Synthetic draft reference',sha256:'a'.repeat(64)}]
setIdentity('Investigator','Synthetic')
const who='Investigator\n'+getOperator()
let previews=0
window.fetch=async (url,init)=>{
 if(url!=='/api/v1/cases/SYN-NAV/systemic/bowtie:preview' || init?.method!=='POST' || typeof init.body!=='string')throw Error('Unexpected fixture request')
 previews++
 const i=JSON.parse(init.body) as Input
 const selected=sources.filter(s=>i.sourceEvidenceIds.includes(s.evidenceId))
 return Response.json({profile:'MCIS-BOWTIE-PREVIEW-1',caseId,inputSha256:await inputHash(caseId,i.model,selected),sources:selected,sourceRole:'Investigator',sourceBinding:'registered-metadata-only',persisted:false,assessment:'hypothesis-structure-only',result:{coreVersion:'mcis-bowtie/1',mode:'hypothesis-structure-only',constructionErrors:[],validationIssues:[],structureValid:true,notCheckedRefCount:0,nodeCount:i.model.nodes.length+1,edgeCount:i.model.edges.length},limitations:['Synthetic response only']})
}
Object.assign(window,{fixtureRequestCount:()=>previews})
createRoot(document.getElementById('root')!).render(<BowtieForm {...{caseId,who,sources}}/>)
