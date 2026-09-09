# Contributing

## Running Tests

```bash
cd /path/to/ehs-human-factors-ontology
PYTHONPATH=src python3 -m unittest discover -s tests -t .
```

171 tests, standard library only. The `PYTHONPATH=src` is required for all invocations.

Other common commands:

```bash
PYTHONPATH=src python3 -m ehs_hfo assess examples/reactor_startup_nonroutine.json
PYTHONPATH=src python3 -m ehs_hfo factors          # list the 20 factors by dimension
PYTHONPATH=src python3 -m ehs_hfo crosswalk        # show every correspondence
python3 tools/build_crosswalk.py --check           # verify crosswalk is current
python3 synthetic/generate_scenarios.py --check    # verify corpus is reproducible
```

## Dependency Policy

This project uses Python 3.9 or later with:
- Standard library only
- No rdflib, no OWL reasoner, no external dependencies

The Turtle parser is hand-written and built-in. The Datalog evaluator is hand-written. There is no dependency on third-party RDF or semantic-web tools.

## Numbers and Alignments

Every correspondence in the crosswalk must be produced by a committed script:

1. The crosswalk is generated from the Turtle ontology by `tools/build_crosswalk.py`
2. A test enforces that the published crosswalk exactly matches what the ontology generates
3. Every alignment carries a match strength (close/broader/narrower/partial; never exact) and a citation
4. No correspondence may be hand-edited in the CSV or Markdown; edit the ontology instead

Every factor's verbatim label is transcribed from its source (NUREG-2198 for IDHEAS-G, framework documents for the others) and carried in `ehs:verbatimLabel` so transcription can be checked.

## Synthetic Data

`synthetic/` contains generated scenario files for testing the engine. Rules:

- Every synthetic JSON file is labelled as such in four places (header, manifest, README, generator comment)
- Files are used only to exercise the engine and test rule evaluation, never as evidence
- `synthetic/generate_scenarios.py --check` verifies the corpus is byte-reproducible
- See `synthetic/README.md` for the generator's design and limitations
