# Official PyPI base-wheel metadata — not execution approval

Checked 2026-11-19, using only HTTPS pypi.org per-version JSON. No wheel bytes
were downloaded, installed, imported or executed. Exact sources and official file URLs,
SHA-256, sizes, Requires-Python, active dependencies and excluded markers are recorded
in official-pypi-base-wheels.json. All 11 selected files are non-yanked.

Target: CPython 3.12.14, Linux x86_64, glibc >=2.17 (observed glibc 2.41).
This is not a musl/Alpine or other architecture list. Ten wheels are py3-none-any;
pydantic_core is cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.

| Distribution | Version | Selected wheel | Official SHA-256 |
|---|---|---|---|
| fastapi | 0.162.7 | fastapi-0.162.7-py3-none-any.whl | fa3be857122ec8d91d4d234e86ac19acf4ef23f5c6c3dfcce78ec0c27c0c5ab4 |
| starlette | 1.10.0 | starlette-1.10.0-py3-none-any.whl | 478c0ab3b4ced6e82719849c118fa406f0278a3499c1a898cd15cd31bdc38ce4 |
| pydantic | 2.14.3 | pydantic-2.14.3-py3-none-any.whl | 3f7b347782ab7e4cf4c798496ae3a82787d9f21ec12676a9c564355eeef8daa8 |
| pydantic_core | 2.50.4 | pydantic_core-2.50.4-cp312-cp312-manylinux2014_x86_64.manylinux_2_17_x86_64.whl | c81d98e27d9d9261909dcccab1ba5d6ea1c98b0bb9470e368604614fd1d36ddd |
| anyio | 4.16.0 | anyio-4.16.0-py3-none-any.whl | c66ae634e0b8228396b801741beb3294326d4b6102f7bba4041c0dfb58c29026 |
| typing-extensions | 4.16.0 | typing_extensions-4.16.0-py3-none-any.whl | 481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8 |
| typing-inspection | 0.4.5 | typing_inspection-0.4.5-py3-none-any.whl | bc210535442b39e1bf2805e0c7a17dfd6a4ace760c84c7f7d16245d23a6b1c39 |
| annotated-types | 0.8.0 | annotated_types-0.8.0-py3-none-any.whl | f072f4d804ea359e4eaf198b1af7a8b0943881a87f31bb764f8bf219bb9419e0 |
| annotated-doc | 0.0.6 | annotated_doc-0.0.6-py3-none-any.whl | 361ca0950cc7082f53fa69e9328409f40a62c61e57e0a47e1825a08078a58a53 |
| idna | 3.20 | idna-3.20-py3-none-any.whl | ab7ae7122974553370f0bdb919e1a960b2cd1bc1ef0276416d896db81c14582c |
| opentelemetry-api | 1.45.2 | opentelemetry_api-1.45.2-py3-none-any.whl | 2cbd737377e710ee740d261c94e93fa0f08e6d037c18f17513cc0a2d94479a34 |

Base closure was checked against all official Requires-Dist entries: no extras selected;
Python <3.13/<3.15 markers apply, <3.11 does not. Exact selected versions satisfy active
constraints, including pydantic-core==2.50.4. No dependency versions were silently upgraded.
Official metadata matches the versions previously observed locally; this DOES NOT prove
that local installations match official wheel bytes or are safe to import.

## Separate future HTTP acceptance dependencies
This list covers framework construction/health handler dependencies only. No HTTP test
or listener was approved/executed. HTTP client/TestClient (httpx vs httpx2), its transitive
requirements, an optional test runner, and an ASGI server if needed require separately
chosen exact versions and official verification. They are deliberately not represented
as a completed lock here. FastAPI standard/all extras are not enabled merely to obtain them.

## Remaining gates
Verify downloaded bytes against these official digests if downloads are later authorized;
review wheel contents and installed payload; freeze interpreter/stdlib/native libraries
and import paths; preserve the three-file source allowlist; independently review actual
framework route construction before any HTTP. This is a pure base artifact selection,
not a runnable MCIS package, pip install command, full runtime lock or permission to start.
No backend, cases, models, credentials, paused tests, main changes or deployment.
