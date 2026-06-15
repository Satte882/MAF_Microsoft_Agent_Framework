from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: Path = Path("data")
    log_level: str = "INFO"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-nano"
    openai_base_url: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
        api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
        return cls(
            host=os.getenv("MAF_LAB_HOST", "127.0.0.1"),
            port=int(os.getenv("MAF_LAB_PORT", "8000")),
            data_dir=Path(os.getenv("MAF_LAB_DATA_DIR", "data")),
            log_level=os.getenv("MAF_LAB_LOG_LEVEL", "INFO").upper(),
            openai_api_key=api_key,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-5.4-nano"),
            openai_base_url=base_url,
        )

    @property
    def database_path(self) -> Path:
        return self.data_dir / "maf_lab.db"

    @property
    def checkpoint_root(self) -> Path:
        return self.data_dir / "checkpoints"

    @property
    def provider_configured(self) -> bool:
        return bool(self.openai_api_key and self.openai_model)

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_root.mkdir(parents=True, exist_ok=True)
