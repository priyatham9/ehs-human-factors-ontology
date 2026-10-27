# SKOS export: reusing the PIF structure and crosswalk as linked data

The 4 context dimensions, 20 performance-influencing factors (PIFs) and the
crosswalk to SPAR-H, CREAM, HFACS and the HSE PIF list are also published as
[SKOS](https://www.w3.org/TR/skos-reference/) (W3C Recommendation, 2009), so
that other vocabularies and tools can link to them without reading the OWL file.

| File | Format |
| --- | --- |
| `docs/skos/ehs-hfo-skos.ttl` | Turtle |
| `docs/skos/ehs-hfo-skos.jsonld` | JSON-LD (flat `@graph`, prefix-only `@context`) |

Once the `docs/` folder is published by GitHub Pages they are served at
`https://priyatham9.github.io/ehs-human-factors-ontology/skos/ehs-hfo-skos.ttl`
and `.../skos/ehs-hfo-skos.jsonld`; the raw-GitHub equivalents are under
`https://raw.githubusercontent.com/priyatham9/ehs-human-factors-ontology/main/docs/skos/`.

Both files are generated from `ontology/ehs-hfo.ttl` by `tools/build_skos.py`
(standard library only) and are never edited by hand.

## What is in it

* `ehs:PIFConceptScheme`: the four context dimensions as top concepts
  (`skos:topConceptOf`), the twenty PIFs as their `skos:narrower` concepts.
  Labels are `skos:prefLabel` (`@en`); where the source document words a PIF
  differently, the verbatim wording is `skos:altLabel`. Boundary notes recording
  contested classifications are `skos:scopeNote`.
* One `skos:ConceptScheme` per external framework (`xw:fw-IDHEAS-G`,
  `xw:fw-SPARH`, `xw:fw-CREAM`, `xw:fw-HFACS`, `xw:fw-HSE-PIF`) holding that
  framework's factors as concepts (78 in all), with the framework's
  bibliographic citation.
* The crosswalk as SKOS mapping properties from a PIF to an external factor.
  The ontology's match strengths map as follows; the direction is always PIF
  (subject) to external factor (object).

| Ontology strength | SKOS property | Meaning here | Count in the export |
| --- | --- | --- | --- |
| exact | `skos:exactMatch` | same construct and scope | 0 (none asserted; a test enforces that none is invented) |
| close | `skos:closeMatch` | same construct, wording or scope differs | 34 |
| broader | `skos:broadMatch` | the external factor subsumes the PIF | 23 |
| narrower | `skos:narrowMatch` | the external factor covers part of the PIF | 0 |
| partial | `skos:relatedMatch` | overlapping, non-nested | 33 |

The 90 alignments give 90 mapping triples (34 + 23 + 33). In addition, each
context dimension carries a `skos:closeMatch` to its IDHEAS-G category
(Task, Environment and situation, Personnel, System): 4 more `closeMatch`
triples, 38 in the file. `closeMatch` rather than `exactMatch` is deliberate:
the ontology treats these as analyst judgements, not asserted identity.

## What is not in it

SKOS has no way to say "this PIF has no counterpart in framework X", so the 6
"no counterpart" assertions are absent here (they remain in the OWL file and in
`crosswalk/crosswalk.md`). The per-row source keys and comments of the reified
alignments, the factor levels, macrocognitive functions, failure modes and
observable proxies are likewise not exported; use `ontology/ehs-hfo.ttl` for
those. The mapping triples carry the analyst judgement and the framework
schemes carry the bibliographic citation, but the row-level citation is only in
the source.

## Identifiers

Concept URIs are the ontology's existing identifiers, for example
`https://priyatham9.github.io/ehs-human-factors-ontology/ehs-hfo#Training`, so
the SKOS file and the OWL file describe the same resources. They are
identifiers. This project does not run a content-negotiating resolver, so
dereferencing a concept URI is not guaranteed to return RDF; fetch the files
above instead. The identifiers will not be renamed without a changelog entry.

## Reusing it

Link to a PIF from your own vocabulary:

```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ehs:  <https://priyatham9.github.io/ehs-human-factors-ontology/ehs-hfo#> .

<https://example.org/my-taxonomy/staffing-shortfall>
    skos:closeMatch ehs:Staffing .
```

Load the file into any SKOS-aware tool or triple store (for example with
`rdflib`, Jena or a SKOS editor; none is required or tested here), or read the
JSON-LD with any JSON-LD processor. Mappings are analyst judgements published
with the caveats in the main README: they are not a validated equivalence
between methods, and in particular nothing here has been adopted, endorsed or
reviewed by any standards body, regulator or the authors of the frameworks
mapped.

## Regenerating and checking

```
python3 tools/build_skos.py           # rewrite docs/skos/
python3 tools/build_skos.py --check   # exit 1 if the files are out of date
python3 -m unittest tests.test_skos
```

`tests/test_skos.py` regenerates both files and compares them with what is
committed; parses the Turtle back with the repository's own parser and the
JSON-LD with a small expander, and requires both to give exactly the generated
triples; checks that every concept has a label and belongs to exactly one
declared scheme and that every SKOS relation points at a declared concept or
scheme; and checks that every alignment appears as its mapping triple. No
network access is used. These checks show the files are well formed and
faithful to the source; they are not validation by an external SKOS validator.
