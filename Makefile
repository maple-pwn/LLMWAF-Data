PYTHON ?= .venv/bin/python
UVICORN ?= .venv/bin/uvicorn
STREAMLIT ?= .venv/bin/streamlit
PYTEST ?= .venv/bin/pytest
ALEMBIC ?= .venv/bin/alembic

.PHONY: init run worker ui migrate test eval scan

init:
	$(PYTHON) scripts/init_db.py --seed data/samples/seed_samples.jsonl

run:
	$(UVICORN) app.main:app --reload

worker:
	$(PYTHON) scripts/run_worker.py --once

ui:
	$(STREAMLIT) run app/ui.py

migrate:
	$(ALEMBIC) upgrade head

test:
	$(PYTEST) -q

eval:
	$(PYTHON) scripts/generate_report.py --output docs/latest_audit.md

scan:
	$(PYTHON) scripts/generate_report.py --output docs/latest_audit.md
