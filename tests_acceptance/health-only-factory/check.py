"""Fixed-source AST plus handmade collector; no FastAPI import, HTTP or app startup."""
import ast
from pathlib import Path
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "service/mcis_service"
EXPECTED = '''
from fastapi import FastAPI
from .health import health
def create_health_app():
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None,
                  swagger_ui_oauth2_redirect_url=None)
    app.get("/api/v1/health", tags=["meta"])(health)
    return app
'''

def checked_tree():
    tree = ast.parse((SOURCE / "health_app.py").read_text())
    if not (isinstance(tree.body[0], ast.Expr) and
            isinstance(tree.body[0].value, ast.Constant) and
            isinstance(tree.body[0].value.value, str)):
        raise ValueError("expected module docstring")
    body = ast.Module(body=tree.body[1:], type_ignores=[])
    if ast.dump(body) != ast.dump(ast.parse(EXPECTED)):
        raise ValueError("factory structure changed; review before execution")
    return tree

def harness():
    # Actual handler source, with only literal-version dependency supplied in memory.
    version_tree = ast.parse((SOURCE / "__init__.py").read_text())
    if len(version_tree.body) != 2:
        raise ValueError("initializer changed")
    version_assignment = version_tree.body[1]
    if ast.dump(version_assignment) != ast.dump(ast.parse('__version__ = "0.1.0"').body[0]):
        raise ValueError("literal version changed")
    version = ast.literal_eval(version_assignment.value)
    handler_tree = ast.parse((SOURCE / "health.py").read_text())
    expected_handler = ast.parse('''"""Liveness response only; not business readiness, storage or dependency validation."""
from . import __version__
def health():
    return {"status": "ok", "service": "mcis-service", "version": __version__}
''')
    if ast.dump(handler_tree) != ast.dump(expected_handler):
        raise ValueError("handler dependency shape changed")
    calls = []
    class Collector:
        def __init__(self, **kwargs):
            self.options = kwargs
            self.routes = []
            calls.append(self)
        def get(self, path, **kwargs):
            def register(handler):
                self.routes.append(("GET", path, kwargs, handler))
                return handler
            return register
    def version_import(name, globals=None, locals=None, fromlist=(), level=0):
        if (name, fromlist, level) != ("", ("__version__",), 1):
            raise ValueError("unexpected handler import")
        return types.SimpleNamespace(__version__=version)
    handler_ns = {"__builtins__": {"__import__": version_import}}
    exec(compile(handler_tree, "reviewed-handler", "exec"), handler_ns)
    handler = handler_ns["health"]
    imports = []
    def factory_import(name, globals=None, locals=None, fromlist=(), level=0):
        imports.append((name, fromlist, level))
        if (name, fromlist, level) == ("fastapi", ("FastAPI",), 0):
            return types.SimpleNamespace(FastAPI=Collector)
        if (name, fromlist, level) == ("health", ("health",), 1):
            return types.SimpleNamespace(health=handler)
        raise ValueError("unexpected factory import")
    namespace = {"__builtins__": {"__import__": factory_import}}
    exec(compile(checked_tree(), "reviewed-factory-with-synthetic-imports", "exec"), namespace)
    return namespace["create_health_app"], handler, calls, imports

class FactoryContract(unittest.TestCase):
    def test_definition_does_not_construct_app(self):
        _, _, calls, imports = harness()
        self.assertEqual(calls, [])
        self.assertEqual(imports, [("fastapi", ("FastAPI",), 0), ("health", ("health",), 1)])

    def test_only_expected_route_and_docs_disabled(self):
        factory, handler, calls, _ = harness()
        collector = factory()  # Handmade collector, never actual FastAPI.
        self.assertEqual(calls, [collector])
        self.assertEqual(collector.options, {
            "docs_url": None, "redoc_url": None, "openapi_url": None,
            "swagger_ui_oauth2_redirect_url": None})
        self.assertEqual(collector.routes, [("GET", "/api/v1/health", {"tags": ["meta"]}, handler)])
        self.assertIs(collector.routes[0][3], handler)
        self.assertEqual(handler(), {"status": "ok", "service": "mcis-service", "version": "0.1.0"})

    def test_each_call_has_separate_collector(self):
        factory, handler, calls, _ = harness()
        a, b = factory(), factory()
        self.assertIsNot(a, b)
        self.assertEqual(len(calls), 2)
        self.assertIs(a.routes[0][3], handler)
        self.assertIs(b.routes[0][3], handler)
        a.routes.clear()
        self.assertEqual(len(b.routes), 1)

if __name__ == "__main__":
    unittest.main()
