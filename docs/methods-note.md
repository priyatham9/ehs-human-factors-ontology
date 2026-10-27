# A traceable crosswalk of IDHEAS-G performance-influencing factors to SPAR-H, CREAM, HFACS and the HSE PIF list

Methods note. Priyatham Chimmani. Version 0.1.0 of `ehs-human-factors-ontology`.

## Abstract

Human reliability analysis (HRA) and incident investigation use several
overlapping taxonomies of the conditions that shape human performance. Each
method names and groups those conditions differently, so findings coded in one
taxonomy are hard to compare with findings coded in another. This note
describes a machine-readable crosswalk from the 20 performance-influencing
factors (PIFs) of IDHEAS-G (NUREG-2198) to the factor inventories of SPAR-H,
CREAM, HFACS and the UK Health and Safety Executive (HSE) PIF list. The four
context categories and the 20 PIFs are adopted from IDHEAS-G without change and
are not claimed as new. The contribution is the crosswalk itself (90
factor-level alignments, each with a declared match strength and a citation),
explicit records of absence and of coverage gaps, automated checks that keep
those records complete and consistent, and a small rule engine that reasons
over the same vocabulary and records the derivation of every conclusion. All
figures in the results section are computed from the repository by a script
and checked by a test. The alignments are the judgement of a single author and
have not been tested for inter-rater reliability or against real incidents.

## 1 Background

Most HRA methods describe the context of a human action through a set of
factors that make error more or less likely. SPAR-H calls them performance
shaping factors and uses eight (Gertman et al. 2005). CREAM uses nine common
performance conditions (Hollnagel 1998). HFACS, built for accident
investigation rather than prediction, classifies preconditions, supervisory
factors and organisational influences in a layered taxonomy (Shappell and
Wiegmann 2000; Shappell et al. 2006). HSE guidance groups performance
influencing factors under job, person and organisation (HSE 1999; HSE PIF
list). IDHEAS-G organises 20 PIFs into four context categories: environment
and situation, system, personnel, and task (NRC 2021).

These sets differ in size and in where they draw boundaries. Boring (2010)
reviews the range of PSF set sizes in use, and Groth and Mosleh (2012) report
that PIFs across methods are not defined precisely enough to be interpreted
consistently and that there is no standard set. For incident analysis this
matters in a practical way. An organisation that codes investigations in HFACS
cannot directly reuse an HRA built on SPAR-H or IDHEAS-G, and a reviewer
comparing two analyses has to translate between vocabularies by hand, usually
without a record of how each term was mapped. A published crosswalk with a
stated strength and source for each correspondence makes that translation
explicit and open to challenge.

## 2 What is adopted and what this work adds

### 2.1 Adopted from IDHEAS-G

The four-context structure and the 20 PIFs come from NUREG-2198. The local
labels map to IDHEAS-G as follows: Task context to Task (identical), System
context to System (identical), Operational context to Environment and situation
(synonym), Human context to Personnel (synonym). Each PIF keeps its NUREG-2198
wording in a `verbatimLabel` field and its NUREG-2198 context assignment. The
idea of grouping PIFs into a few context categories is also older than this
work and older than IDHEAS-G. None of this is claimed as original, and the
repository README states so first.

The five macrocognitive functions and their failure modes used by the rule
engine are also IDHEAS-G concepts. The assignment of each PIF to the functions
it affects is the author's reading of NUREG-2198 and is labelled as such in the
ontology and in `docs/COMPATIBILITY.md`.

### 2.2 Added by this work

1. **The crosswalk.** Each of the 20 PIFs is mapped to its counterparts in
   SPAR-H, CREAM, HFACS and the HSE PIF list. Every alignment is a separate,
   addressable record carrying the local factor, the external factor, a match
   strength and one or more citation keys.
2. **Alignment types and rationale.** Match strengths are `close`, `broader`,
   `narrower` and `partial`, defined in `crosswalk/crosswalk.md`. A fifth value,
   `exact`, is defined but deliberately unused, and a test enforces that.
   Alignments that needed qualifying carry a written note explaining the
   judgement, for example where one IDHEAS-G factor spans two SPAR-H factors.
3. **Absence and gap records.** Where a framework has no counterpart for a
   local factor, the ontology asserts that absence rather than leaving a blank.
   Where an external factor has no local counterpart, a coverage gap record says
   so with a reason. External entries that are outcomes, headings or containers
   rather than context factors are marked out of scope with a reason.
4. **Automated consistency checks.** Tests require every external entry to be
   aligned, recorded as a gap, or marked out of scope; every alignment to cite
   a source; every citation key to resolve to a bibliography entry that states
   how it was verified; and the published crosswalk tables to match what the
   ontology generates.
5. **A rule engine over the same vocabulary.** A stratified Datalog evaluator
   reasons over factor levels supplied for a scenario and records, for each
   derived fact, the rule and the facts that produced it. Each rule declares
   whether it rests on cited literature or on an author's convention.

## 3 Method for building and checking alignments

**Transcription.** The external inventories were transcribed from the source
documents listed in `CITATIONS.md`, keeping each source's own wording in a
`verbatimLabel` field. Each bibliography entry records whether the document
itself was read (`primary`), only its bibliographic record was confirmed
(`bibliographic`), or its content was taken from an intermediary
(`secondary`). The CREAM conditions are the weakest link: they were transcribed
from Shirali et al. (2019) rather than from Hollnagel (1998), and
`docs/PROVENANCE.md` says so.

**Assigning a match.** For each pair of local PIF and external framework, the
author compared the NUREG-2198 description of the PIF with the external
factor's wording and scope, then chose the strength that best described the
relation: `close` for the same construct with differences unlikely to change
an assessment, `broader` when the external factor subsumes the local one,
`narrower` when it covers only part, and `partial` for overlapping but
non-nested constructs. A local factor may align to more than one external
factor in the same framework. Where no external factor fitted, an absence was
asserted. HFACS was mapped to the revised taxonomy shown in Shappell et al.
(2006), and the ontology notes the differences from the 2000 report.

**Encoding.** The alignments are stored in `ontology/ehs-hfo.ttl` as reified
individuals rather than direct mapping triples, so that each correspondence
can hold its own strength, citation and note. `tools/build_crosswalk.py`
renders `crosswalk/crosswalk.md` and `crosswalk/crosswalk.csv` from the Turtle
file, and the test suite fails if the committed files differ from the
generated ones.

**Checking.** The checks listed in section 2.2 run in the repository's unit
test suite. They establish internal completeness and consistency. They do not
establish that any single judgement is correct.

**Computing the results.** Every figure in section 4 is produced by
`tools/methods_note_stats.py`, which reads the ontology, the rule base and the
worked example. The script writes the block between the two marker comments
below, and `tests/test_methods_note.py` fails if that block, or the headline
figures quoted in the abstract, no longer match the data. To refresh after a
data change, run `python3 tools/methods_note_stats.py --write`.

## 4 Results

The tables below are generated. The text after them comments on them without
introducing further figures.

<!-- BEGIN GENERATED BY tools/methods_note_stats.py; do not hand-edit -->

**Table 1. Alignments by framework and match strength.**

| Framework | close | broader | narrower | partial | exact | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| SPAR-H | 7 | 2 | 0 | 7 | 0 | 16 |
| CREAM | 7 | 8 | 0 | 7 | 0 | 22 |
| HFACS | 6 | 8 | 0 | 9 | 0 | 23 |
| HSE PIF list | 14 | 5 | 0 | 10 | 0 | 29 |
| **All** | 34 | 23 | 0 | 33 | 0 | 90 |

**Table 2. Alignments by context dimension.**

| Dimension | IDHEAS-G category | Factors | Alignments |
| --- | --- | ---: | ---: |
| Human context | Personnel | 5 | 28 |
| Operational context | Environment and situation | 5 | 17 |
| System context | System | 3 | 12 |
| Task context | Task | 7 | 33 |

**Table 3. Coverage of each external inventory.** An entry can be both
aligned and recorded as a gap when the only alignment is partial and the
construct itself is judged missing.

| Framework | Entries | Aligned to a local factor | Recorded gap | Gap and aligned | Out of scope |
| --- | ---: | ---: | ---: | ---: | ---: |
| SPAR-H | 8 | 8 | 0 | 0 | 0 |
| CREAM | 9 | 9 | 1 | 1 | 0 |
| HFACS | 28 | 11 | 3 | 0 | 14 |
| HSE PIF list | 29 | 23 | 3 | 0 | 3 |
| IDHEAS-G | 4 | 0 | 0 | 0 | 4 |

**Table 4. Local factors with an asserted absence in a framework.**

| Local factor | Framework with no counterpart |
| --- | --- |
| Noise and communication pathways | SPAR-H |
| Resistance to physical movement | SPAR-H |
| Scenario familiarity | HFACS |
| Thermal conditions | SPAR-H |
| Workplace accessibility and habitability | SPAR-H |
| Workplace visibility | SPAR-H |

**Table 5. External entries recorded as coverage gaps.**

| External entry | Framework | Also has a partial alignment |
| --- | --- | --- |
| Effectiveness of organisational learning | HSE PIF list | no |
| Failed to correct problem | HFACS | no |
| Motivation vs. other priorities | HSE PIF list | no |
| Peer pressure | HSE PIF list | no |
| Personal readiness | HFACS | no |
| Supervisory violations | HFACS | no |
| Time of day (circadian rhythm) | CREAM | yes |

**Summary figures.**

- Local factors: 20 in 4 context dimensions.
- External entries transcribed: 78 across 5 frameworks.
- Factor-level alignments: 90.
- Asserted absences (no counterpart): 6.
- Local factors aligned in 4 of 4 frameworks: 14.
- Local factors aligned in 3 of 4 frameworks: 6.
- Local factors with no counterpart in any of the 4 frameworks: 0.
- Alignments per local factor: minimum 3, maximum 9 (Team and organisation factors).
- Rules: 24, of which 18 are marked `literature` and 6 `convention`.

**Worked example output** (`examples/reactor_startup_nonroutine.json`).

- Factors assessed: 20 of 20.
- Screening band: `stop-and-review`.
- Aggravated failure modes: failure of decisionmaking, failure of understanding.
- Aggravated error modes: knowledge-based mistake, rule-based mistake.
- Unsupported control demands: knowledge-based control.
- Degraded factors with no mitigation claimed: Procedures, guidance and instructions, Scenario familiarity, Time pressure and stress, Training.
- Distinct rules fired: 21 of 24.

<!-- END GENERATED -->

**Reading the results.** Close and partial alignments are about equally
common, and no alignment is claimed as exact. The HSE list attracts the most
alignments because several of its factors are fine-grained where IDHEAS-G is
coarse, most visibly for team and organisation factors. HFACS has the largest
out-of-scope share because much of its inventory classifies unsafe acts, which
are outcomes rather than context; those are modelled as error modes instead.

All five asserted absences against SPAR-H fall in the operational context.
SPAR-H has no PSF for the physical work environment that IDHEAS-G divides into
several factors. The one HFACS absence is scenario familiarity, which HFACS
does not treat as a precondition.

The coverage gaps run the other way: they are external constructs with no
IDHEAS-G factor. Supervisory failures in HFACS, and motivation, peer pressure
and organisational learning in the HSE list, are outside the twenty PIFs. Time
of day in CREAM is recorded as a gap even though mental fatigue has a partial
alignment to it, because the two are different constructs. Every local factor
has a counterpart in at least three of the four frameworks.

## 5 Example scenario through the rule engine

The worked example in `examples/reactor_startup_nonroutine.json` is a
hand-written illustration, not a record of a real event. It describes a batch
reactor restart after an unplanned trip. The operator qualified three weeks
earlier and has not run this recovery, the recovery sequence is not covered by
an approved procedure, and the outage window is fixed. Scenario familiarity is
supplied as severely degraded; training, procedures, and time pressure and
stress as degraded; the other sixteen factors as nominal.

To run it:

```
PYTHONPATH=src python3 -m ehs_hfo assess examples/reactor_startup_nonroutine.json
```

The engine's summary for this scenario is reproduced in the last part of the
generated block in section 4. Three points about how it gets there:

1. Degraded scenario familiarity raises demand on knowledge-based control
   (`R10-control-demand`), and because training is also degraded that demand
   is recorded as unsupported (`R11-unsupported-demand`). Two distinct degraded factors point at knowledge-based
   mistakes, so that error mode is recorded as aggravated. The rule that does
   this (`R22-aggravated-by-second-factor`) says two routes to the same failure
   class are open. It does not say the risk has doubled.
2. At the level of IDHEAS-G macrocognitive functions, understanding and
   decisionmaking are aggravated and action execution is elevated. Detection
   and interteam coordination are untouched.
3. The `stop-and-review` band is produced by rule `R33-band-stop-and-review`,
   which is marked `convention` with no source. The trace prints that marking.
   An excerpt of the trace as the command prints it:

```
screeningBand(stop-and-review)  <- R33-band-stop-and-review [convention; no source]
  rule: screeningBand(stop-and-review) :- severelyDegradedFactor(?F), not mitigatedFactor(?F), aggravatedErrorMode(?M).
    severelyDegradedFactor(ehs:ScenarioFamiliarity)  <- R02-severely-degraded [literature; nureg2198]
      factorLevel(ehs:ScenarioFamiliarity, ehs:LevelSeverelyDegraded)  [given]
    aggravatedErrorMode(ehs:KnowledgeBasedMistake)  <- R22-aggravated-by-second-factor [literature; groth2012]
```

The band is an ordinal label. It is not a human error probability, and no
SPAR-H multiplier or other quantification is used anywhere in the repository.

## 6 Rule-based narrative suggester and its first evaluation

`python -m ehs_hfo suggest` takes incident narrative text and returns candidate
PIFs. It uses keyword and phrase rules only, with no learned component. A
curated set of 97 rules (`crosswalk/pif_rules.csv`) pairs a phrase with a PIF
and with an external SPAR-H, CREAM, HFACS or HSE factor that the ontology
aligns to that PIF; a test fails if the alignment is missing, so each hit can be
read back through the crosswalk to a citation. A second, baseline set is derived
by code from the ontology's own labels: a stemmed word becomes a rule for a PIF
if it occurs in that PIF's label vocabulary and in no other PIF's.

The evaluation compares each set with the PIFs hand-coded for 23 CSB
investigations in `incidents/` (67 investigation-PIF pairs over 10 PIFs). The
only incident text in the repository is the set of quoted passages those codings
rest on, so the "narrative" for an investigation is its concatenated quotes. The
investigations fall into two cohorts. The development cohort (10 investigations,
25 pairs) was coded before the rules were written; the author had read those
quotes, so the curated scores on it are resubstitution and optimistic, and a
variant without the 11 rules whose phrase was taken from the quotes is reported
beside it. The held-out cohort (13 investigations, 42 pairs) was coded afterwards
from 15 further CSB investigations, with the rules frozen first, and is a genuine
out-of-sample test. Three caveats apply to both. Recall measures whether the
rules' vocabulary reaches words a coder already pointed at, not discovery in
free-running narratives; the held-out passages were also chosen by looking for
text on each factor's topic and are mostly recommendation wording from summary
pages, which inflates recall. The same person coded both cohorts and wrote the
rules. The gold labels are incomplete (a PIF is coded only when a passage was
quoted for it), so a false positive may be a real condition nobody coded.

Results are in `incidents/suggester_eval.md` and `docs/suggester.html`, both
generated and tested. On the development cohort, the untuned baseline recovered
5 of 25 pairs (precision 0.31); the curated set recovered 20 of 25 (precision
0.74, recall 0.80); the curated set without the quote-derived phrases recovered
14 of 25 (precision 0.74, recall 0.56). On the held-out cohort, the baseline
recovered 10 of 42 pairs (precision 0.42); the curated set recovered 30 of 42
(precision 0.86, recall 0.71). A control that always predicts the most frequent
development PIF (team and organisation factors) scored precision 0.69 and recall
0.21 on the held-out cohort. The earlier figures therefore held up out of sample
in kind: recall fell from 0.80 to 0.71 and precision rose from 0.74 to 0.86, but
it stayed above the 0.56 of the development-derived-phrase-free variant, which is
the fairer comparison. Time pressure and stress (2 held-out pairs) was missed
both times. Ten of the 20 PIFs have gold coding in either cohort, so the rules
for the other ten remain untested. With 42 held-out pairs one pair moves recall
by about 2.4 points, and no confidence interval is claimed. A stronger test
needs full-report narratives coded by someone other than the rule author.

## 7 Limitations

1. **Single author.** Every match strength, every asserted absence and every
   PIF-to-function assignment is one person's judgement. No second coder
   reviewed them.
2. **No inter-rater reliability.** Because there was one coder, there is no
   agreement statistic to report. The strengths should be read as a proposal
   to be tested, not as measured agreement.
3. **No validation on real incidents.** Neither the crosswalk nor the rule
   engine has been applied to coded incident reports or compared with
   investigation outcomes. The worked example and the synthetic corpus in
   `synthetic/` are fabricated and labelled as such.
4. **Secondary transcription for CREAM.** The CREAM conditions were taken from
   Shirali et al. (2019), not from Hollnagel (1998) directly.
5. **Domain transfer.** IDHEAS-G, SPAR-H and CREAM were developed mainly for
   nuclear power and HFACS for aviation. Using the vocabulary in chemical
   manufacturing or general industry is an extension that the sources do not
   themselves license.
6. **Convention-based banding.** The screening bands rest on thresholds the
   author chose. They are labelled as such and are not calibrated.
7. **Factor levels are inputs.** The engine reasons from levels an analyst
   supplies and cannot check whether those levels are right.

## 8 References

Each entry below was checked against the issuing body, the publisher, or the
DOI record during preparation of this note. Fuller verification notes for the
entries the code relies on are in `CITATIONS.md`.

- Boring, R.L. (2010). How many performance shaping factors are necessary for
  human reliability analysis? *10th International Probabilistic Safety
  Assessment and Management Conference (PSAM10)*, Seattle, WA.
  INL/CON-10-18620. OSTI 1010682.
- Gertman, D.I., Blackman, H.S., Marble, J.L., Byers, J.C. and Smith, C.L.
  (2005). *The SPAR-H Human Reliability Analysis Method.* NUREG/CR-6883,
  INL/EXT-05-00509. Washington, DC: U.S. Nuclear Regulatory Commission.
- Groth, K.M. and Mosleh, A. (2012). A data-informed PIF hierarchy for
  model-based human reliability analysis. *Reliability Engineering and System
  Safety*, 108, 154-174. https://doi.org/10.1016/j.ress.2012.08.006
- Health and Safety Executive (1999). *Reducing Error and Influencing
  Behaviour.* HSG48. Sudbury: HSE Books. ISBN 978-0-7176-2452-2.
- Health and Safety Executive (n.d.). *Performance Influencing Factors (PIFs).*
  https://www.hse.gov.uk/humanfactors/assets/docs/pifs.pdf
- Hollnagel, E. (1998). *Cognitive Reliability and Error Analysis Method
  (CREAM).* Oxford: Elsevier. ISBN 978-0-08-042848-2.
- Shappell, S.A. and Wiegmann, D.A. (2000). *The Human Factors Analysis and
  Classification System (HFACS).* DOT/FAA/AM-00/7. Washington, DC: Federal
  Aviation Administration, Office of Aviation Medicine.
- Shappell, S., Detwiler, C., Holcomb, K., Hackworth, C., Boquet, A. and
  Wiegmann, D. (2006). *Human Error and Commercial Aviation Accidents: A
  Comprehensive, Fine-Grained Analysis Using HFACS.* DOT/FAA/AM-06/18.
  Washington, DC: Federal Aviation Administration, Office of Aerospace
  Medicine.
- Shirali, G.A., Hosseinzadeh, T., Ahamadi Angali, K. and Rostam Niakan
  Kalhori, S. (2019). Modifying a method for human reliability assessment
  based on CREAM-BN: a case study in control room of a petrochemical plant.
  *MethodsX*, 6, 300-315. https://doi.org/10.1016/j.mex.2019.02.008
- U.S. Nuclear Regulatory Commission (2021). *The General Methodology of an
  Integrated Human Event Analysis System (IDHEAS-G).* NUREG-2198. Prepared by
  J. Xing, Y.J. Chang and J. DeJesus Segarra. Washington, DC: Office of Nuclear
  Regulatory Research. ADAMS ML21127A272.

## 9 Suggested citation

Chimmani, P. (2026). *A traceable crosswalk of IDHEAS-G performance-influencing
factors to SPAR-H, CREAM, HFACS and the HSE PIF list* (methods note, version
0.1.0). ehs-human-factors-ontology.
https://github.com/priyatham9/ehs-human-factors-ontology/blob/main/docs/methods-note.md

When the four-context structure or the twenty PIFs are what is being relied
on, cite NUREG-2198 for them. Cite this note for the crosswalk, the alignment
records and the checking method.
