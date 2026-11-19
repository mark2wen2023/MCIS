# Shared media demo constants without preparation imports

Base: 585a9c0ffbce68a5a98c9facdfb2c91fd2db2c4a, candidate/media-demo-lazy-factory.

Only change: move existing CID and PUBLIC assignments verbatim from tools/media_review_demo/prepare.py to constants.py; launcher and prepare import those same names from that module. PUBLIC_URL stays in prepare. Shared module has only a docstring and two literal assignments, no imports or I/O. Existing prepare.CID and prepare.PUBLIC names remain available; both modules share the same PUBLIC dictionary, as before. No values, validation rules, CLI, API, generation logic or function body changed.

The removed edge is launch.py → prepare.py for constants. That edge previously also loaded TestClient, PDF and converter dependencies as a side effect of importing preparation. This does not claim all such transitive paths have been removed: launcher still has its other dependencies; explicitly importing or executing prepare still loads preparation dependencies. Factory/main changes from earlier commits remain intact. Default settings, exceptions and route behavior unchanged; no source-policy branch merged.

Development command: `python tests_acceptance/media-demo-shared-constants/check.py` — passed.

Only tracked launcher/prepare/common source parsed as AST; fixed old Git object used as comparison. Original two assignment ASTs and literal values exactly match; complete new prepare AST equals old with those assignments replaced by one import, and complete launcher AST equals old with the single import target changed. Old prepare edge exists, new one absent. Shared module's AST permits only literal assignments/docstring. Only those literals and selected import statements execute with a closed handmade importer, confirming retained names and shared dictionary identity. Neither full launcher nor full prepare executes/imports; no application, third-party imports, sample bytes, seeds, environment values, model, DB/ORM, services, browsers or paused tests.

This is development source/fixture validation, not independent acceptance or a verified runnable isolated environment. Full dependency closure, real runtime compatibility and startup remain unverified and paused. No permission/archive/write tests or deployment.
