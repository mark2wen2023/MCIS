"""Unexecuted orchestration for an APPROVED isolated host, not a server launcher.

No CLI can run this. The future trusted host owns TLS/session creation, a new
DB/root, cleanup and case-creation authorization. None is inferred from flags.
The transport must use same-origin server cookies; it must not retry requests.
"""
import re
from urllib.parse import quote
from .fixtures import CASE_IDS, cases, intake_bodies, materials, sha


class PreparationStopped(RuntimeError):
    pass


def checked(condition, message):
    if not condition:
        raise PreparationStopped(message)


def bind_existing_case_creator(*, context_for_creation=None):
    """Future trusted host only; missing authorization adapter fails before imports.

    context_for_creation must independently authorize creation for the exact
    synthetic ID and return a server Ctx. authority.py supplies the internal
    fixed-case provider; its configuration must come from a trusted host.
    case.read/session possession alone must never satisfy creation authority.
    The private router is a handler collector, never mounted or served.
    """
    checked(callable(context_for_creation), 'Explicit server case-creation authorization adapter required')
    from fastapi import APIRouter
    from mcis_service.cases.basic_registration import _register_basic_cases
    from mcis_service.common.context import Ctx
    _, create_case, _ = _register_basic_cases(APIRouter())

    async def create(body):
        checked(body in cases(), 'Only the two exact fabricated case bodies are supported')
        ctx = await context_for_creation(body['caseId'], 'case.create')
        checked(type(ctx) is Ctx, 'Server creation context unconfirmed')
        # Existing schema, role check, duplicate check, put_doc and audit intact.
        return 201, create_case(body=body, ctx=ctx)
    return create


async def prepare_registered_case_a(*, host):
    """host is a trusted integration adapter, NOT supplied by an HTTP client.

    Required adapter is deliberately absent in this candidate. approved_scope()
    must refuse without platform-approved isolation + NEW owned DB/root and must
    stop resources/revoke sessions/clean its own temporary paths on every exit.
    create_case(body) must invoke the existing create_case handler with an
    explicitly authorized server context. Generic case.read is NOT that grant.
    request(method,path,body) returns (status, decoded JSON), no auto retry.
    Do not instantiate this using a mock and label it a real preparation.
    """
    checked(host is not None, 'Approved isolation/identity host adapter is missing')
    # Resource lifetime encloses case creation and every read/write. No exception
    # is caught/retried here. An unknown commit stops the entire preparation.
    async with host.approved_scope():
        declared=cases()
        for case in declared:
            status,doc=await host.create_case(case)
            checked(status==201 and doc==case,'Case creation not confirmed; stop without retry')
        bodies=intake_bodies();raws=materials();cid=CASE_IDS[0]
        base='/api/v1/cases/'+quote(cid,safe='')
        for case in declared:
            status,doc=await host.request('GET','/api/v1/cases/'+quote(case['caseId'],safe=''),None)
            checked(status==200 and doc==case,'Same-case readback not confirmed')
            status,runs=await host.request('GET','/api/v1/cases/'+quote(case['caseId'],safe='')+'/image-reviews',None)
            checked(status==200 and runs==[],'Both cases must start with confirmed zero image runs')
        bindings={}
        for kind,body in bodies.items():
            status,preview=await host.request('POST',base+'/evidence-intakes:preview',body)
            checked(status==200 and isinstance(preview,dict),'Preview failed')
            digest=preview.get('requestDigest')
            checked(isinstance(digest,str) and re.fullmatch('[0-9a-f]{64}',digest) is not None,'Preview digest missing')
            checked(preview.get('caseId')==cid and preview.get('fileName')==body['fileName']
                    and preview.get('sourceSha256')==sha(raws[kind][1])
                    and preview.get('byteLength')==len(raws[kind][1])
                    and preview.get('metadata')=={key:body[key] for key in ('title','source','extractedBy','extractedUtc','category','confidentiality','note')},'Preview does not describe the fabricated request')
            # Confirmation is only of these exact fabricated bytes/declarations.
            status,receipt=await host.request('POST',base+'/evidence-intakes:commit',
                                            {**body,'requestDigest':digest,'confirmed':True})
            checked(status==200 and isinstance(receipt,dict),'Commit unconfirmed; may have committed, never retry automatically')
            checked(receipt.get('caseId')==cid and receipt.get('requestDigest')==digest
                    and receipt.get('sourceSha256')==preview['sourceSha256']
                    and receipt.get('fileName')==body['fileName']
                    and receipt.get('byteLength')==preview['byteLength']
                    and receipt.get('metadata')==preview['metadata']
                    and isinstance(receipt.get('evidenceId'),str)
                    and re.fullmatch(r'EV-[0-9]{3,}',receipt['evidenceId']) is not None,'Receipt mismatch')
            status,readback=await host.request('GET',base+'/evidence-intakes/'+digest,None)
            checked(status==200 and isinstance(readback,dict)
                    and all(readback.get(key)==receipt[key] for key in ('caseId','requestDigest','sourceSha256','evidenceId','metadata','fileName','byteLength')),
                    'Receipt readback mismatch')
            bindings[kind]=digest
        for cid in CASE_IDS:
            status,runs=await host.request('GET','/api/v1/cases/'+quote(cid,safe='')+'/image-reviews',None)
            checked(status==200 and runs==[],'Preparation must not create an image run')
        result={'caseId':CASE_IDS[0],'bindings':bindings,'imageRuns':0,'sourceVerified':False}
        # Host retains its resource scope while an approved UI driver/operator
        # imports these bindings, edits/saves/reloads, and exercises case controls.
        # This is a required continuation, not an invented browser implementation.
        return await host.review_in_same_origin_page(result)


if __name__ == '__main__':
    raise SystemExit('BLOCKED: no approved isolated host, trusted creation adapter, TLS/session bootstrap or browser driver; nothing started')
