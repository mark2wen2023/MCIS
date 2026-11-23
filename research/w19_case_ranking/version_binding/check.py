"""Developer-visible synthetic version binding; no product interface."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import runpy
import tempfile

PIN_BLOB = "44fc5d82279db5fa3a3c748161f3122708e85668"
ROOT = Path(__file__).resolve().parent

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def receipt(card, catalog, locate):
    # catalog is fixed by this synthetic test host, never selected by a card.
    binding = card.get("sourceBinding")
    if binding is None:
        state = "BINDING_MISSING"
    elif binding["version"] != catalog["version"]:
        state = "SOURCE_VERSION_MISMATCH"
    elif binding["sha256"] != catalog["sha256"]:
        state = "SOURCE_DIGEST_NOT_CURRENT"
    elif binding["recordId"] != catalog["recordId"]:
        state = "RECORD_NOT_SELECTED"
    else:
        state = locate(card)
    return {
        "cardId": card["cardId"], "traceability": state,
        "binding": deepcopy(binding), "support": "NOT_ASSESSED",
        "causation": "NOT_ASSESSED", "review": "PENDING",
        "authenticatedReview": False,
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verifier", type=Path,
                        default=ROOT.parent / "source_traceability" / "check.py")
    args = parser.parse_args()
    raw = args.verifier.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if blob != PIN_BLOB:
        raise SystemExit("PINNED_VERIFIER_MISMATCH")
    for line in (ROOT / "INPUTS.sha256").read_text().splitlines():
        expected, name = line.split("  ")
        if digest((ROOT / name).read_bytes()) != expected:
            raise SystemExit("FROZEN_INPUT_MISMATCH")
    fixture = json.loads((ROOT / "fixture.json").read_text())
    current = (ROOT / "current.txt").read_bytes()
    stale = (ROOT / "stale.txt").read_bytes()
    catalog = fixture["hostSelection"]
    assert digest(current) == catalog["sha256"]
    assert digest(stale) == fixture["cards"][1]["sourceBinding"]["sha256"]
    # Same filename, title and record identity; changed timestamp and bytes.
    a, b = current.decode("utf-8").rstrip("\n").split("\t", 2), stale.decode("utf-8").rstrip("\n").split("\t", 2)
    assert a[:2] == b[:2] and a[2] != b[2]
    locate = runpy.run_path(str(args.verifier))["locate"]
    with tempfile.TemporaryDirectory(prefix="w19-version-binding-") as temp:
        path = Path(temp) / "source-records.txt"
        path.write_bytes(current)
        locate.__globals__["ROOT"] = Path(temp)
        cards = fixture["cards"]
        outputs = [receipt(c, catalog, locate) for c in cards]
        assert [r["traceability"] for r in outputs] == [
            "LOCATED", "SOURCE_VERSION_MISMATCH", "BINDING_MISSING"]
        checks = ["current_exact_utf8_located", "same_title_stale_version_rejected",
                  "missing_binding_pending"]
        # Existing locator alone rejects old digest against current file.
        assert locate(cards[1]) == "SOURCE_HASH_MISMATCH"
        checks.append("legacy_current_bytes_reject_stale_digest")
        # A fully self-consistent stale snapshot can locate, but is not current.
        path.write_bytes(stale)
        assert locate(cards[1]) == "LOCATED"
        assert receipt(cards[1], catalog, locate)["traceability"] == "SOURCE_VERSION_MISMATCH"
        checks.append("locatable_stale_snapshot_not_current")
        path.write_bytes(current)
        c = deepcopy(cards[1])
        c["sourceBinding"]["version"] = catalog["version"]
        assert receipt(c, catalog, locate)["traceability"] == "SOURCE_DIGEST_NOT_CURRENT"
        checks.append("relabelled_version_cannot_replace_digest")
        c = deepcopy(cards[0])
        c["sourceBinding"]["recordId"] = "SYN-OTHER"
        assert receipt(c, catalog, locate)["traceability"] == "RECORD_NOT_SELECTED"
        checks.append("record_not_selected_rejected")
        c = deepcopy(cards[0])
        c["content"]["source"]["excerpt"] = cards[1]["content"]["source"]["excerpt"]
        assert receipt(c, catalog, locate)["traceability"] == "TEXT_MISMATCH"
        checks.append("stale_time_text_under_current_binding_rejected")
        assert all(r["support"] == r["causation"] == "NOT_ASSESSED"
                   and r["review"] == "PENDING" and r["authenticatedReview"] is False
                   for r in outputs)
        checks.append("all_receipts_unassessed_unauthenticated_pending")
    print(json.dumps({"scope": "developer-visible synthetic controls only",
                      "verifierBlob": PIN_BLOB, "hostSelection": catalog,
                      "receipts": outputs, "checks": checks,
                      "passed": len(checks)}, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
