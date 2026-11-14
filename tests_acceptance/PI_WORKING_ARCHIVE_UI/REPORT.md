# Pi historical archive UI (v2)

The existing archive component/port accepts v1 legacy and v2 historical bundles.
Only v2 permits Pi results and optional reviewOrigin. Strict result projection is
shared with extractionWorking.frozenProposal, preserving remote-deepseek and
configured model, original quote/span/claim and restricted protocol events.
An export envelope's format must match its actual bundle payload format.

Pi/model/trace are explicitly historical package declarations, NOT verified
identity or signed audit. Scripted reviews, unverified user submissions and
legacy-unspecified records display separately. The archive component has no
review/fact-activation controls. Context invalidation, unknown import replay,
reauthorized byte-identical download check and no browser storage are unchanged.

Local checks:
- New working-archive-pi.tsx:28 synthetic port/React HappyDOM assertions passed.
- Existing working-archive.tsx:27 assertions passed.
- Existing working-archive-independent.ts:13 assertions passed.
- Strict TypeScript on both archive product files and imported shared parser passed.
- Existing actual React/HappyDOM → stdio Python → temporary SQLite archive
  export/import/list/read/remount passed with current v2 backend. This uses the
  original fictional fixed-output fixture, NOT a real Pi/provider run.

No actual browser file landing, external API, production authentication,
publication, merge or deployment was performed by this UI task. Independent
review is reported separately by the coordinating reviewer.
