import argparse
from pathlib import Path

from core.database import SessionLocal, init_database
from services.sample_service import build_audit_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an audit report markdown file.")
    parser.add_argument("--output", type=Path, default=Path("docs/latest_audit.md"))
    args = parser.parse_args()
    init_database()
    with SessionLocal() as session:
        report = build_audit_report(session)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "\n".join(
            [
                "# Sample Factory Audit Report",
                f"- Total samples: {report['total_samples']}",
                f"- Deduplicated samples: {report['deduplicated_samples']}",
                f"- Low confidence samples: {report['low_confidence_samples']}",
                f"- Needs review samples: {report['needs_review_samples']}",
                f"- Source distribution: {report['source_distribution']}",
                f"- Scenario distribution: {report['scenario_distribution']}",
                f"- Attack distribution: {report['attack_distribution']}",
                f"- High similarity groups: {report['high_similarity_groups']}",
                f"- Label conflicts: {report['label_conflicts']}",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
