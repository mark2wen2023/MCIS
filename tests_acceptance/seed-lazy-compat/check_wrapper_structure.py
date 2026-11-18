"""AST-only wrapper inspection. Does not execute/import the wrapper or any seed."""
import ast
from pathlib import Path
p = Path(__file__).resolve().parents[2] / 'service/mcis_service/colreg/seed_annotations.py'
tree = ast.parse(p.read_text(), filename=str(p))
# Unexpected bare expressions at top-level include the previously broken LILY_MARY_ token.
for i, node in enumerate(tree.body):
    if isinstance(node, ast.Expr):
        if not (i == 0 and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            raise RuntimeError('unexpected top-level expression')
assignments = {n.target.id:n.value for n in tree.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
if 'LILY_MARY_BAND_EVIDENCE' not in assignments:
    raise RuntimeError('original mapping missing')
mapping = assignments['LILY_MARY_BAND_EVIDENCE']
if not isinstance(mapping, ast.Dict) or len(mapping.keys) != 5:
    raise RuntimeError('original mapping structure changed')
functions = {n.name:n for n in tree.body if isinstance(n, ast.FunctionDef)}
body = functions['_load_all_mappings'].body
if len(body) != 1 or not isinstance(body[0], ast.Return) or not isinstance(body[0].value, ast.Dict):
    raise RuntimeError('mapping loader structure changed')
keys = body[0].value.keys
if [k.id if isinstance(k, ast.Name) else None for k in keys] != ['LILY_MARY_CASE','HAILI5_CASE']:
    raise RuntimeError('mapping entries missing')
for node in tree.body:
    if isinstance(node, ast.ImportFrom) and node.module and node.module.endswith(('haili5_seed','lily_mary','yangze22')):
        raise RuntimeError('eager seed import')
print('PASS AST-only wrapper structure; no module execution / seed reading')
