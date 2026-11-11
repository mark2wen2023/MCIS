#!/usr/bin/env python3
"""W6.1 测试用假 mcis-core：只实现 colreg，确定性输出；把收到的 vesselStatus/evidenceIds 回显到结果里。"""
import json
import sys

cmd = sys.argv[1] if len(sys.argv) > 1 else ""
req = json.loads(sys.stdin.read() or "{}")
if cmd != "colreg":
    print(json.dumps({"ok": False, "error": {"code": "UNKNOWN_COMMAND", "message": cmd}}))
    sys.exit(0)
vids = sorted(req.get("tracks", {}).keys())
status_rows = sorted(req.get("vesselStatus") or [], key=lambda r: r["timeSec"])


def status_at(vid, t):
    st = "PowerDriven"
    for r in status_rows:
        if r["vesselId"] == vid and r["timeSec"] <= t:
            st = r["status"]
    return st


bands = []
for i, (a, b, sit, stage) in enumerate([(0, 300, "HeadOn", "None"), (300, 540, "ImmediateDanger", "ImmediateDanger")]):
    bands.append({"bandId": f"E{i + 1}", "startTimeSec": a, "endTimeSec": b, "situation": sit, "inSight": True,
                  "giveWayVesselId": None, "standOnVesselId": None, "applicableRules": ["R14"], "basis": "fake",
                  "dangerStage": stage, "doubt": False, "doubtReason": None,
                  "vesselStatus": {v: status_at(v, a) for v in vids}})
ev = req.get("evidenceIds") or []
checks = []
for i, v in enumerate(vids):
    checks.append({"checkId": f"EK-{i + 1:02d}", "rule": "R14", "title": "对遇右转", "vesselId": v,
                   "verdict": "NotComplied" if i else "Complies", "atTimeSec": 300, "requiredAction": "向右转",
                   "actualAction": "fake", "deviation": "", "evidenceIds": list(ev)})
print(json.dumps({"ok": True, "coreVersion": "fake-0", "result": {"caseId": req.get("caseId"), "engineVersion": "fake-0",
                                                                    "bands": bands, "checks": checks}}, ensure_ascii=False))
