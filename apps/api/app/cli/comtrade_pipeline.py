from __future__ import annotations

import argparse
import asyncio

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.bulk_pipeline import ComtradeLocalPipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="UN Comtrade local HS2022 pipeline")
    parser.add_argument(
        "command",
        choices=("download", "import", "analyze", "all"),
        help="Pipeline stage to execute",
    )
    args = parser.parse_args()
    settings = get_settings()
    pipeline = ComtradeLocalPipeline(settings)
    with SessionLocal() as db:
        if args.command in {"download", "all"}:
            asyncio.run(pipeline.download(db))
        if args.command in {"import", "all"}:
            pipeline.import_downloads(db)
        if args.command in {"analyze", "all"}:
            asyncio.run(pipeline.analyze(db))


if __name__ == "__main__":
    main()
