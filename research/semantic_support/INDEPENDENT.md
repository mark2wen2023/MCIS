# Independent offline semantic-comparison review

Scope: `evaluate.py` and fixed provisional corpus/predictions/review snapshot
contract. This reviewer did not change implementation, call a model/API, certify
expert labels or independently authenticate the linked PDF.

## Final tests

Independent `test_evaluate_independent.py`: **28 tests**.
Combined with primary `test_evaluate.py`: **44/44 passed**, zero skips, 0.33s.

Independent coverage includes:
- exact citation while proposed semantics contradict the provisional suggestion;
  neither label is upgraded to verified meaning/truth;
- Unicode code-point coordinates including astral characters, explicit repeated
  quote spans, mismatched length and out-of-bounds location;
- two different aliases with the same self-reported name, including a script:
  identity, qualification and independence remain unverified, conflicting
  rationales preserved, agreeing opinions still do not establish truth;
- strict field/count/bool-as-int/source-hash/corpus-hash validation, complete
  prediction coverage, unknown/duplicate identities and opinions;
- duplicate decoded JSON keys, nonfinite numbers, nesting and file-byte budgets;
- rejection of fabricated identityVerified/verified-expert metadata;
- inputs remain unchanged; generic CLI failures do not echo sentinel source data;
- actual CLI execution with socket creation forbidden, using the 11-item public
  excerpt corpus, scripted predictions and empty review snapshot: no network or
  real model, two unlabeled suggestions retained, no reviewer certification.

No blocking issue found. The two axes remain independent: quote location only
checks exact text at a declared code-point span, whereas semantic labels are
unverified external proposals compared with provisional AI-constructed labels.
No accuracy, correctness rate, expert gold standard or factual activation is
emitted. Scripted predictions are explicitly distinguished from unverified model
outputs. A review file is a snapshot, not an immutable revision log.

Source SHA checking proves internal correspondence to sourceText, not that the
PDF/URL is authentic or that its page locator was verified. sourceLocatorVerified
remains false. Different reviewer IDs do not prove different humans or independent
professional review. Professional adjudication and production integration remain
outside this offline comparison tool.
0c5c8305e25f4b9ef12934c33c9bdac7458554f675bcf078c46bcb852722aff9  pi-transcript/research/semantic_support/evaluate.py
