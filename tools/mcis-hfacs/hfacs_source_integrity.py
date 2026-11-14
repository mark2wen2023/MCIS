"""Test-only source pins from W184's committed acceptance record.

Reviewed repository history is the trust anchor, not the candidate receipt.
No SDK, Git metadata, sibling checkout, network or artifact generation required.
"""
import hashlib

CORE_SHA256 = {'unity/Assets/_Project/Scripts/Core/Primitives/Result.cs': '15f9b52af048291c69e4a0ebd9959e679414c9abe67c02daf35ad7b6c9c73145', 'unity/Assets/_Project/Scripts/Domain/Evidence/CustodyEvent.cs': 'ffe7a06d86ec2d698cf23e61484d1e0117eebdaea9fc41a3cc9ea4fc585b7f26', 'unity/Assets/_Project/Scripts/Domain/Evidence/CustodyLedger.cs': '618af0e414ed0a70e52a712d9702249512922d3ce08528530927d7020ae837d8', 'unity/Assets/_Project/Scripts/Domain/Evidence/EvidenceItem.cs': '9116d127128155f5d1ebd0491e66a95042989bdbf97c9b687f2577c024813a5c', 'unity/Assets/_Project/Scripts/Domain/Evidence/InvestigationAudit.cs': '07aa67c779169490de2697569519b25fc122bc2473b4a0e31660c1b4c5026d2a', 'unity/Assets/_Project/Scripts/Domain/Evidence/Sha256Hex.cs': 'ad9478e84a7b947a16145cfc9407f21aaf14a62b3e99379ae729829015bd93be', 'unity/Assets/_Project/Scripts/Domain/HumanFactors/Hfacs.cs': '4411823490ecc16f8ef95856e5000750f587bc8c2752a6ead282367cc1db22e9'}


def verify_sources(root, inputs):
    """Reject incomplete/changed core pins and mismatched receipt source bytes."""
    if not isinstance(inputs, dict) or not set(CORE_SHA256) <= set(inputs):
        raise AssertionError('Receipt omits required core source')
    # Core provenance must remain pinned even if source and receipt change together.
    for path, expected in CORE_SHA256.items():
        if inputs[path] != expected:
            raise AssertionError('Core receipt differs from W184 baseline: ' + path)
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
            raise AssertionError('Core source differs from W184 baseline: ' + path)
    for path, expected in inputs.items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
            raise AssertionError('Receipt/source mismatch: ' + path)
