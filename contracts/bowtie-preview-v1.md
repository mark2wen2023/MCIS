# W15.3 Bow-tie hypothesis structure preview

Scope: blank manual hypothetical diagram; no persistence, confirmed facts, risk score, legal/causal conclusion, automatic analysis or W11/ECFC integration. Existing unchanged BowTieModel is the only structure-rule implementation. Nodes are always ToBeVerified, barriers always Unknown; neither accepted from clients. Source metadata binding does not verify source bytes or substantiate any link. All tests synthetic.

Method references inspected 2026-11-12: UK CAA https://www.caa.co.uk/safety-initiatives/working-with-industry/bowtie/about-bowtie/introduction-to-bowtie/ and https://www.caa.co.uk/safety-initiatives/working-with-industry/bowtie/safety-risk-priorities/evaluating-using-control-effectiveness/ . General aviation methodology reference, not maritime law. Hazard sets context; top event denotes loss of control; preventive/recovery controls occupy opposite sides. Effectiveness needs contextual assessment and is NOT inferred by this preview. Threat-chain/allowed-edge constraints are project assumptions. No-barrier direct paths may be structurally valid, not safe or sufficiently controlled.

Original page14 prototype and DEFECTS/W15.md retrieved from main34048e4. This slice implements editable Bow-tie subset only; AcciMap, STAMP, ECFC import, status assessment, export, persistence/review remain unimplemented.

## HTTP
GET /api/v1/cases/{case_id}/systemic/bowtie:sources
POST /api/v1/cases/{case_id}/systemic/bowtie:preview
no-store, Investigator/LeadInvestigator with full personal/evidence_meta read; restricted evidence visibility uses existing policy. Role headers are local self-report, not identity authentication. Explicit SQLite snapshot, before/after full case/policy/selected-source fingerprint; revoked permission403, changed context409. No database/audit writes. CLI unavailable503, no Python fallback.

GET response {profile:"MCIS-BOWTIE-PREVIEW-1",caseId,sources:[{evidenceId,title,sha256}],sourceBinding:"registered-metadata-only",identityMode:"local-role-header"}.

POST exact body {model:{hazard,topEvent:{id,label},nodes:[{id,label,kind,barrierId}],edges:[{fromId,toId}]},sourceEvidenceIds:[]}.
UTF8 JSON <=128KiB, no duplicate/unknown keys/nonfinite numbers; 0..64 nodes,0..128 edges,0..8 unique source IDs. IDs ASCII [A-Za-z0-9_-],1..64; trimmed nonempty hazard/labels <=500 chars. kinds Threat/PreventionBarrier/MitigationBarrier/Consequence/EscalationFactor; barrierId string only for EscalationFactor, otherwise null. Duplicate node/edge IDs and invalid links retained for core construction diagnostics, not silently dropped. Sources apply to the whole draft as supporting materials, NOT individual-node verified evidence; no core refs are populated.

POST response {profile,caseId,inputSha256,sources,sourceRole,sourceBinding:"registered-metadata-only",persisted:false,assessment:"hypothesis-structure-only",result,limitations:[...]}. inputSha256 canonical recursive-sort compact UTF8 JSON of {caseId,model,sources:<ID-sorted snapshots>}. Frontend must recompute, compare sources, clear result on input/case/identity changes, reject stale or mismatched responses.

## CLI tools/mcis-bowtie
stdin model object alone. stdout {ok:true,result:{coreVersion:"mcis-bowtie/1",mode:"hypothesis-structure-only",constructionErrors:[{code,elementId,message}],validationIssues:[{code,elementId,message,severity}],structureValid:boolean,notCheckedRefCount:0,nodeCount:number,edgeCount:number}}. Construction failure stops at first failure, structureValid false, validationIssues empty, counts indicate successfully accepted temporary items; no partial graph displayed as validated. Successful construction returns all Validate issues and exact accepted counts. Input protocol rejection {ok:false,error:{code,message}}, exit4; unexpected operational failures nonzero. No core IsValid exported as factual validation. Max stdout256KiB, process timeout bounded. Explicit 10-file dependency list excludes SystemicEcfcImport/SystemicJson/SystemicDocument and W11.
