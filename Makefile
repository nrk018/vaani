.PHONY: dev api web ingest bench

PY ?= .venv/bin/python

api:
	cd api && PYTHONPATH=. ../.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd web && npm run dev

ingest:
	KMP_DUPLICATE_LIB_OK=TRUE TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONPATH=api $(PY) ingest/build_index.py

ingest-xi:
	KMP_DUPLICATE_LIB_OK=TRUE TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONPATH=api $(PY) ingest/build_index.py --with-xi --xi-rows 2000 --xi-langs hi,mr

bench:
	KMP_DUPLICATE_LIB_OK=TRUE TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONPATH=api $(PY) eval/bench.py
