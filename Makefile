PYTHON ?= python3
NODE ?= node
NPM ?= npm
.PHONY: setup ingest train experiment-v2 audit test build dev demo stress
setup:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt
	cd frontend && $(NPM) ci
ingest:
	$(PYTHON) -m backend.app.data.ingest_workbook
train:
	LOKY_MAX_CPU_COUNT=4 OMP_NUM_THREADS=1 $(PYTHON) -m backend.app.ml.train
experiment-v2:
	OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 $(PYTHON) -m backend.app.ml.experiment_v2
audit:
	$(PYTHON) -m backend.app.data.audit
test:
	LOKY_MAX_CPU_COUNT=4 $(PYTHON) -m pytest
	cd frontend && $(NPM) run typecheck
build:
	cd frontend && NEXT_TELEMETRY_DISABLED=1 $(NPM) run build
dev:
	$(PYTHON) scripts/dev.py
demo: dev
stress:
	$(PYTHON) scripts/stress_test.py
