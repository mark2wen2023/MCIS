"""Concurrent same-ID creation must not turn into an update."""
from concurrent.futures import ThreadPoolExecutor
import threading
from .conftest import C,H


def test_concurrent_create_never_updates_existing_case(client,empty_client,monkeypatch):
    from mcis_service.cases import router as module
    original=module.put_doc
    entered=threading.Event()
    other_entered=threading.Event()
    count=0
    guard=threading.Lock()
    def delayed(*args,**kwargs):
        nonlocal count
        with guard:
            count+=1
            first=count==1
        if first:
            entered.set()
            other_entered.wait(.3)
        else: other_entered.set()
        return original(*args,**kwargs)
    monkeypatch.setattr(module,'put_doc',delayed)
    case=client.get(C,headers=H()).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first=pool.submit(empty_client.post,'/api/v1/cases',headers=H(),json={**case,'title':'first creation'})
        assert entered.wait(2)
        second=pool.submit(empty_client.post,'/api/v1/cases',headers=H(),json={**case,'title':'second creation'})
        responses=[first.result(timeout=10),second.result(timeout=10)]
    assert sorted(r.status_code for r in responses)==[201,409],[(r.status_code,r.text) for r in responses]
    winner=next(r.json() for r in responses if r.status_code==201)
    assert empty_client.get(C,headers=H()).json()['title']==winner['title']
