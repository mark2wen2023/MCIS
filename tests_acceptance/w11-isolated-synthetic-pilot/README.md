# W11 isolated synthetic combined pilot (acceptance only)

Independent acceptance directory for one-case, one-edge, one-excerpt local
synthetic verification. It reuses the existing single-edge isolation assembly
and permission/audit implementation from `tests_acceptance/w11-excerpt-binding-local`
and `tests_acceptance/w11-edge-host-optin` without editing those files or any
product source.

Draft preview/save goes through the existing ECFC service routes and the
already-verified real `mcis-ecfc` .NET core (contract `mcis-ecfc-draft/1`),
built offline from the pinned `CORE_SOURCES` recipe. The W4.1 `mcis-core.dll`
artifact (`mcis-core-build/1`) is not an ECFC validator and is not used.

The excerpt route `/__local_synthetic_w11/SYN-XREPO-001/edge-excerpt` is
registered only after `create_app()` in this pilot process. The official
application does not register it.

This directory is not a product feature, does not add a product endpoint, does
not change graph format or permissions, and does not write the formal product
database. HTTP results are HTTP, not a browser result. This is not a W11
whole-package claim.
