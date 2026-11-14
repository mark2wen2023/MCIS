# Intranet metadata / case query plan v1

Isolated internal API: `mcis_service.intranet_plan.build_plan(document)` and offline CLI
`cd service && .venv/bin/python -m mcis_service.intranet_plan < request.json`.
This is a proposal/metadata tool, not a connector or production configuration endpoint.

Input is exactly `{sources: [...], case: {...}}`. Maximum UTF-8 CLI input 64 KiB,
32 sources, 16 explicitly identified vessels. Duplicate JSON keys, unknown fields,
wrong types and excessive nesting fail closed. CLI errors contain only fixed codes,
never input or exception details (exit 4). No automatic persistence or logging.
Callers can save only successfully validated documents; invalid input is never exported.

Each source is exactly `{id, category, transport, endpointRef?, credentialRef?, maxWindowDays?}`.
`id`: ASCII letter followed by up to 63 ASCII alphanumerics/underscore/hyphen.
category: `ship_parameters`, `ais`, `company`, `regulatory`; transport: `api`, `mcp`.
endpointRef: `endpoint:<identifier>`; credentialRef: `credential:<identifier>`.
These are opaque configuration identifiers, never URLs, headers, tokens, shell commands,
environment-variable lookups or secret values. Credential reference is optional (auth
requirements are unknown); endpointRef absent/null means `unconfigured`; supplied valid
reference means `configured_unverified` (已配置但未验证连通). No `connected` state.
Invalid metadata yields `validation_failed` and no plan/configuration echo. Unknown fields,
including password/apiKey/token/headers/url, are rejected. As with every metadata system,
operators must never intentionally put secret material in identifier fields.
maxWindowDays is an integer 1..366, default 31, a local planning limit only.

case fields: `caseId`, `vessels`, `startUtc`, `endUtc`, all optional or null.
caseId is an ASCII letter/digit followed by up to 127 ASCII alphanumerics/_/./-.
vessels is a list of exact `{kind,value}` objects: IMO (7 digits, checksum valid)
or MMSI (9 digits, nonzero). They are caller-supplied identifiers, not identity verification.
No name, inferred alias, wildcard, coordinates, arbitrary filter or executable operation.
Timestamps must be ISO 8601 with explicit timezone and normalize to UTC; no naive dates.
Missing or empty vessel list, absent/null/blank case ID or timestamps are listed as
`pendingFields`; malformed supplied values fail validation. start must precede end.
Each source gets one read-only query intent preserving all vessel identifiers, case ID,
and normalized time boundaries. Source windows over maxWindowDays are `range_exceeded`;
missing fields are `pending_input`; unconfigured sources `blocked_unconfigured`;
otherwise `planned_unverified`. All intents remain `executable:false`; no pagination,
MCP tool invocation, collection, remote verification or fact activation is implemented.
No sources means no intents and an explicit `sources` pending field. Categories without
registered sources are returned as `unconfiguredCategories`, never silently substituted.

Integration: future authenticated settings UI may roundtrip these validated metadata
records; case creation must explicitly supply existing case ID and verified vessel IDs,
not guess mappings from existing free-text ship names. Future adapters must independently
resolve references, enforce per-case authorization and remote range limits, and obtain
network authorization. Existing service config.py/main.py, DB and UI remain unchanged.
