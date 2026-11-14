# Strict final presentation equivalence · 2026-11-14

Only JSON presentation may vary: object key ordering, insignificant JSON whitespace,
and equivalent JSON string escapes. A bounded recursive parser rejects duplicate
decoded keys (including nested duplicates), invalid/trailing JSON and over64 depth
or64KiB. Strings compare exact decoded code units (no trim/normalization); arrays
retain order; types differ. Number lexemes remain exact, so1,1.0,1e0 and negative
zero differ even when JS numbers could conflate them. No lossy large-number parse.

After strict equivalence only, Node forwards the **original validated string**
to Python. Python's exact validated-byte check, canonical messages/call IDs,
source/auth/citation validation and PendingReview/saved=false boundary remain
unchanged. This does not correct evidence or accept new fields/content. The
older diagnostic classifier continues to label formatting for historical failure
diagnosis; those labels alone no longer decide final acceptance.

Independent actual Pi fixture-loop check confirms original validated bytes reach
host, while changed strings/number tokens/duplicates/arrays/extras fail closed.
Final npm test78/78 zero skipped (includes earlier60 plus18 equivalence tests).
Independent equivalence+diagnostic38/38 overlaps this78. Python remote63/63 from
prior unchanged-host rerun. These are local tests, not CI or real-model proof.

## Separate live acceptance
New run be93095b-c8be-47e1-9579-f2a3788a23aa completed accepted_pending_review:
4 real DeepSeek rounds through actual Pi,3 tools,7 proposals/7 citations,
saved=false. Only the pinned public excerpt was supplied. The host received
original validated text, not canonical reserialization. No facts approved,
production persistence, UI/browser, CI, deployment or full-case accuracy claim.

## Important end-to-end qualification
The Python remote host still requires payload == terminal model text == validated
candidate text. Therefore the live success proves an exact-byte final path;
it does NOT prove whitespace-different final text is accepted end-to-end.
The Node equivalence tests cover only the Node boundary; the Python gate remains
strict and may reject presentation differences. No claim of server relaxation.
