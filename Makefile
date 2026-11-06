.PHONY: pif-cooccurrence test

pif-cooccurrence:
	python3 tools/pif_cooccurrence.py --write

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -t .
