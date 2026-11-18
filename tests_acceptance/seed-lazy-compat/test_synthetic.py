"""Only the import-free helper is loaded by exact path; no MCIS package imports."""
import runpy
from pathlib import Path
helper = Path(__file__).resolve().parents[2] / 'service/mcis_service/common/lazy_exports.py'
LazyExports = runpy.run_path(str(helper))['LazyExports']
# Entirely handmade stand-in namespace and loaders, never actual seed modules.
namespace = {}; calls = []; real = {'synthetic-band': ['synthetic-evidence']}
def load_alias():
    calls.append('alias')
    return real
def load_all():
    calls.append('all')
    return {'SYNTHETIC': exports.get('ALIAS')}
exports = LazyExports(namespace, {'ALIAS': load_alias, 'ALL': load_all})
assert calls == []
assert exports.get('ALL')['SYNTHETIC'] is exports.get('ALIAS') is real
assert calls == ['all', 'alias']
assert exports.get('ALL') is namespace['ALL']
namespace['ALL']['SYNTHETIC'] = {'replacement': ['synthetic-new']}
def annotations(case):
    return {k:list(v) for k,v in exports.get('ALL').get(case, {}).items()}
a = annotations('SYNTHETIC'); a['replacement'].append('local')
assert annotations('SYNTHETIC') == {'replacement':['synthetic-new']}
namespace['ALL'] = {'OTHER': {'x':['y']}}
assert annotations('SYNTHETIC') == {} and annotations('OTHER') == {'x':['y']}
other = {'ALIAS': {'override': []}}
second = LazyExports(other, {'ALIAS': lambda: (_ for _ in ()).throw(RuntimeError('not used'))})
assert second.get('ALIAS') is other['ALIAS']
assert calls == ['all','alias']
print('PASS synthetic lazy cache, alias identity, mapping overrides and copy behavior; no application imports')
