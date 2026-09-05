# ehs-human-factors-ontology

A machine-readable encoding of the four-context performance-influencing-factor
structure used in human reliability analysis, an explicit crosswalk from it to
SPAR-H, CREAM, HFACS and the HSE PIF list, and a dependency-free rule engine
that evaluates a work scenario against it and shows its working.

Python 3.9+, standard library only. No pip installs, no build step.

## The claim, stated up front

**The four context dimensions in this repository are not new.** They are the
four PIF context categories published by the U.S. Nuclear Regulatory Commission
in IDHEAS-G (NUREG-2198, 2021), which classifies its 20 PIFs "according to the
four types of context: environment and situation, system, personnel, and task."

| This ontology | IDHEAS-G | Relation |
| --- | --- | --- |
| Task context | Task | identical label |
| System context | System | identical label |
| Operational context | Environment and situation | synonym |
| Human context | Personnel | synonym |

Two labels are identical; two are synonyms. The twenty factors are IDHEAS-G's
twenty PIFs, adopted unchanged. Grouping PIFs into a small number of context
categories is itself conventional — THERP (1983) splits them internal/external,
HSE uses Job/Person/Organisation, and CREAM (1998), SPAR-H (2005), NUREG-1792
(2005) and HFACS each group on their own lines — but those partitions differ in
arity and none of them draws IDHEAS-G's four-way boundary. Only the IDHEAS-G
correspondence is claimed as one to one, and only it is machine-checked.

This is said first because it is the thing a reviewer would otherwise find and
hold against the work. The taxonomy is adopted, deliberately and with citation.
What is contributed is the encoding, the crosswalk and the traceability — and
those are worth less than a new taxonomy would be if a new taxonomy were
warranted. It is not: Boring (2010) documents that PSF sets already range from
one factor to fifty-plus, and Groth and Mosleh (2012) report that the existing
ones are not defined precisely enough to be interpreted consistently. Adding a
fifteenth loosely-defined grouping would make a documented problem worse.

## What this repository actually contains

**1. An OWL/Turtle ontology** (`ontology/ehs-hfo.ttl`, hand-written, 867 lines).
Four context dimensions, twenty factors, five ordinal factor levels, three
cognitive control levels and their error modes, five external frameworks with
their complete factor inventories (78 external factors), and 90 reified
alignments plus 6 asserted absences between them. Every
factor carries the source's own wording in `ehs:verbatimLabel` so a reader can
check the transcription.

**2. A crosswalk** (`crosswalk/crosswalk.md`, `crosswalk/crosswalk.csv`).
Every factor mapped to its counterpart in SPAR-H, CREAM, HFACS and the HSE PIF
list, with a match strength and a citation on every row, and an explicit
`no counterpart` assertion where a framework has none. Generated from the
Turtle by `tools/build_crosswalk.py`; the test suite fails if the two disagree,
so it cannot drift.

**3. A forward-chaining rule engine** (`src/ehs_hfo/engine.py`). A bottom-up
Datalog evaluator with stratified negation. Every derived fact records the rule
that produced it and the facts that satisfied that rule's body, so any
conclusion unwinds to the scenario inputs and the cited literature.

**4. A synthetic scenario corpus** (`synthetic/`). Fabricated, labelled as such
in four places, and used only to exercise the engine. See `synthetic/README.md`.

## Quick start

```
git clone <this repository>
cd ehs-human-factors-ontology

python3 -m unittest discover -s tests -t .          # 158 tests
PYTHONPATH=src python3 -m ehs_hfo assess examples/reactor_startup_nonroutine.json
```

Other commands:

```
PYTHONPATH=src python3 -m ehs_hfo assess <file> --json   # machine-readable result
PYTHONPATH=src python3 -m ehs_hfo factors            # the twenty factors by dimension
PYTHONPATH=src python3 -m ehs_hfo crosswalk          # every correspondence
PYTHONPATH=src python3 -m ehs_hfo crosswalk --framework xw:fw-SPARH
PYTHONPATH=src python3 -m ehs_hfo gaps               # what is not covered
PYTHONPATH=src python3 -m ehs_hfo rules              # the rule base, by stratum

python3 tools/build_crosswalk.py --check             # crosswalk is current
python3 synthetic/generate_scenarios.py --check      # corpus is reproducible
```

## The worked example

`examples/reactor_startup_nonroutine.json` describes a batch reactor restart
after an unplanned trip: an operator who qualified three weeks ago and has not
run this recovery, a recovery sequence not covered by an approved procedure, and
a fixed outage window. Training, scenario familiarity, procedures, and time
pressure are all supplied as degraded.

The engine derives that the task has been displaced to knowledge-based control
while the training supporting that control level is degraded, and that two
distinct degraded factors independently bear on knowledge-based mistakes. Part
of the trace:

```
Screening band: stop-and-review
  Ordinal label only. Produced by rules marked 'convention'. Not a probability, not a rate.

  screeningBand(stop-and-review)  <- R33-band-stop-and-review [convention; no source]
    rule: screeningBand(stop-and-review) :- severelyDegradedFactor(?F),
          not mitigatedFactor(?F), aggravatedErrorMode(?M).
    because: A severely degraded factor occurring alongside an aggravated error
             mode puts the scenario in the stop-and-review band. Threshold chosen
             by the author; no source supports it.
      severelyDegradedFactor(ehs:ScenarioFamiliarity)  <- R02-severely-degraded [literature; nureg2198]
          factorLevel(ehs:ScenarioFamiliarity, ehs:LevelSeverelyDegraded)  [given]
      aggravatedErrorMode(ehs:KnowledgeBasedMistake)  <- R22-aggravated-by-second-factor [literature; groth2012]
        ...
```

Two things to notice. The band rule announces itself as a convention with no
source, because it is one. And the chain bottoms out in `[given]` — facts the
scenario or the ontology supplied — so there is nothing between the input and
the conclusion that a reader cannot inspect.

This is a hand-written illustration. It is not a record of a real event and
contains no site data.

## Methodology

### Ontology

Hand-written Turtle, parsed by a hand-written parser (`src/ehs_hfo/turtle.py`)
because the repository is restricted to the standard library and `rdflib` is not
available. The parser covers the Turtle 1.1 subset the file uses and raises with
a line and column on anything else; what it does not support is listed in its
module docstring.

Alignments are **reified** — each is an individual with a local factor, an
external factor, a match strength and a citation — rather than direct
`skos:closeMatch` triples. That costs verbosity and buys the ability to attach a
source and a caveat to a single correspondence, which is the whole point of the
exercise.

Match strengths are `close`, `broader`, `narrower` and `partial`. `exact` is
declared but deliberately unused, and a test enforces that: asserting exact
identity between factors from frameworks written decades apart for different
industries would claim more than the sources support.

### Rule engine

A bottom-up Datalog evaluator with stratified negation as failure.

- **No function symbols**, so the Herbrand base is finite and evaluation
  terminates.
- **Stratified negation**, checked at construction. A negative dependency inside
  a cycle raises `StratificationError` rather than picking an answer. For a
  stratified program the perfect model is unique and independent of rule order.
- **Range restriction** enforced per rule: a variable in the head, or under
  negation, must be bound by a positive body literal.
- **Deterministic output.** The fact index is seeded in sorted order and
  alternative derivations are canonically sorted, so two runs of the same
  scenario produce byte-identical reports. An audit record that changes between
  runs is not an audit record.
- Data complexity is PTIME. The implementation is naive iteration to a fixpoint
  per stratum, which is ample for twenty factors and twenty-one rules.

Every rule declares a `basis`. `literature` means the proposition appears in the
cited source and the rule must carry a citation — enforced in `Rule.__post_init__`.
`convention` means the author chose a threshold and no source supports it. Every
screening-band rule is `convention`, and a test fails if one ever claims
otherwise. The distinction is printed in every trace, because the difference
between "Rasmussen says so" and "I picked two" is what a reviewer is looking for.

### Unassessed is not nominal

A factor omitted from a scenario is carried as `ehs:LevelUnknown`, never as
nominal, and the report prints assessment coverage. Treating missing data as
satisfactory is the standard way a screening tool understates a hazard, so the
default is the conservative one.

## What an ontology does and does not buy you

Worth being blunt, because "ontology" is a word that does more marketing than
work.

**What it buys.**

- *Fixed identifiers.* `ehs:ScenarioFamiliarity` means one thing. Two analysts
  filling in a spreadsheet column called "familiarity" do not.
- *A place to put provenance.* Every factor carries the source's own wording,
  every alignment carries a citation and a strength, and every gap is an
  assertion someone can argue with.
- *Mechanical checking.* Because it is a data file rather than a diagram, tests
  can enforce that every external factor is accounted for, that every alignment
  is cited, and that the published crosswalk matches the source.
- *A vocabulary the rules are written against*, so a factor cannot be reasoned
  about that the ontology does not declare.

**What it does not buy.**

- *Correctness.* An ontology records assertions. Every claim here is only as good
  as the source it cites or the judgement behind it, and the judgements are one
  person's.
- *Reasoning.* **Nothing in this repository runs an OWL reasoner.** No
  subsumption, no classification, no consistency check. The file has not been
  verified consistent under OWL 2 Direct Semantics, and it is not claimed to be.
  The engine is a Datalog evaluator, which is a different thing with different
  guarantees.
- *Automated reasoning in the computer-science sense.* There is no SMT or
  first-order decision procedure here, no proof certificate in any standard
  format, and no soundness theorem relative to a formal semantics of the domain.
  What there is: a definite semantics for the program evaluated, guaranteed
  termination, and a derivation trace. Calling it more than that would be an
  overclaim.
- *Agreement.* Encoding a boundary does not settle it. IDHEAS-G files procedures
  under Personnel; a practitioner might file them under System or Task. The
  ontology records the choice and notes the disagreement. It does not resolve it.
- *Validation.* Nothing here has been checked against injury or incident
  outcomes.

## Limitations

The ones most likely to matter, in rough order of severity.

1. **No probability, anywhere.** The output is an ordinal screening band
   produced by rules marked `convention`. It is not a human error probability,
   not a rate, and not calibrated against anything. It is not comparable across
   sites and it does not support a threshold for action.
2. **The factor-to-error-mode links are unvalidated.** They are theoretical
   propositions from the cited literature. No effect size is attached to any of
   them and none has been tested against outcome data.
3. **Factor levels are inputs.** An analyst supplies them. The engine cannot
   derive a level from data and cannot tell whether a supplied level is right.
   The traceability is real; the inputs are still judgements.
4. **Domain transfer is not licensed by the sources.** Every framework
   crosswalked here except HSE's was built for nuclear power or aviation.
   NUREG-2198 says existing methods "are not necessarily adequate to model human
   actions ... in other domains." Using this vocabulary in chemical
   manufacturing is an extension, not an application. It is also why SPAR-H's
   multipliers are absent: they were fitted to nuclear operations, and porting
   them elsewhere without revalidation would not be defensible.
5. **The CREAM rows are transcribed at one remove.** Hollnagel's book was not
   consulted; the nine CPCs come from Shirali et al. (2019). Check them against
   the original before relying on them. See `docs/PROVENANCE.md`.
6. **Match strengths are one person's judgement.** No second coder, no
   inter-rater reliability, no adjudication.
7. **The `observableProxy` annotations are speculation.** They suggest what
   might be measured to assess a factor from routinely collected data. None has
   been validated. Read them as a research agenda.
8. **No time-of-day or circadian factor.** CREAM has one; IDHEAS-G does not, so
   neither does this. It is recorded as a coverage gap rather than quietly
   dropped. Closing it honestly would need an exposure denominator by hour of
   shift, which no public dataset supplies — the problem Hanecke et al. (1998)
   had to build estimated exposure models to work around.
9. **Mitigations are counted, never judged.** The engine records that a control
   was claimed. It cannot tell whether it exists or works.
10. **The IRIs do not dereference.** They are stable identifiers, not resolvable
    documents.

## Theoretical position

Worth being explicit, since it is a live argument in the field.

This is an additive contextual-factor model: it treats context as a set of
factors that can each be degraded, and reasons about what follows. Rasmussen
(1997) argues against exactly this style of analysis, in favour of modelling
work-system constraints and boundaries. Leveson's STAMP (2004) treats safety as
constraint enforcement across a control structure rather than as a sum of
contributing factors.

**Neither is cited here as support, because neither supports this.** A paper
invoking STAMP approvingly while building a factor model would be making an
error a reviewer would name. The position taken is narrower: a factor
vocabulary is useful for structuring what an analyst already records, and that
usefulness is not an argument that accidents decompose into factors. If the
systems-theoretic critique is right, the value of this repository is as a
disciplined bookkeeping and traceability layer, not as an accident model.

Similarly, the empirical record on PSF-based quantification is mixed, and the
NRC says so itself. NUREG-2198 reports that the International and U.S. HRA
Empirical Studies "identified three types of HEP variability in a given
scenario: method-to-method, analyst-to-analyst, and crew-to-crew," and names
"weak guidance for performing the qualitative analysis and poor understanding of
performance-influencing factors (PIFs)" among the sources of it. The underlying
international study (NUREG-2127) found method-to-method spreads for a single
human failure event of about one order of magnitude in its loss-of-feedwater
scenarios and up to two in its steam-generator-tube-rupture scenarios, after
censoring outliers.

Being accurate about that study cuts both ways, so: on ranking, NUREG-2127
concluded that "the HRA predictions mostly correlate with the empirical
difficulty," with specific exceptions rather than a general failure. It is
evidence of wide quantitative spread, not evidence that the methods are
uninformative. The spread is reason enough for this repository to quantify
nothing, and that is the only weight put on it here.

## Repository layout

```
ontology/ehs-hfo.ttl        the ontology (hand-written Turtle)
crosswalk/                  generated from the Turtle; do not hand-edit
  crosswalk.md              readable tables, notes, gaps
  crosswalk.csv             one row per correspondence
src/ehs_hfo/
  turtle.py                 dependency-free Turtle 1.1 subset parser
  ontology.py               typed, validated view of the ontology
  facts.py                  facts, patterns, rules, scenarios
  engine.py                 stratified Datalog evaluator with provenance
  rules.py                  the rule base; every rule cited or marked convention
  assessment.py             scenario evaluation and report rendering
  cli.py                    command line interface
tools/build_crosswalk.py    regenerates crosswalk/ from the Turtle
synthetic/                  fabricated corpus + generator (read its README)
examples/                   hand-written worked scenario
tests/                      158 tests, stdlib unittest
docs/PROVENANCE.md          what was read, transcribed, or judged
CITATIONS.md                bibliography with per-entry verification status
```

## Tests

```
python3 -m unittest discover -s tests -t .
```

158 tests, no third-party dependencies. Beyond ordinary unit coverage they
enforce the claims this README makes:

- every external factor is crosswalked, recorded as a gap, or marked out of
  scope with a reason — nothing may be silently dropped
- every alignment cites a source; no alignment claims `exact`
- every citation key resolves to a `CITATIONS.md` entry that declares how it was
  verified, and no entry is unused
- every screening-band rule is marked `convention`
- degrading a factor never improves the band
- the committed crosswalk matches what the ontology generates
- the synthetic corpus is byte-reproducible and every file carries its label
- the same scenario produces a byte-identical report across runs

## Citing

The four-context structure is the NRC's. Cite NUREG-2198 for it, not this
repository. If the encoding or the crosswalk is useful, cite this repository for
those and the underlying frameworks for their content. `CITATIONS.md` gives the
full references with verification status.

Every entry in `CITATIONS.md` records how it was checked, and seven of the twelve
are marked `primary`, meaning the document was retrieved and the specific wording
read in it rather than taken on trust. That includes NUREG-2198, where the
four-context sentence, all twenty PIF names and each PIF's context assignment
were confirmed against the published report. The five that remain `bibliographic`
say so, and `docs/PROVENANCE.md` names the weakest link — the CREAM rows, which
are transcribed at one remove and should be checked against Hollnagel before
anyone quotes them.

## Licence

MIT. See `LICENSE`.

The ontology file is MIT-licensed. The **content** it transcribes belongs to the
cited sources: NUREG-2198, NUREG/CR-6883 and DOT/FAA reports are US government
works; the HSE PIF list is HSE's; CREAM is Hollnagel's. Factor names and short
labels are transcribed as terminology for the purpose of crosswalking. No source
document is reproduced here, and none should be added to this repository.
