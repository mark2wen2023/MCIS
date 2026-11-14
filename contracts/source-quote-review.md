# Read-only source quote review UI

Scope: shared component used by extractionWorking and workingArchive only. No RPC, approval, business field, storage or routing changes. No model request or automated semantic verdict.

The supplied quote string must remain byte-for-string identical in React text: no trim, normalization, inferred qualifier, filler or whitespace restoration. Render blockquote with white-space: pre-wrap. This preserves supplied text spacing, not original PDF table/page geometry.

Separate original quote from AI summary and structured claim. Always show a short manual check reminder: preserve qualifiers such as approximate/at least/unknown; missing/blank information proves neither presence nor absence; check original page and other evidence. Quote location/exact matching does not establish semantic support. Historical quotes remain unverified archive declarations. No success mark or automatic omission detection.

Acceptance: exact textContent including leading/trailing spaces, tabs, CR/LF and repeated spaces; pre-wrap style; malicious-looking HTML remains text; empty quote not auto-filled; shared component integrated twice; historical warning preserved; strict TypeScript and prior Pi UI tests. HappyDOM is not browser/PDF visual reconstruction validation.
