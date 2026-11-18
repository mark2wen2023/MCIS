"""服务配置：全部来自环境变量，均有安全默认值。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = SERVICE_ROOT.parent


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("MCIS_DATA_DIR", SERVICE_ROOT / "data")))
    db_url: str | None = field(default_factory=lambda: os.environ.get("MCIS_DB_URL"))
    seed_demo: bool = field(default_factory=lambda: os.environ.get("MCIS_SEED_DEMO", "1") != "0")
    # Independent of seed population; only explicit application configuration enables reads.
    allow_analysis_seed_reads: bool = False
    allow_public_report_reads: bool = False
    core_cmd: str = field(default_factory=lambda: os.environ.get("MCIS_CORE", str(PROJECT_ROOT / "tools" / "mcis-core" / "mcis-core.sh")))
    core_timeout_s: float = field(default_factory=lambda: float(os.environ.get("MCIS_CORE_TIMEOUT", "60")))
    host: str = "127.0.0.1"
    port: int = field(default_factory=lambda: int(os.environ.get("MCIS_PORT", "8765")))

    @property
    def blob_dir(self) -> Path:
        return self.data_dir / "blobs"

    @property
    def resolved_db_url(self) -> str:
        return self.db_url or f"sqlite:///{self.data_dir / 'mcis.db'}"
