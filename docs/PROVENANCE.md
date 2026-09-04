# Provenance

What was read, what was transcribed from somewhere else, and what is asserted on
the author's judgement alone. The purpose of this file is to let a reviewer
attack the weakest link without having to find it first.

## 1. The four context dimensions are not original

This is the single most important statement in the repository, so it is placed
first.

The four context dimensions — Task, Operational, Human, System — are the four
performance-influencing-factor context categories published by the U.S. Nuclear
Regulatory Commission in IDHEAS-G (NUREG-2198, 2021). The report classifies its
20 PIFs "according to the four types of context: environment and situation,
system, personnel, and task."

The correspondence is one to one:

| This ontology | IDHEAS-G | Relation |
| --- | --- | --- |
| Task context | Task | identical label |
| System context | System | identical label |
| Operational context | Environment and situation | synonym |
| Human context | Personnel | synonym |

Two labels are identical and two are synonyms. The twenty factors are
IDHEAS-G's twenty PIFs, adopted without addition, deletion or subdivision.

**Nothing about this taxonomy is new, and the repository does not claim it is.**
The same four-way cut is visible in THERP's internal/external PSF split (1983),
CREAM's nine common performance conditions (1998), SPAR-H's eight PSFs (2005),
the NRC's own 15-PSF good-practice set (NUREG-1792, 2005), HFACS's Preconditions
sub-tree, and HSE's Job/Person/Organisation headings. A reviewer drawn from the
human reliability analysis community would identify the IDHEAS-G correspondence
immediately, and any claim of novelty here would be a straightforward error.

The binding is machine-checkable, not just prose: every
`ehs:ContextDimension` carries `ehs:correspondsToIdheasCategory`, and
`tests/test_ontology.py` fails if a dimension does not name the IDHEAS-G
category it renames.

What this repository does contribute is narrower and is stated in the README:
the encoding is machine-readable, the crosswalk to four other frameworks is
explicit and cited row by row, and every conclusion the engine reaches carries a
derivation trace back to its inputs and its sources.

## 2. Source documents: what was actually read

| Key | Verification | Notes |
| --- | --- | --- |
| `nureg2198` | **primary** | The published report (ADAMS ML21127A272) was retrieved and its text extracted. The four-context sentence was read verbatim; all twenty PIF names were located verbatim; and each PIF's context category was confirmed against the report's own listing (5 environment-and-situation, 3 system, 5 personnel, 7 task). The domain-transfer and HEP-variability quotations were also read. |
| `gertman2005` | **primary** | Retrieved from the NRC and its text extracted. Report numbers, authors, dates and all eight PSF names read in the document, including the parenthesised forms this repository transcribes. Multipliers were not used and were not checked. |
| `hse_pifs` | **primary** | The single-page PDF was retrieved and read in full. All three headings and all 26 factors confirmed verbatim, as was HSE's own "not exhaustive" note. |
| `shappell2006` | **primary** | The FAA report PDF was retrieved, its text extracted, and the taxonomy figure read directly. Report number, six-author list and July 2006 date confirmed. All 28 HFACS category names transcribed here were located verbatim. |
| `shappell2000` | **primary** | The FAA report PDF was retrieved and its text extracted. Report number, both authors and the February 2000 date confirmed, as were the four HFACS levels. 22 of the 28 transcribed category names appear verbatim; the six that do not are recorded in `CITATIONS.md`. |
| `shirali2019` | **primary** | Retrieved and read. Authors, title, *MethodsX* 6:300–315 and DOI 10.1016/j.mex.2019.02.008 confirmed. The nine CREAM CPC labels were read in the article text. |
| `folkard2003` | **primary** | Full text retrieved; the sentence on risk by time on shift was read verbatim. Identifiers confirmed by DOI resolution. |
| `hollnagel1998` | bibliographic + **secondary** | See section 3. |
| `groth2012` | bibliographic | DOI resolves to exactly this record. Article text not read. Supports the partial-match caveat and rule R22. |
| `rasmussen1983` | bibliographic | DOI resolves to exactly this record. Article text not read. Supports the three control levels. |
| `reason1990` | bibliographic | Book; text not consulted. Supports the error-mode classes. |
| `hanecke1998` | bibliographic | Identifiers confirmed against the journal's record and the published abstract read. Full article not retrieved. Cited only in support of a stated limitation. |

Seven of the twelve entries are `primary`, meaning the document was retrieved and
the specific wording read in it. This was done as a separate verification pass by
someone who did not write the ontology, and it closes what was previously flagged
as the highest-value outstanding check: the NUREG-2198 four-context sentence, on
which the central claim of this repository rests, has now been read in
NUREG-2198 itself rather than taken on trust.

`CITATIONS.md` carries the full entries. `tests/test_citations.py` fails if any
key used in the ontology or the rule base has no entry, if any entry is unused,
or if any entry omits its verification state.

### The HFACS version question

Two HFACS reports matter and they differ where this crosswalk touches them.

The 2000 report (DOT/FAA/AM-00/7) subdivides *Preconditions for Unsafe Acts*
into substandard conditions and substandard practices of operators. The revised
taxonomy figured in the 2006 report (DOT/FAA/AM-06/18, "Figure 2. The HFACS
framework.") uses three groups instead:

- *Condition of Operators* — Physical/Mental Limitations, Adverse Mental States,
  Adverse Physiological States
- *Environmental Factors* — Technological Environment, Physical Environment
- *Personnel Factors* — Personal Readiness, Crew Resource Management

**This crosswalk maps to the 2006 arrangement**, and `xw:fw-HFACS` says so. A
reader checking these rows against the 2000 report will not find some of the
category names, and that is the reason. The 2006 figure was read directly in the
retrieved PDF rather than taken from a secondary description.

Both reports have since been checked line by line against the 28 category names
transcribed here. All 28 appear verbatim in the 2006 report. Six do not appear in
the 2000 report: the five Preconditions groups listed above, plus **Failed to
Correct Problem**, which the 2000 report calls *failed to correct a known
problem*. `xw:hfacs-FailedToCorrectProblem` cites both reports and carries the
2006 wording as its `ehs:verbatimLabel`.

## 3. The CREAM transcription, which is the weakest link

Hollnagel's *CREAM* (1998) is a book and **the book text was not consulted**.
The nine Common Performance Conditions in section 10.3 of the Turtle file were
transcribed from Shirali et al. (2019, *MethodsX*), an open-access paper that
reproduces them.

This is recorded three times — here, on `xw:fw-CREAM` in the ontology, and in
`CITATIONS.md` — because a transcription at one remove can go wrong in ways the
transcriber cannot see. Anyone relying on the CREAM rows should check them
against Hollnagel directly before quoting them. Shirali et al. are cited as a
transcription source, not as authority for CREAM.

## 4. What the match strengths are, and are not

Every alignment carries one of five strengths: exact, close, broader, narrower,
partial. These are **analyst judgements made by one person against transcribed
source wording**. They are not measured agreement. There is no second coder, no
inter-rater reliability statistic, and no adjudication procedure. Nobody has
checked them but the author.

No alignment is marked `exact`, and `tests/test_crosswalk.py` enforces that. The
frameworks were written independently, decades apart, for different industries.
Groth and Mosleh (2012) report that PIFs across methods are not defined
specifically enough for consistent interpretation across them. Asserting exact
identity between two such factors would claim more than the sources support.

The `partial` rows are where that imprecision bites hardest and are the rows
most worth arguing with. They are listed individually in
`crosswalk/crosswalk.md` under "Notes on individual rows".

## 5. What is original to this repository

Four things, and they are small:

1. **The `ehs:observableProxy` annotations.** Suggestions of what might be
   measured to assess each factor from routinely collected industrial data.
   These are **proposals and are entirely unvalidated**. No proxy has been
   tested against any outcome. They are the most speculative content in the
   file and should be read as a research agenda, not as a method.
2. **The rules marked `convention`.** Every screening-band threshold. No source
   supports any of them; the author picked them. The engine prints
   `[convention; no source]` next to these in every trace, and
   `tests/test_rules.py` fails if a banding rule ever claims literature support.
3. **The crosswalk row selection and strengths.** Which external factor a local
   factor corresponds to, and how closely. See section 4.
4. **The coverage-gap assertions.** Which external factors are recorded as
   uncovered, including the judgement that a partial overlap does not count as
   coverage.

Everything else is adopted from the cited sources.

## 6. Data provenance

**There is no empirical data in this repository.** Nothing here was computed
from OSHA filings, incident records, or any employer's data.

- `examples/reactor_startup_nonroutine.json` is a hand-written illustration. It
  is not a record of any real event and contains no site data.
- `synthetic/scenarios/` is fabricated by a seeded generator. See
  `synthetic/README.md`. No number computed from it is an empirical finding.

The author's prior work on OSHA ITA establishment filings
(`github.com/priyatham9/ehs-benchmarks`) is separate. It is a data-quality
analysis of regulatory filings and **is not evidence for anything in this
repository**. The two should not be conflated: nothing here has been validated
against injury outcomes, and the OSHA work says nothing about performance
shaping factors.

## 7. What has not been validated

Stated plainly, because these are the questions a reviewer will ask:

- **No factor-to-error-mode link has been validated against outcome data.** The
  `ehs:predisposesTo` assertions are theoretical propositions from the cited
  literature. No effect size is attached to any of them.
- **The screening bands are not calibrated.** They are ordinal labels. They have
  never been compared against injury or incident rates, and the repository
  computes no probability, rate or human error probability of any kind.
- **Factor levels are inputs, not outputs.** The engine does not derive a level
  from data and cannot check whether a supplied level is right. Garbage in,
  traceable garbage out.
- **Mitigations are counted, never judged.** The engine records that a control
  was claimed against a factor. It has no way to assess whether the control
  exists, works, or is being followed.
- **No inter-rater reliability has been established** for either the crosswalk
  strengths or the factor levels an analyst would assign.
- **The OWL file has not been checked for consistency by an OWL reasoner.**
  Nothing in this repository computes entailments. No claim is made that the
  file is consistent under OWL 2 Direct Semantics. See the README section on
  what an ontology does not buy you.

## 8. Domain transfer

Every framework crosswalked here except HSE's was developed for either nuclear
power operations or commercial aviation. NUREG-2198 states that existing methods
"were developed for a procedure-based response to internal events occurring
at-power in NPPs" and "are not necessarily adequate to model human actions ... in
other domains."

Applying this vocabulary to general chemical manufacturing is therefore an
extension the source documents do not license, and it is not validated here. It
is one reason SPAR-H's multipliers are deliberately absent: they were estimated
from nuclear power plant data, and transferring them to another sector without
revalidation would be an unjustified move that no evidence in this repository
supports.
