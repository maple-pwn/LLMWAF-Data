import argparse
import json
from pathlib import Path

from alembic import command
from alembic.config import Config

from core.bootstrap import bootstrap_defaults
from core.database import SessionLocal
from core.database import init_database
from services.sample_service import create_sample_record


def run_migrations() -> None:
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")


def load_seed_samples(seed_path: Path) -> None:
    if not seed_path.exists():
        return
    with SessionLocal() as session:
        for line in seed_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            create_sample_record(session, json.loads(line))
        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the sample factory database.")
    parser.add_argument("--seed", type=Path, default=Path("data/samples/seed_samples.jsonl"))
    args = parser.parse_args()
    init_database()
    run_migrations()
    bootstrap_defaults()
    load_seed_samples(args.seed)


if __name__ == "__main__":
    main()
