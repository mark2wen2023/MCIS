# Internal PDF derivative/source binding contract

Pure functions only; no database, route, file write, custody operation or model invocation. `build` receives caller-authorized immutable PDF bytes, explicit source identity/version declarations, and a completed digital text-layer artifact. It verifies current source byte SHA, page order/count/text SHA, tool/method fields, then computes independent derivative-content and whole binding hashes. Registered source hash may differ from current source hash; neither is overwritten with text SHA.

The whole-binding hash uses precisely defined UTF-8 sorted-key compact JSON serialization with no NaN. The artifact hash covers all fields except itself; derivativeContentSha256 covers the derivative object including tool/parameters/page hashes. These detect consistency only, not tamper-proof signatures, real evidence authenticity, trusted operator identity or policy approval. A caller who can construct new inputs can compute new hashes. `validate` must receive current trusted source binding from the host, never trust the artifact's own case/evidence/sourceStateDigest as authorization.

No Custody Change is emitted or accepted in the artifact. Source mutations are rejected relative to the host-supplied binding. This pure contract cannot forbid a separate production caller from misusing custody APIs; formal integration must explicitly test no Change/Verify/source-row writes. No such production wiring exists here.

Physical page and exact text bytes remain separate from printed page numbering, OCR and image understanding. Original PDF bytes remain unchanged. All identity fields in tests are synthetic, including the offline public report test IDs/sourceStateDigest; the PDF itself is the verified official public report. No true cases or production tables are accessed.

Run `../mcis-work/service/.venv/bin/python -m pytest -q` in this folder. Public-PDF integration uses the local internal deriver and existing official.pdf snapshot. No remote updates or API exposure. Parser CPU/RSS/escaped-group/env limitations from the deriver still apply; this binding layer adds no sandbox.
