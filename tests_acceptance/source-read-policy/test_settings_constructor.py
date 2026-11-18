"""Compile only Settings class AST; fabricated environment and roots, no app imports."""
import ast
from dataclasses import dataclass, field, fields
from pathlib import Path
from types import SimpleNamespace
source = Path(__file__).resolve().parents[2] / 'service/mcis_service/config.py'
tree = ast.parse(source.read_text(), filename=str(source))
cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Settings')
# No top-level config imports/initializers are executed; defaults use an empty fake env.
namespace = {'__name__': '__main__', 'dataclass': dataclass, 'field': field, 'Path': Path,
             'os': SimpleNamespace(environ={}), 'SERVICE_ROOT': Path('/synthetic/service'),
             'PROJECT_ROOT': Path('/synthetic')}
exec(compile(ast.Module(body=[cls], type_ignores=[]), '<synthetic-settings-class>', 'exec'), namespace)
Settings = namespace['Settings']
old_names = ['data_dir','db_url','seed_demo','core_cmd','core_timeout_s','host','port']
values = [Path('/synthetic/case'), 'sqlite:///synthetic.db', False, 'synthetic-core', 12.5, '127.0.0.1', 9876]
s = Settings(*values)
assert [getattr(s, name) for name in old_names] == values
assert [f.name for f in fields(Settings)][:7] == old_names
assert s.allow_analysis_seed_reads is False and s.allow_public_report_reads is False
for count in range(8):
    partial = Settings(*values[:count])
    assert [getattr(partial, name) for name in old_names[:count]] == values[:count]
s = Settings(*values, allow_analysis_seed_reads=True, allow_public_report_reads=False)
assert s.allow_analysis_seed_reads is True and s.allow_public_report_reads is False
assert [getattr(s, name) for name in old_names] == values
# No ambient environment reads: seed population still defaults on under empty config.
default = Settings()
assert default.seed_demo is True
assert default.allow_analysis_seed_reads is False and default.allow_public_report_reads is False
namespace['os'].environ['MCIS_SEED_DEMO'] = '0'
assert Settings().seed_demo is False
print('PASS Settings class synthetic construction: legacy positional prefixes, explicit policies, seed default')
