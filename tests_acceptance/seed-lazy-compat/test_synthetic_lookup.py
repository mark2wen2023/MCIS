"""Exact import-free helper only; all namespaces/loaders/data below are fabricated."""
import runpy
from pathlib import Path
LazyExports = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'service/mcis_service/common/lazy_exports.py'))['LazyExports']
def fixture():
    ns = {}; calls = []; fictional = {'f':['synthetic-fiction']}; real = {'r':['synthetic-real-stand-in']}
    def real_loader():
        calls.append('real'); return real
    exports = LazyExports(ns, {'REAL':real_loader})
    def all_loader():
        calls.append('all'); return {'FICTION':fictional, 'REAL-ID':exports.get('REAL')}
    exports.loaders['ALL'] = all_loader
    loaders = {'FICTION':lambda:fictional, 'REAL-ID':lambda:exports.get('REAL')}
    def read(key):
        return {k:list(v) for k,v in exports.get_item('ALL', key, loaders).items()}
    return ns, calls, exports, loaders, read
# Demonstrate prior algorithm materializes the synthetic real loader for unknown ID.
ns,calls,e,loaders,read = fixture()
assert e.get('ALL').get('UNKNOWN', {}) == {}
assert calls == ['all','real']
# New algorithm: unknown and fictional paths cannot call full/real loaders.
ns,calls,e,loaders,read = fixture()
assert read('UNKNOWN') == {}
assert read('FICTION') == {'f':['synthetic-fiction']}
assert calls == [] and 'ALL' not in ns and 'REAL' not in ns
copy = read('FICTION'); copy['f'].append('local')
assert read('FICTION') == {'f':['synthetic-fiction']}
assert read('REAL-ID') == {'r':['synthetic-real-stand-in']}
assert calls == ['real'] and 'ALL' not in ns
assert read('REAL-ID') == {'r':['synthetic-real-stand-in']} and calls == ['real']
full = e.get('ALL'); assert calls == ['real','all']
assert full['REAL-ID'] is ns['REAL']
del full['REAL-ID']; del full['FICTION']
assert read('REAL-ID') == {} and read('FICTION') == {}  # no resurrection
full['UNKNOWN'] = {'override':['value']}
assert read('UNKNOWN') == {'override':['value']}
ns['ALL'] = {}; assert read('REAL-ID') == {} and calls == ['real','all']
ns['ALL'] = {'FICTION':{'replaced':['x']}}
assert read('FICTION') == {'replaced':['x']}
assert calls == ['real','all']
# A preinstalled complete mapping, including empty, always takes priority.
ns,calls,e,loaders,read = fixture(); ns['ALL'] = {}
assert read('REAL-ID') == {} and calls == []
# If the item loader explicitly installs a complete map, honor that after loading.
ns = {}; e = LazyExports(ns,{})
def install():
    ns['ALL'] = {}; return {'must-not-win':[]}
assert e.get_item('ALL','KEY',{'KEY':install}) == {}
print('PASS fabricated lookup paths, override/deletion precedence, alias cache and copied values; no seed imports')
