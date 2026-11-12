"""Prepared before implementation freeze; run only once implementation is ready."""
import json
from helpers import client,seed,save_body,save,endpoint,export,unzip,intake
MEMBER='hfacs/backup.v1.json'
def test_complete_history_multiple_roundtrips_archive_only(tmp_path):
 with client(tmp_path/'source') as c:
  seed(c);digest=None;first_request=None
  for i in range(51):
   b=save_body(digest,i)
   if first_request is None:first_request=b
   doc=save(c,b);digest=doc['digest']
  raw=export(c);files=unzip(raw);backup=json.loads(files[MEMBER])
  assert json.loads(files['manifest.json'])['packageVersion']=='1.1.0'
  assert len(backup['revisionAudit'])==len(backup['requestReceipts'])==51
  assert backup['currentDocument']==doc
 with client(tmp_path/'restored') as c:
  assert intake(c,raw).status_code==200
  result=intake(c,raw,True);assert result.status_code==200,result.text
  assert c.get(endpoint('draft')).json()['document']==doc
  assert c.post(endpoint('save'),json=first_request).status_code==409
  updated=save(c,save_body(digest,52));assert updated['revision']==52
  raw2=export(c);backup2=json.loads(unzip(raw2)[MEMBER])
  assert backup2['revisionAudit'][:51]==backup['revisionAudit']
  old={x['request_id']:x for x in backup['requestReceipts']}
  new={x['request_id']:x for x in backup2['requestReceipts']}
  assert all(new[k]==v for k,v in old.items())
 with client(tmp_path/'restored-again') as c:
  result=intake(c,raw2,True);assert result.status_code==200,result.text
  assert c.get(endpoint('draft')).json()['document']==updated
  assert json.loads(unzip(export(c))[MEMBER])==backup2
