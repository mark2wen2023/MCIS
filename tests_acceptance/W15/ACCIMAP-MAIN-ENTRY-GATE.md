# W15 AcciMap main-entry acceptance gate

Status: handoff for a future reviewed integration, not a route, API, or completed product feature.
Audited product candidate: `2447b14076bbf39db014b8bf4a3a3b350cbf0e05`.
Existing component-only Chromium receipt: `fe01c6680a8fd4a7dbd9f21e371a14ed0926aeae` (desktop 1440×900 and 390×844). Reuse the verified keyboard behavior, not the isolated test page as evidence of integration.

## What can be reused

- `web/src/pages/SystemicPage.tsx` owns the current case and identity lifecycle, but currently mounts Bow-tie only. Use this case-scoped entry after a suitable AcciMap reader is identified. Do not fetch AcciMap through the Bow-tie endpoint or reinterpret Bow-tie source data.
- `web/src/accimapPreview/Diagram.tsx` is a synthetic-only renderer. Its case/fixture check is not authorization. Do not re-label a persisted or real draft as fictional to pass it.
- `unity/Assets/_Project/Scripts/Domain/Systemic/SystemicDocument.cs` shows the legacy archive shape. Serialization and core validation are not evidence of a current, permission-filtered Web draft. Do not mine an archive or expose a generic download to populate the preview.

## Stop before wiring until the input is established

Identify the authorized producer and an existing or separately approved reader. State how it proves the current case, draft ID, immutable revision, and current source-read permissions, and where human review state originates. No reader has been established in this candidate. Do not create a new transport contract, default demo fallback, or persistence. An unavailable reader is a blocker, not an empty approved diagram.

## Run these cases through the real entry after integration

| Check | Expected |
| --- | --- |
| Current authorized synthetic draft | Shows the current revision only; nodes visibly remain draft/unknown unless an approved workflow supplies another state. Directed edges and information flows stay distinguishable. No facts, causal conclusions, or new edges are inferred. |
| Missing draft, malformed linkage or incorrect case/revision | No old diagram, evidence reference or auto-generated graph; UI reports unavailable or invalid. |
| Case/identity/revision switch during a delayed read | Old response cannot repopulate the diagram, URL, or linked evidence after the switch. |
| Read permission changes before display or refresh | No prior graph or source labels survive the denial. No hidden raw source payload is required by the renderer. |
| Desktop and 390×844, in the actual system-analysis route | Tab exposes a visible figure focus. Arrow keys pan the figure only. Open the full text list with keyboard; measure whole-page overflow again after disclosure and check complete six-layer labels. |
| No mutation | App/browser receipt shows no save, archive write, export, role elevation, or cross-case fetch for this workflow. |

Use synthetic fixtures and a loopback app in sandboxed Chromium. Preserve actual product and fixture SHAs, viewport, read effects, screenshots, assertions and unverified checks. Keep this gate separate from W15 package completion and from W4/W21.
