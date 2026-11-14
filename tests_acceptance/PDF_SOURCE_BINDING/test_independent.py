"""Independent pure-contract checks; no authenticity or database claims."""
from copy import deepcopy
import pytest
from binding import build, validate, BindingError, digest, canonical
from test_binding import fixture

@pytest.mark.parametrize('field',['version'])
def test_boolean_outer_version_cannot_equal_integer(field):
    pdf,s,d=fixture();a=build(s,pdf,d);a[field]=True
    with pytest.raises(BindingError):validate(a,s,pdf)

@pytest.mark.parametrize('field',['physicalPage','byteLength'])
def test_artifact_numeric_type_not_equal_float(field):
    pdf,s,d=fixture();a=build(s,pdf,d)
    a['derivative']['pages'][0][field]=float(a['derivative']['pages'][0][field])
    with pytest.raises(BindingError):validate(a,s,pdf)

@pytest.mark.parametrize('place',['source','derivative','page'])
def test_extra_change_fields_not_accepted(place):
    pdf,s,d=fixture()
    target={'source':s,'derivative':d,'page':d['pages'][0]}[place]
    target['Change']={'replaceSource':True}
    with pytest.raises(BindingError):build(s,pdf,d)


def test_postbuild_input_mutation_cannot_rewrite_artifact():
    pdf,s,d=fixture();a=build(s,pdf,d);old=deepcopy(a)
    s['evidenceId']='new';d['pages'][0]['text']='changed';d['warnings'].append('x')
    assert a==old


def test_rehashed_body_with_old_derivative_digest_rejected():
    pdf,s,d=fixture();a=build(s,pdf,d)
    a['derivative']['warnings']=['different disclaimer']
    a['artifactSha256']=digest(canonical({k:v for k,v in a.items() if k!='artifactSha256'}))
    with pytest.raises(BindingError):validate(a,s,pdf)


def test_valid_unicode_bytes_not_character_count():
    pdf,s,d=fixture();p=d['pages'][0]
    p['byteLength']=len(p['text'])
    with pytest.raises(BindingError):build(s,pdf,d)


def test_surrogate_json_rejected():
    pdf,s,d=fixture();d['pages'][0]['text']='\ud800'
    with pytest.raises(BindingError):build(s,pdf,d)


def test_object_key_order_not_meaningful_but_registered_hash_is():
    pdf,s,d=fixture();a=build(s,pdf,d)
    assert validate(dict(reversed(list(a.items()))),dict(reversed(list(s.items()))),pdf)
    s['registeredSha256']='f'*64
    with pytest.raises(BindingError):validate(a,s,pdf)


def test_self_consistent_new_text_not_authenticated_extraction():
    # Explicit limitation: a binder checks hashes, not whether PDF actually says it.
    pdf,s,d=fixture();p=d['pages'][0];p['text']='synthetic replacement'
    raw=p['text'].encode();p['textSha256']=digest(raw);p['byteLength']=len(raw)
    a=build(s,pdf,d)
    assert validate(a,s,pdf)
    assert any('not source authenticity' in x for x in a['limitations'])
