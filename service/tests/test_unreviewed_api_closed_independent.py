"""Independent default-route check without any asserted role header."""
import pytest
from .conftest import C
from .test_binding_review_independent import snapshot

@pytest.mark.parametrize('method',['GET','POST','PUT'])
def test_default_unreviewed_route_absent_without_identity(client,method):
    before=snapshot(client)
    response=client.request(method,C+'/timeline/unreviewed-runs',json={
        'operationId':'40000000-0000-4000-8000-000000000001',
        'request':{'sources':[{'evidenceId':'EV-001','csvMapping':{'timeColumn':'utc','columns':[{'column':'heading','kind':'Heading'}]}}]}})
    assert response.status_code==404
    assert snapshot(client)==before
