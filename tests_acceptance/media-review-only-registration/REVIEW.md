# Private review-only registration — developer evidence

Base `c57d12b1ef694fb44c3b57d185ecbadde1274ab4`; branch `candidate/media-demo-lazy-factory`.

Added unconnected private `_register_image_review_only(app)` and `_register_audio_review_only(app)` in the existing modules. Each uses the existing storage initializer and existing review router/page mount, sets its model runtime to None, and shares the original duplicate-registration flag. No new app factory or default call site. Existing full registration still imports its tasks module, sets the caller runtime, initializes storage, includes review then task router, registers page decorators and sets the completion flag in the same order.

The private mount helpers now omit only the task include when their explicit task argument is None. The limited path retains:
- Image import/list/detail/revision; `/image-review-lab` and its preview.js.
- Audio source/import/list/detail/revision; `/audio-review-lab`.
- Identical media tables and append-only trigger installation; duplicate guard and failure propagation.
- Existing case/role/access/history/receipt checks, and conditional task-backed binding verification. No record acceptance changes.

Checks executed:

```
python tests_acceptance/media-review-only-registration/check.py
```

Both image and audio passed. The test reads only the two named current source files and fixed baseline Git source blobs, parses AST, and executes only extracted registration/storage-initializer function definitions with handwritten fake app/state/metadata/engine/router/decorators/import hooks. Fake execute records SQL strings; it does not execute SQL. Fake task import returns a handmade object; no real task module or endpoint/page callback runs.

The whole module AST equals the baseline after reversing precisely the task-include condition and removing the new private function. Storage initializer source is byte-identical. Exact existing router endpoint sets are checked. Full-path baseline/candidate traces match for normal registration and synthetic import/create_all/begin/enter/execute/include/page-registration failures. Limited traces equal full traces with only task import/include removed, runtime None; initialization and registration failures propagate and never mark completion. Full/limited repeated registration in both orders stops before another setup effect.

These are developer AST and fake-dependency checks, not FastAPI/HTTP/ORM/SQL/permission/model or startup acceptance. No paused tests ran. The actual modules still have transitive DB/authorization/report-access imports. Task-backed records still dynamically import binding checks; absence of task routes does not remove that dependency. Existing task controls remain visible in HTML; this change does not claim a ready limited-mode UX. Downloads remain subject to existing separate intake/artifact routing and guards; no new download endpoint is mounted here.

Remaining before any workspace integration: approved limited app assembly preserving prerequisites and history/access/audit controls; a same-origin serving configuration; continuous explicit identity context (workspace headers versus standalone defaults); guarded same-case run selection; appropriate task-control availability. No capability proof or permission is manufactured by these functions. Existing demo still uses full main.create_app; no activation, merge or deployment occurred.
