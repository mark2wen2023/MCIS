# W20 Python projection to React synthetic acceptance
Parent: 660eb9940174143e006c0d99e2609d2c0d114932. Presenter now also compares held/current full-source digests.
Actual projector: 28594e2e37484824ddce4aff9711df45845edb60.
Changes are the isolated presenter, its tests and this cross-language harness; no product/default wiring.

From this candidate checkout, with an existing export/checkout of 28594e2 and installed JS dependencies:
```sh
node research/w20_dispute_cross_language/run.cjs /path/to/28594e2 . /path/to/existing/node_modules
```
Python 3 standard library; existing esbuild, React and react-dom only. No installation/network in execution. Four Python module Git blobs and the presenter blob are checked. fixture.json SHA256: 4c6adf9de4d7cf1eabae9cf845d98b977622b6d37dfb31a6179eefc8eb9c1dac.

The visible fixture declares one disputed question, same case/revision, two separate sub-items and two different synthetic line arrays. The host computes each complete array's UTF-8 SHA, binds selected excerpts to the actual FourChair, issues four real simulated tickets, submits eight reviews and runs the unchanged projector. The UI input comes exclusively from two predeclared (item,role) projected rows; expected control comes from the frozen fixture, not the projection. All eight rows remain in the transport payload. No voting resolves the question.

Output: 5 integration checks pass (exit 0):
- both SSR cards preserve their selected Python row's quote, role, source ID and line;
- unresolved/pending, no fact activation or write controls;
- one deliberately mismatched source rejects the whole display with no quote leakage or input mutation.

Explicit mocked boundary: same published constructor seam mocks packet loading/parsing, ledger and constructor file open/close. Actual issue/submit_simulated/receipt/project and source-selection checks run. The fixed public packet is NOT read or validated; protocol packetSha256 is not claimed as the synthetic source digest. No actual ledger/account/model/evidence-write is used. Source arrays are developer-defined strings, not acquired originals; computed hashes are local fixture identity, not authority/authenticity. Labels and rationales are scripted, not semantic evaluation.
This uses two predeclared rows across two sub-items, not four independent source attestations or a full four-seat UI. React SSR only, unmounted presenter, no HTTP/browser/default application route, approval or archive. No canceled dependency work is reused.

## Full-source version boundary
Python projection source.sha256 is preserved as input.items[].sourceSha256. The separate fixture control carries each current source.sha256. The presenter requires the held digest to match the current source digest, as well as the exact item/seat/source and excerpt.
Both hosts use SHA-256 over UTF-8 of lines.join(LF) + final LF, with no Unicode normalization. The Node fixture host independently rebuilds current source digests from its source lines; it does not grant authority to a caller-supplied digest.
Added positive: Python and Node digest equality and rendered source-version metadata. Added negative: same case/revision/source ID/line/quote, changed neighboring line, recomputed current digest; entire display rejected without showing historical quotes. Original match and wrong-source checks remain.
This is trusted ONLY within the developer-controlled fixture. No production source resolver/authentication exists; arbitrary client control must not be treated as authority. These sources do not consume 1724774 / SYN-XREPO-001 registered bytes and are NOT claimed as that registered same-case integration.
