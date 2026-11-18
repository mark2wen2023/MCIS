"""Isolated source/AST checks only: never import main or the application package."""
import ast
from pathlib import Path
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "service/mcis_service"

def isolated_handler():
    # Version is read from the code-only initializer as a literal, never imported.
    init = ast.parse((SOURCE / "__init__.py").read_text())
    if len(init.body) != 2 or not isinstance(init.body[0], ast.Expr):
        raise ValueError("initializer shape changed")
    assignment = init.body[1]
    if not isinstance(assignment, ast.Assign) or len(assignment.targets) != 1 or not isinstance(assignment.targets[0], ast.Name) or assignment.targets[0].id != "__version__":
        raise ValueError("version declaration changed")
    version = ast.literal_eval(assignment.value)
    if not isinstance(version, str):
        raise ValueError("version must be literal text")
    source = (SOURCE / "health.py").read_text()
    tree = ast.parse(source)
    expected = ast.parse('''"""Liveness response only; not business readiness, storage or dependency validation."""
from . import __version__
def health():
    return {"status": "ok", "service": "mcis-service", "version": __version__}
''')
    if ast.dump(tree) != ast.dump(expected):
        raise ValueError("unexpected health module dependency or executable statement")
    imports = []
    def only_version(name, globals=None, locals=None, fromlist=(), level=0):
        if (name, fromlist, level) != ("", ("__version__",), 1):
            raise ValueError("unexpected import")
        imports.append("__version__")
        return types.SimpleNamespace(__version__=version)
    namespace = {"__builtins__": {"__import__": only_version}, "__name__": "synthetic.health"}
    exec(compile(tree, "reviewed-health-source", "exec"), namespace)
    return namespace["health"], version, imports

class HealthContract(unittest.TestCase):
    def test_actual_handler_contract(self):
        health, version, imports = isolated_handler()
        self.assertEqual(health(), {"status": "ok", "service": "mcis-service", "version": version})
        self.assertEqual(imports, ["__version__"])
        self.assertEqual(version, "0.1.0")

    def test_response_is_fresh_and_not_readiness(self):
        health, _, _ = isolated_handler()
        first = health()
        first["status"] = "synthetic caller mutation"
        second = health()
        self.assertEqual(second["status"], "ok")
        self.assertEqual(set(second), {"status", "service", "version"})
        self.assertIsNot(first, second)

    def test_main_registration_ast_only(self):
        tree = ast.parse((SOURCE / "main.py").read_text())
        imported = [n for n in tree.body if isinstance(n, ast.ImportFrom) and n.module == "health"]
        self.assertEqual(len(imported), 1)
        self.assertEqual(ast.dump(imported[0]), ast.dump(ast.parse("from .health import health").body[0]))
        factory = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "create_app")
        expected = ast.parse('app.get("/api/v1/health", tags=["meta"])(health)').body[0]
        self.assertEqual(sum(ast.dump(n) == ast.dump(expected) for n in factory.body), 1)
        self.assertFalse(any(isinstance(n, ast.FunctionDef) and n.name == "health" for n in ast.walk(factory)))
        paths = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and n.value == "/api/v1/health"]
        self.assertEqual(paths, ["/api/v1/health"])

if __name__ == "__main__":
    unittest.main()
