"""调用 C# 计算核心 mcis-core（stdin/stdout JSON）。"""
from __future__ import annotations

import json
import subprocess
from typing import Any


class CoreError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 502):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status


_STATUS = {"NOT_IMPLEMENTED": 501, "BAD_REQUEST": 422, "BAD_JSON": 422, "UNKNOWN_COMMAND": 501}


def run(core_cmd: str, command: str, payload: dict[str, Any], timeout_s: float = 60.0) -> dict[str, Any]:
    try:
        proc = subprocess.run([core_cmd, command], input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                              capture_output=True, timeout=timeout_s, check=False)
    except FileNotFoundError as e:
        raise CoreError("CORE_UNAVAILABLE", f"找不到 mcis-core：{core_cmd}", 503) from e
    except subprocess.TimeoutExpired as e:
        raise CoreError("CORE_TIMEOUT", f"mcis-core {command} 超时", 504) from e
    out = proc.stdout.decode("utf-8", "replace").strip().splitlines()
    if not out:
        raise CoreError("CORE_NO_OUTPUT", f"mcis-core 无输出（exit={proc.returncode}）：{proc.stderr.decode('utf-8', 'replace')[-400:]}", 502)
    try:
        env = json.loads(out[-1])
    except ValueError as e:
        raise CoreError("CORE_BAD_OUTPUT", out[-1][:400], 502) from e
    if not env.get("ok"):
        err = env.get("error") or {}
        code = err.get("code", "CORE_ERROR")
        raise CoreError(code, err.get("message", ""), _STATUS.get(code, 502))
    return env
