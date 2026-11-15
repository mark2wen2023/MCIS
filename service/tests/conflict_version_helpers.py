"""Fresh-version helper for tests of non-concurrency behavior; never a client retry."""
from .test_working_record_archive import checked as request,ROOT,HEAD


def checked(c,method,url,body=None,status=200,headers=HEAD):
    if body is not None and (method=='patch' and '/conflicts/' in url or method=='post' and url.endswith('/conflicts')):
        listing=request(c,'get',ROOT+'/conflicts:editable',headers=headers).json()
        key=url.rsplit('/',1)[-1] if method=='patch' else body.get('conflictId')
        row=next((row for row in listing if row['conflict']['conflictId']==key),None)
        if row:body={**body,'expectedVersion':row['version']}
    return request(c,method,url,body,status,headers)
