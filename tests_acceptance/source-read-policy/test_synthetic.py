"""Only import-free policy helper is executed; no application imports or seed files."""
import runpy
from pathlib import Path
m = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'service/mcis_service/common/source_policy.py'))
Policy, Disabled = m['SourceReadPolicy'], m['SourceDisabled']
a, p = m['read_analysis'], m['read_public_report']
for av,pv in [(False,False),(True,False),(False,True),(True,True)]:
    policy = Policy(av,pv); calls=[]
    for enabled, invoke, label in [(av,a,'analysis'),(pv,p,'public')]:
        def loader(*args, **kwargs):
            calls.append(label); return (args,kwargs)
        try:
            value=invoke(policy, loader, 'synthetic', option='synthetic')
        except Disabled:
            assert not enabled
        else:
            assert enabled and value == (('synthetic',),{'option':'synthetic'})
    assert calls == (['analysis'] if av else []) + (['public'] if pv else [])
# Independent policy instances; an enabled instance does not open another instance.
closed,opened=Policy(),Policy(True,True)
assert a(opened,lambda:'synthetic-result') == 'synthetic-result'
for invalid in [closed,None,{'analysis_seed':True},object()]:
    calls=[]
    try:a(invalid,lambda:calls.append('called'))
    except Disabled:pass
    else:raise AssertionError('disabled policy accepted')
    assert calls == []
# Read failures are distinct from Disabled; not converted to a fake empty result.
class SyntheticReadFailure(Exception):pass
def failure():raise SyntheticReadFailure('synthetic failure')
for invoke in [a,p]:
    try:invoke(opened,failure)
    except SyntheticReadFailure:pass
    else:raise AssertionError('failure swallowed')
# Legacy two-argument adapter shape is preserved by the guarded callback.
assert a(opened,lambda: (lambda session,case:(session,case))('fake-session',{'caseId':'SYNTHETIC'})) == ('fake-session',{'caseId':'SYNTHETIC'})
assert closed == (False,False) and opened == (True,True)
print('PASS fabricated policy matrix, independent instances, zero disabled callbacks, failure distinction and adapter shape')
