import {declarationSnapshot} from '../compare.mjs';
const H='a'.repeat(64),J='b'.repeat(64);
function pair(role){
 const data={caseId:'SYNTHETIC',recordId:'INTERVIEW-A',record:{evidenceId:'EV-1',sourceSha256:H}};
 return {interview:{state:'available',data},media:{state:'available',data:{caseId:'SYNTHETIC',runId:'RUN-'+role,revision:0,initial:{sourceVersions:{pdf:{evidenceId:'EV-1',sha256:H},image:{evidenceId:'EV-1',sha256:H}},candidate:{source:{pdf_sha256:H,image_sha256:H}}}}},selection:{caseId:'SYNTHETIC',runId:'RUN-'+role,reviewRevision:0,mediaKind:'image',sourceRole:role},roleDeclaration:{role,basisText:'合成人工声明',declaredAt:'合成时间标签',declarerProvenance:'合成且未认证',boundSnapshot:declarationSnapshot(data)},historyEvents:[]};
}
export const scenarioNames=['多角色一致','ID及摘要多错','缺失与null','同案不同笔录','跨案件','显式ABA','不可用','重复角色','文本转义'];
export function scenario(name){
 if(!scenarioNames.includes(name))throw Error('Unknown synthetic scenario');
 const a=pair('pdf'),b=pair('image');
 if(name==='ID及摘要多错'){b.media.data.initial.sourceVersions.image.evidenceId='EV-2';b.media.data.initial.sourceVersions.image.sha256=J;b.media.data.initial.candidate.source.image_sha256=J}
 if(name==='缺失与null'){delete b.media.data.initial.candidate.source.image_sha256;b.media.data.initial.sourceVersions.image.sha256=null}
 if(name==='同案不同笔录'){b.interview.data.recordId='INTERVIEW-B';b.roleDeclaration.boundSnapshot=declarationSnapshot(b.interview.data)}
 if(name==='跨案件')b.media.data.caseId='OTHER';
 if(name==='显式ABA'){const s=declarationSnapshot(b.interview.data);b.historyEvents=[{type:'snapshot_observed',snapshot:{...s,recordId:'INTERVIEW-B'}},{type:'snapshot_observed',snapshot:s}]}
 if(name==='不可用')b.interview={state:'unavailable'};
 if(name==='重复角色')return {requiredRoles:['pdf','image'],pairs:[a,a,b]};
 if(name==='文本转义')b.roleDeclaration.basisText='<script>synthetic</script>';
 return {requiredRoles:['pdf','image'],pairs:[a,b]};
}
