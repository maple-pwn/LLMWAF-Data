import argparse
import time

from core.database import SessionLocal, init_database
from services.generation_service import process_pending_generation_tasks


def process_pending() -> int:
    with SessionLocal() as session:
        return process_pending_generation_tasks(session)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local generation worker.")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    init_database()
    if args.once:
        process_pending()
        return
    while True:
        process_pending()
        time.sleep(1.0)


if __name__ == "__main__":
    main()
