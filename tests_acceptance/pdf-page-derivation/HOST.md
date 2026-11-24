# Local synthetic PDF/controller handoff

Fixed parent/input `955785e6055d26aadb0dc98f5e504bbb3a1d2364`. No existing production or acceptance file is changed. New files: `controller_host.py`, `controller_consumer.cjs`, this document.

```sh
/path/to/existing/venv/bin/python -I -B tests_acceptance/pdf-page-derivation/controller_host.py
```

Use the existing environment requirements from README.md plus Node with WebCrypto. Linux developer command used `/workspace/mcis/service/.venv/bin/python`; keep the lexical venv path. No installation, browser, network, HTTP listener, default app/seed, model or OCR. Existing Git objects and four unchanged pinned files are required, verified against fixed Git bytes and explicit SHA256. The original allowlisted materializer remains unchanged; lazy fetch is disabled.

The host runs the existing one-case temporary SQLite PDF test exactly once. It uses the same real handlers for source registration and authorized original read, the same real Poppler renderer and Pillow crop checks. A transparent acceptance-side observer forwards `render` calls unchanged and captures only successful return values. It does not replace production methods, authorization or database rows. The original fixture asserts one Access, matching original bytes and audit chains, then removes its temporary database. There is no second original read. This is explicit synthetic context, not a real login.

Only the two observed PNG/description pairs are sent to a local Node child through stdin. No original PDF, registration ID, request digest, credentials or database is sent or saved. The fixed runner and local observer are the trust boundary; hashes are not authorization or proof against an arbitrary forged host. The receiver is not a network/input endpoint and must not be treated as a production authority.

The receiver calls the **actual unchanged production** `OcrPagePreview.create` / `loadDerived` / `select` / `clear`. It verifies two distinct page digests, physical-page labels, derived region labels, supplied operation-control disable/restore, and a changed in-memory PNG rejected without another draw. No disk original is modified. The controller uses real WebCrypto. Its canvas and bitmap decoder use the existing style of synthetic spy, not a browser: actual PNG decoding was exercised by the Python/Pillow fixture, while this receiver proves the byte/description handoff and controller calls. The controller's context crop includes a 12px margin (88×88 for a 64×64 region), distinct from the exact Python crop.

Linux result: exit 0, one original integrated registration test, two pages accepted by controller, one changed-byte negative, one total Access, zero observer Access. These are stages of a single test execution, not an aggregate count of independent end-to-end passes. Only a finite receipt is printed; source/page bytes remain ephemeral. Consumer failures suppress its raw output.

No product host/mount, real DOM, browser/pixels/accessibility, production authorization, OCR, report, persisted derivative binding or archive is verified. This candidate does not enable the existing HTML's derived mode. No route, schema, permission or official verified flag changes. Publication and deployment are separate from this local run.
