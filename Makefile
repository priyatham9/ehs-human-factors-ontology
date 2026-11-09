.PHONY: pif-cooccurrence health test

pif-cooccurrence:
	python3 tools/pif_cooccurrence.py --write

health:
	python3 tools/health.py --write

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -t .
