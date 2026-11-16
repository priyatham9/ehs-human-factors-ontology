.PHONY: pif-cooccurrence health test translation-audit

translation-audit:
	python3 tools/build_translation_audit.py

pif-cooccurrence:
	python3 tools/pif_cooccurrence.py --write

health:
	python3 tools/health.py --write

test:
	PYTHONPATH=src python3 -m unittest discover -s tests -t .
