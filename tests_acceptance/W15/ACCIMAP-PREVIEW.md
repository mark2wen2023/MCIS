# W15 AcciMap: isolated synthetic draft presentation

Pinned product parent: a6fc54a02472c87d467927e88e6a8a4054fa1a6b.

The six tier names follow the existing C# `AcciMapLevel` in
`unity/Assets/_Project/Scripts/Domain/Systemic/AcciMap.cs`. That model separates
directed edges from information flows, and validates them in the native core.
The fixed `web/src/pages/SystemicPage.tsx` mounts only Bow-tie via case-bound
Bow-tie source/preview reads. The legacy AcciMap core/archive does not give the
Web component a trusted, current, same-case reviewed draft or scoped source
list. Do not reuse the Bow-tie response or mine archive data as a substitute.

The new static, isolated component has no route, storage, links, requests,
evidence import, validation engine, approval or export. Explicit synthetic
same-case typed fixture only. Its case/fixture guard is not authentication.
Solid and dashed arrows only draw supplied relationship and information-flow
edges. Missing, ambiguous and self endpoints are counted and omitted; no
relationship is added or declared correct. All visible nodes remain unknown
Links sharing an endpoint pair receive separate drawing tracks, regardless of
kind or direction. A native keyboard-toggleable disclosure lists each input link
with the full IDs, direction, link kind, and whether the map could draw it.
and pending. Full IDs are retained in SVG titles.

To connect the actual product, first identify an existing or separately
approved current AcciMap draft reader with case and revision/identity binding,
source permissions and explicit human workflow. Revalidate from actual
reviewed input before adding a route, persistence or local download. No
contract, production permission, archive or existing route is modified here.

Linux check using existing React/ReactDOM, esbuild, TypeScript and Happy DOM:

```sh
cd web
node_modules/.bin/esbuild tests/accimap-draft-diagram.test.tsx --bundle --packages=external --platform=node --format=esm --jsx=automatic --outfile=tests/.tmp-accimap.mjs
node tests/.tmp-accimap.mjs
```

Observed exit 0 for the new component-only sparse TypeScript check and React
static render + Happy DOM assertions. No browser, actual core rerun, full
application build, untrusted input ingestion, or product integration claim.
