# Independent Skill reference UI review

Scope: frozen extractionWorking/workingArchive parsers and React displays,
plus static inspection of the public UI launcher's new Skill preservation checks.
No product implementation changed by this reviewer. No real model/network call.

Design accepted: execution v1 has exact legacy fields and no inferred Skill;
v2 requires skillRef exactly{id,version,contentDigest}. Structurally valid unknown
historical IDs/versions are inert version declarations, not registry lookups,
installed capabilities, professional certification or permission to execute.
Displays use neutral Skill-version labels rather than infer a role from unknown ID.

Added `web/tests/pi-skill-ui-independent.tsx`:31/31 passed. Covers:
- v1 no synthesized reference; v1+reference and v2 missing/extra/mistyped fields denied.
- unknown valid ID/version preserved, no instruction/URL/tool/authority fields.
- newline/control/URL/type/digest/version bounds denied.
- immutable reference projection and changed reference on reread rejected.
- archive remains untrusted/nonactivated and retains scripted_test origin.
- both HappyDOM views display version metadata and no-execution-authority notice;
  no registry/network fetch, Skill action button or URL link occurs.

Additional reruns: primary Skill26/26; existing Pi working30/30 and archive28/28.
Strict TypeScript for both ports/components passed. These are local synthetic
contract/HappyDOM checks, not real browser, real inference, CI or professional
methodology validation. The launcher assertions preserve skillRef across working
view/remount/export/history and remain read-only with respect to Skill loading.
No new blocker found in this scope. Existing case/source/auth/quote validation
remains the responsibility of the trusted backend and is not conferred by UI metadata.
