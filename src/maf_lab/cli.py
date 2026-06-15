from __future__ import annotations

import uvicorn
from dotenv import load_dotenv

from maf_lab.config import Settings


def main() -> None:
    load_dotenv()
    settings = Settings.from_env()
    uvicorn.run(
        "maf_lab.api:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=False,
    )


if __name__ == "__main__":
    main()
