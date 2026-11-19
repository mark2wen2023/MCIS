"""Full factory source executed only with a closed, entirely handmade importer.
No actual package imports, application, ORM, files/data or external dependencies.
"""
import ast
from pathlib import Path
import subprocess
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
PATH = 'service/mcis_service/media_review_demo.py'
BASE = '76d6c22c474172a28f7b2da9ae45021e8d573b82'
old = subprocess.run(['/usr/bin/git','-C',str(ROOT),'show',BASE+':'+PATH],
                     env={'PATH':'/usr/bin:/bin','GIT_NO_LAZY_FETCH':'1',
                          'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null'},
                     check=True,capture_output=True).stdout.decode()
new = (ROOT/PATH).read_text()


def exercise(source):
    events = []
    settings, app = object(), object()
    def create(received):
        assert received is settings
        events.append('create')
        return app
    def image(received):
        assert received is app
        events.append('image')
    def audio(received):
        assert received is app
        events.append('audio')
    dependencies = {
        'main': SimpleNamespace(create_app=create),
        'image_review.app': SimpleNamespace(register_image_review=image),
        'audio_review.app': SimpleNamespace(register_audio_review=audio),
    }
    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level != 1 or name not in dependencies:
            raise AssertionError('unexpected import in synthetic harness')
        events.append('import:'+name)
        return dependencies[name]
    namespace = {'__builtins__':{'__import__':fake_import}, '__name__':'synthetic_factory'}
    exec(compile(source, '<factory source with fake importer only>', 'exec'), namespace)
    before = list(events)
    assert namespace['create_media_review_demo'](settings) is app
    return before, events


expected_imports = ['import:main','import:image_review.app','import:audio_review.app']
old_before, old_all = exercise(old)
new_before, new_all = exercise(new)
# Old source is a concrete counterexample to the no-dependency-at-definition rule.
assert old_before == expected_imports and old_before != []
assert new_before == []
assert old_all == new_all == expected_imports + ['create','image','audio']
# Verify unchanged ordinary function operations, without executing real imports.
old_tree, new_tree = ast.parse(old), ast.parse(new)
old_func = next(n for n in old_tree.body if isinstance(n,ast.FunctionDef))
new_func = next(n for n in new_tree.body if isinstance(n,ast.FunctionDef))
assert ast.dump(old_func.args) == ast.dump(new_func.args)
assert [ast.dump(n) for n in old_func.body] == [ast.dump(n) for n in new_func.body if not isinstance(n,ast.ImportFrom)]
assert not any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in new_tree.body)
assert not any(isinstance(n,(ast.Try,ast.TryStar)) for n in ast.walk(new_tree))
print('PASS old counterexample: 3 eager fake imports; candidate definition: 0')
print('PASS identical explicit-call import/create/register order, settings and returned object')
print('PASS unchanged signature/ordinary body, no exception suppression; AST/fakes only, not startup isolation')
