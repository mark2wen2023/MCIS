# W19 product source review

Base: main `3aba2bf03e393909c611489ae573a887087637ac`.

This changes the actual existing `SuggestionPreview` used by `KnowledgePage`, rather than an offline research page. It does not change a service API, persist a candidate, publish content, fetch a source link, or call an LLM. The existing provider remains `template-stub-v1`.

The displayed source classification remains an operator assertion. A local checkbox means the operator checked the displayed source type, locator and excerpt for copying to the form; it is not a rights release or fact verification. Copying requires the acknowledgment digest to match the current response and the existing source-binding parser to accept the response against the current input. The returned content is cloned. Generating another preview resets the acknowledgment even for identical input.

Validation in the isolated source snapshot:

```
esbuild tests/knowledge-source-review.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/w19-source-review.cjs --jsx=automatic
node /tmp/w19-source-review.cjs
esbuild tests/knowledge-w192.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/w19-original.cjs
node /tmp/w19-original.cjs
tsc -p tsconfig.app.json --tsBuildInfoFile /tmp/w19-source-review.tsbuildinfo
esbuild src/knowledge/SuggestionPreview.tsx --bundle --platform=browser --format=esm --outfile=/tmp/w19-source-component.js --jsx=automatic
```

16 local checks, the existing W19.2 regression, isolated typecheck and browser-target bundle pass. These are not full web app build, browser click/visual acceptance, API end-to-end, real model, or production identity validation. Independent review recorded separately. No deployment or merge.
