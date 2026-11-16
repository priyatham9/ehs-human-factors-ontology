# Crosswalk translation audit

The standard SKOS export preserves all 90 proposed PIF mapping expressions,
but omits all six explicit `ehs:noCounterpartIn` assertions. A missing SKOS
mapping cannot distinguish an author-asserted absence from an unrecorded
comparison. The [interactive audit](translation-audit.html) exposes that loss
using the committed ontology, not fabricated examples.

This is an audit of an **author-proposed crosswalk**, not a new taxonomy,
independent adjudication of its alignments, or validation against incidents.

## The information-loss result

The source contains this statement:

```turtle
ehs:WorkplaceVisibility ehs:noCounterpartIn xw:fw-SPARH .
```

The test suite removes that one statement from an in-memory copy of the source.
The resulting standard SKOS Turtle and JSON-LD files are **byte-identical** to
the exports of the original source. The source meanings differ: the original
records an explicit no-counterpart assertion; the altered copy records neither
a mapping nor an absence. Consequently the source distinction cannot be
reconstructed from this projection alone. This is a non-injective translation,
not an inference that the absence assertion itself is correct.

The 80 local-factor × four-framework cells currently comprise 74 mapped cells
and six asserted absences. There are no unasserted source cells in that grid.
The export makes the six absences indistinguishable from unasserted cells.
The deliberate-deletion fixture tests the distinction without presenting an
invented unasserted cell as a fact about the committed ontology.

## What is preserved and what is lost

| Unit being counted | Source | Standard SKOS | Recoverable with sidecar |
| --- | ---: | ---: | ---: |
| PIF mapping expressions | 90 | 90 | 90 |
| Original alignment resource identities | 90 | 0 | 90 |
| Alignment records with source keys | 90 | 0 | 90 |
| Alignment records with comments | 14 | 0 | 14 |
| Explicit no-counterpart assertions | 6 | 0 | 6 |
| Explicit external coverage-gap records | 7 | 0 | 7 |

These rows overlap and must not be added into a percentage of total
information lost. All counts are generated in
[`skos/translation-loss-report.json`](skos/translation-loss-report.json).
The 90 PIF mappings comprise 34 close, 33 partial and 23 broader assertions;
the four context-dimension mappings to IDHEAS-G are counted separately.
Framework-level bibliographic citations survive in SKOS, whereas original
row-level source keys do not.

The mapping properties are the existing exporter's declared projection:
`close → skos:closeMatch`, `partial → skos:relatedMatch`, and
`broader → skos:broadMatch`, directed from local factor to external factor.
Retaining that expression does not prove logical equivalence between the
ontology's local strength definitions and the standard SKOS semantics.

An external coverage gap is distinct from a local-factor/framework absence.
CREAM's *Time of day* is both a recorded gap and the target of the proposed
partial alignment from *Mental fatigue*. Its SKOS concept and `relatedMatch`
survive; the explicit gap record and its rationale do not. Treating “has a
mapping” as “fully covered” would erase precisely the distinction the author
recorded.

## Separate, interoperable RDF sidecar

The existing files `ehs-hfo-skos.ttl` and `ehs-hfo-skos.jsonld` are unchanged.
The new files are generated independently:

- [`skos/ehs-hfo-crosswalk-sidecar.ttl`](skos/ehs-hfo-crosswalk-sidecar.ttl)
- [`skos/ehs-hfo-crosswalk-sidecar.jsonld`](skos/ehs-hfo-crosswalk-sidecar.jsonld)
- [`skos/translation-loss-report.json`](skos/translation-loss-report.json)

The sidecar contains the original outgoing triples of every `ehs:Alignment`
and `ehs:CoverageGap` resource, including their original identifiers, literal
language/datatype information, source keys, match strengths and comments. It
also contains each original `ehs:noCounterpartIn` triple. It adds no new
alignment or negative SKOS property.

Each absence triple is additionally identified with standard RDF reification
(`rdf:Statement`, `rdf:subject`, `rdf:predicate`, `rdf:object`). A stable statement
IRI is derived from the SHA-256 of its canonical full-IRI triple. The direct
triple is retained too: RDF reification alone does not assert its content.
`prov:wasDerivedFrom` links the statement to a `urn:sha256:` identifier for the
exact source-file bytes. `prov:specializationOf` connects that snapshot to the
source document. The sidecar document has the same snapshot provenance and
lists its records with `dcterms:hasPart`.

The source's no-counterpart statements are direct object-property assertions,
not reified source rows with their own citations or rationales. **Their new
provenance is source-file provenance only.** Factor-level citations or boundary
notes are not promoted into independent evidence for the absence. The sidecar
does not claim that this informal author assertion is an OWL proof that no
counterpart can exist.

The Turtle uses absolute IRIs and ordinary RDF 1.1 statements. The JSON-LD uses
an absolute-IRI, flat `@graph` profile with explicit value objects and no remote
context. They can be consumed as RDF without custom JSON keys. The repository
uses its own parser and a restricted JSON-LD profile reader for tests; it does
not claim certification by an external RDF or SKOS validator.

## Precisely scoped round trip

Let `C(G)` select:

1. every outgoing triple of any resource typed `ehs:Alignment` or
   `ehs:CoverageGap` in graph `G`;
2. every direct triple whose predicate is `ehs:noCounterpartIn`.

For the source graph `O`, the SKOS graph `S` and decoded sidecar `A`, the tested
invariant is:

```text
C(S ∪ A) = C(O)
```

The current contract contains **600 source triples**, all 600 recovered, with
zero missing and zero added contract triples. Both serializations must recover
the same graph. The sidecar itself includes these complete scoped records;
SKOS continues to supply the lightweight concept structure and projected
mapping expressions.

This is **not a full-ontology round trip**. Factor levels, macrocognitive
functions, failure modes, observable proxies, unrelated annotations and OWL
entailments are outside the contract. Use the original ontology for them.
Conflicting source assertions are retained and flagged rather than silently
resolved. Unasserted comparisons remain unasserted. Source comments and
citations remain author assertions; serialization fidelity is not validation.

## Reproduce

```sh
python3 tools/build_translation_audit.py
python3 tools/build_translation_audit.py --check
PYTHONPATH=src python3 -m unittest tests.test_translation_audit tests.test_skos
```

Outputs contain no build timestamp, machine path or random identifier. Tests
cover exact generated output, unchanged standard SKOS bytes, both RDF
serializations, scoped reconstruction, the indistinguishable absence/unknown
counterexample, a changed-rationale counterexample, a partial mapping that
coexists with a gap, conflict preservation, absence provenance and literal
escaping/language/datatype fidelity. All are standard-library tests without
network access.
