import streamlit as st
from sqlalchemy import func, select

from core.bootstrap import bootstrap_defaults
from core.database import SessionLocal, init_database
from models.entities import Dataset, SampleRecord
from services.sample_service import build_audit_report


def main() -> None:
    st.set_page_config(page_title="Sample Factory", layout="wide")
    st.title("LLM Sample Factory")
    st.caption("A lightweight operations view for local development.")

    init_database()
    bootstrap_defaults()

    with SessionLocal() as session:
        sample_total = session.scalar(select(func.count()).select_from(SampleRecord))
        dataset_total = session.scalar(select(func.count()).select_from(Dataset))
        st.metric("Samples", sample_total or 0)
        st.metric("Datasets", dataset_total or 0)
        report = build_audit_report(session)

    cols = st.columns(3)
    cols[0].metric("Deduplicated", report["deduplicated_samples"])
    cols[1].metric("Needs Review", report["needs_review_samples"])
    cols[2].metric("Low Confidence", report["low_confidence_samples"])

    st.subheader("Source Distribution")
    st.json(report["source_distribution"])

    st.subheader("Attack Coverage")
    st.json(report["attack_distribution"])

    st.subheader("Flags")
    st.json(
        {
            "high_similarity_groups": report["high_similarity_groups"],
            "label_conflicts": report["label_conflicts"],
        }
    )


if __name__ == "__main__":
    main()
