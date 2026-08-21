.PHONY: dev api web ingest bench

PY ?= .venv/bin/python

api:
	cd api && PYTHONPATH=. ../.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	cd web && npm run dev

ingest:
	KMP_DUPLICATE_LIB_OK=TRUE TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONPATH=api $(PY) ingest/build_index.py

ingest-xi:
	KMP_DUPLICATE_LIB_OK=TRUE TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONPATH=api $(PY) ingest/build_index.py --with-xi --xi-rows 8000 --xi-langs hi,mr

# Every unique MS MARCO *validation* query (hinval+marval = 97,941 each).
# Not the 10M-row train dump. Expect ~1–2 hours embed + ~1M chunks. Restart make api after.
ingest-xi-all:
	KMP_DUPLICATE_LIB_OK=TRUE TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONPATH=api $(PY) ingest/build_index.py --with-xi --xi-rows 200000 --xi-langs hi,mr

bench:
	KMP_DUPLICATE_LIB_OK=TRUE TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=1 PYTHONPATH=api $(PY) eval/bench.py
