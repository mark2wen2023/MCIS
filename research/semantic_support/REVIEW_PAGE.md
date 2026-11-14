# Offline semantic explanation review sheet

Interface: `python render_review.py --corpus CORPUS.json --predictions PREDICTIONS.json --output NEW.html`. Standard library only. Loads bounded strict JSON using evaluate.load, reruns evaluate(corpus, raw corpus digest, predictions), never trusts an existing comparison file. Unknown keys, duplicate keys, invalid binding/coverage and budgets are rejected by existing evaluation contract. Output capped at 8 MiB; exclusive create mode 0600, never overwrites.

Pure static HTML, no JavaScript/network/assets/forms/href/navigation. URLs are text. All data is escaped including quotes. CSP blocks defaults, connections, forms, frames and base URLs; only inline styles allowed. Supplied quote text uses pre-wrap, not PDF reconstruction. Original rationale displayed completely. No suggested-label answer is displayed or used to tick boxes. Every checkbox starts unchecked; no automatic error detection.

Each item separates model label, model rationale, pending claim, exact supplied quote, source declaration, optional full supplied source text and three temporary checkboxes/notes. Notes and checks are page-only and may be lost on refresh; browsers may restore field values, which is also not persistent review or authentication. Printed/edited copies do not authenticate a reviewer or change facts. This is not the production review workflow.

Generated artifact: jiangxin9-research-review.html, 8 items using existing second-case corpus and real-predictions file. The renderer itself does not call any model. No new API request, automatic judgment, human certification or fact activation. Existing prediction origin remains an unverified statement, not a verified model identity.

Local unittest test_render_review: 7 tests passed (controls/default unchecked, full text, injection literal escaping, bad label/hash, output budget, exclusive writes/0600, duplicate input). Static HTML parser checks, not browser-engine visual acceptance. Independent review completed: 9 additional tests pass, combined 16/16. See REVIEW_PAGE_INDEPENDENT.md. No browser visual acceptance.
