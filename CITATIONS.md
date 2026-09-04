# Citations

Every `ehs:sourceRef` in `ontology/ehs-hfo.ttl`, and every `source_refs` entry on a
rule in `src/ehs_hfo/rules.py`, is a key in this file. The keys are the only
citation mechanism in the repository; `tests/test_citations.py` fails if a key is
used anywhere in the ontology or the rule base without an entry here.

## Verification status

Each entry records how it was checked. Three states are used and they are not
interchangeable.

| State | Meaning |
| --- | --- |
| `primary` | The source document itself was retrieved and the specific claim was read in it. |
| `bibliographic` | Existence, authorship, venue and identifiers confirmed against the publisher, the issuing agency, or a DOI resolution. The specific passage was not read in the original. |
| `secondary` | The content used here was transcribed from another publication that quotes or reproduces it, because the original was not consulted. The intermediary is named. |

Nothing in this repository is cited at a strength above what its verification
state supports. Where the ontology depends on a `secondary` transcription, the
Turtle file says so at the point of use, and `docs/PROVENANCE.md` explains why.

**Independent verification pass.** Every entry below was re-checked against the
source document by a reviewer who did not write the ontology. Seven of the twelve
are now `primary`: the document was retrieved at the URL or ADAMS accession
number given in its entry, its text extracted, and the specific wording this
repository transcribes read in it. Where that pass upgraded a state, the entry
says exactly what was read; where it could not, the state was left alone. No
claim was upgraded on the strength of a search result, an abstract, or a
secondary description. The five that remain `bibliographic` are the two books
(`hollnagel1998`, `reason1990`) and three articles whose identifiers resolve
exactly but whose text was not retrieved (`groth2012`, `rasmussen1983`,
`hanecke1998`).

---

## Frameworks crosswalked

### `nureg2198`

U.S. Nuclear Regulatory Commission (2021). *The General Methodology of an
Integrated Human Event Analysis System (IDHEAS-G).* NUREG-2198. Washington, DC:
Office of Nuclear Regulatory Research. Manuscript completed November 2020;
published May 2021. ADAMS accession ML21127A272.

**Verification:** primary. The published report was retrieved from the NRC
(ML21127A272) and its text extracted. The title page confirms "Manuscript
Completed: November 2020" and "Date Published: May 2021". The four-context
sentence quoted below was read verbatim in Section 3, in the passage describing
the four-layer PIF structure. All twenty PIF names transcribed in section 8 of
the Turtle file were located verbatim, and each one's assignment to a context
category was confirmed against the report's own listing: five environment-and-
situation PIFs, three system, five personnel, seven task. The domain-transfer
and HEP-variability sentences quoted below were also read in the document.

**What it supports here.** The entire four-context structure, and therefore the
central claim of this repository — that the structure is adopted rather than
invented. IDHEAS-G organises 20 PIFs into exactly four context categories, and
states it in these words:

> "PIFs are classified according to the four types of context: environment and
> situation, system, personnel, and task."

The twenty factors in section 8 of the Turtle file are those twenty PIFs. It is
also the source for the NRC's own account of where human reliability analysis is
weak: HEP variability is described as method-to-method, analyst-to-analyst and
crew-to-crew, with "weak guidance for performing the qualitative analysis and
poor understanding of performance-influencing factors" named as key causes. And
for the domain-transfer caveat this repository leans on heavily: existing
methods "were developed for a procedure-based response to internal events
occurring at-power in NPPs" and "are not necessarily adequate to model human
actions ... in other domains."

### `gertman2005`

Gertman, D.I., Blackman, H.S., Marble, J.L., Byers, J.C. & Smith, C.L. (2005).
*The SPAR-H Human Reliability Analysis Method.* NUREG/CR-6883,
INL/EXT-05-00509. Washington, DC: U.S. Nuclear Regulatory Commission.
Manuscript completed September 2004; published August 2005.

**Verification:** primary. Retrieved from the NRC at
<https://www.nrc.gov/reading-rm/doc-collections/nuregs/contract/cr6883/cr6883.pdf>
and its text extracted. Report numbers, the five-author list and both dates were
read in the document. The eight PSFs were read in the passage stating that "in
1999, further research identified eight PSFs capable of influencing human
performance", and the two parenthesised forms this repository transcribes —
"Procedures (including job aids)" and "Ergonomics (including the human-machine
interface)" — were both located verbatim.

**What it supports here.** The eight SPAR-H performance shaping factors
transcribed in section 10.2 of the Turtle file: available time; stress;
experience and training; complexity; ergonomics (human-machine interface);
procedures; fitness for duty; work processes.

SPAR-H's multipliers are **not** used anywhere in this repository. They are
derived from nuclear power plant data and this repository makes no argument that
they transfer to general chemical manufacturing. Only the factor names are
crosswalked.

### `hollnagel1998`

Hollnagel, E. (1998). *Cognitive Reliability and Error Analysis Method (CREAM).*
Oxford: Elsevier Science.

**Verification:** bibliographic for the book; the nine Common Performance
Conditions used in section 10.3 are **secondary**, transcribed from
`shirali2019` (below), which reproduces them. The book text was not consulted.

**What it supports here.** The nine CPCs: adequacy of organisation; working
conditions; adequacy of man-machine interface and operational support;
availability of procedures and plans; number of simultaneous goals; available
time; time of day; adequacy of training and experience; crew collaboration
quality.

`ehs:TimeOfDay` has no local counterpart and is recorded as a coverage gap
(`xw:gap-cream-TimeOfDay`) rather than quietly dropped.

### `shirali2019`

Shirali, G.A., Hosseinzadeh, T., Ahamadi Angali, K. & Rostam Niakan Kalhori, S.
(2019). Modifying a method for human reliability assessment based on CREAM-BN: A
case study in control room of a petrochemical plant. *MethodsX*, 6, 300–315.
DOI: 10.1016/j.mex.2019.02.008. PMC6384312.

**Verification:** primary. Retrieved and read; author list, title, journal,
volume, page range and DOI confirmed, and the nine CPC labels were read in the
article text. Independently re-verified: the DOI resolves to exactly this
record, and all nine CPC labels were read again in the open-access full text at
PMC6384312, matching this repository's transcription including "Time of the
day".

**What it supports here.** It is the intermediary through which CREAM's nine
CPCs were transcribed. It is cited as a transcription source only. It is an
open-access secondary source, not the authority for CREAM — Hollnagel is — and
the Turtle file records the substitution at `xw:fw-CREAM`.

### `shappell2000`

Shappell, S.A. & Wiegmann, D.A. (2000). *The Human Factors Analysis and
Classification System — HFACS.* Report No. DOT/FAA/AM-00/7. Washington, DC:
Office of Aviation Medicine, Federal Aviation Administration. February 2000.

**Verification:** primary. The report PDF was retrieved from the FAA at
<https://www.faa.gov/sites/faa.gov/files/data_research/research/med_humanfacs/oamtechreports/00_07.pdf>
and its text extracted. Report number, both authors, the issuing office and the
February 2000 date were read in the document, as were the four HFACS levels.

**What it supports here.** The four HFACS levels: Unsafe Acts; Preconditions for
Unsafe Acts; Unsafe Supervision; Organizational Influences. Also the two
supervisory categories recorded as coverage gaps
(`xw:gap-hfacs-FailedToCorrectProblem`, `xw:gap-hfacs-SupervisoryViolations`).

**Where the 2000 wording differs, precisely.** Of the 28 HFACS category names
transcribed in section 10.4 of the Turtle file, 22 appear verbatim in this 2000
report and six do not. Five of the six are the Preconditions groups introduced by
the 2006 revision — *Environmental Factors*, *Physical Environment*,
*Technological Environment*, *Condition of Operators* and *Personnel Factors* —
which is the version difference already described under `shappell2006` and in
`docs/PROVENANCE.md`. The sixth is narrower and is recorded here so it is not
mistaken for a transcription error: this repository uses the 2006 wording
**Failed to Correct Problem**, whereas the 2000 report calls the same category
*failed to correct a known problem*. `xw:hfacs-FailedToCorrectProblem` cites both
reports; its `ehs:verbatimLabel` is the 2006 form.

### `shappell2006`

Shappell, S., Detwiler, C., Holcomb, K., Hackworth, C., Boquet, A. & Wiegmann,
D. (2006). *Human Error and Commercial Aviation Accidents: A Comprehensive,
Fine-Grained Analysis Using HFACS.* DOT/FAA/AM-06/18. Washington, DC: FAA Office
of Aerospace Medicine. July 2006.

**Verification:** primary. The report PDF was retrieved from the FAA and its
text extracted. Title, six-author list, report number and July 2006 date were
read in the document. The taxonomy figure, captioned "Figure 2. The HFACS
framework.", was located and its Preconditions sub-tree read directly.
Independently re-verified from the same FAA PDF: the report number, the July
2006 date, all six author surnames, the issuing office and the figure caption
were confirmed, and all 28 HFACS category names transcribed in section 10.4 of
the Turtle file were located verbatim in the report text.

**What it supports here.** The **revised** HFACS taxonomy, which is the version
this crosswalk maps to. Under *Preconditions for Unsafe Acts* the 2006 figure
shows three groups, confirmed in the document text:

- *Condition of Operators* — Physical/Mental Limitations, Adverse Mental States,
  Adverse Physiological States
- *Environmental Factors* — Technological Environment, Physical Environment
- *Personnel Factors* — Personal Readiness, Crew Resource Management

This differs from the 2000 report, which subdivides Preconditions into
substandard conditions and substandard practices of operators. The crosswalk
maps to the 2006 arrangement and `xw:fw-HFACS` says so explicitly, because a
reader checking against the 2000 report would otherwise find categories that are
not there.

### `hse_pifs`

Health and Safety Executive (n.d.). *Performance Influencing Factors (PIFs).*
HSE human factors guidance.
<https://www.hse.gov.uk/humanfactors/assets/docs/pifs.pdf>

**Verification:** primary. The PDF was retrieved from that URL and its text
extracted. It is a single page, so the entire list was read: all three headings
and all 26 factors this repository transcribes were confirmed verbatim,
including HSE's own note "NB. This list is not exhaustive".

**What it supports here.** The PIF inventory in section 10.5, under HSE's three
headings of Job, Person and Organisation factors. HSE states of its own list
that it "is not exhaustive", which is recorded on `xw:fw-HSE-PIF`; a crosswalk
that claimed completeness against a list its own publisher calls incomplete
would be overstating.

---

## Supporting the rule base

### `groth2012`

Groth, K.M. & Mosleh, A. (2012). A data-informed PIF hierarchy for model-based
Human Reliability Analysis. *Reliability Engineering & System Safety*, 108,
154–174. DOI: 10.1016/j.ress.2012.08.006.

**Verification:** bibliographic. The DOI resolves to exactly this record — both
authors, title, journal, volume 108, pages 154–174 and the 2012 date all match.
The article text was not read.

**What it supports here.** Two things. First, the `ehs:MatchPartial` strength
and the general warning attached to it: Groth and Mosleh report that PIFs across
methods are not defined specifically enough for consistent interpretation, that
there is no standard PIF set, and that few rules govern how PIF sets are created.
The rows marked `partial` in the crosswalk are where that observation bites.
Second, rule `R22-aggravated-by-second-factor`, which records that a second
independent degraded factor bearing on the same error mode opens a second route
to it. Note what that rule does **not** say: nothing here supports multiplying
factor effects together, and SPAR-H's practice of doing so is not adopted.

### `rasmussen1983`

Rasmussen, J. (1983). Skills, rules, and knowledge; signals, signs, and symbols,
and other distinctions in human performance models. *IEEE Transactions on
Systems, Man, and Cybernetics*, SMC-13(3), 257–266.
DOI: 10.1109/TSMC.1983.6313160.

**Verification:** bibliographic. The DOI resolves to exactly this record --
author, title, journal, volume SMC-13, issue 3, pages 257-266 and the 1983 date
all match. The article text was not read; the three cognitive control levels are
used here as the standard attribution they have become.

**What it supports here.** The three cognitive control levels in section 6 of
the Turtle file — skill-based, rule-based, knowledge-based — and the rules that
reason about a task being pushed from one level to another. The worked reactor
scenario turns on this: an unfamiliar situation with no covering procedure
displaces the operator from rule-based to knowledge-based control.

### `reason1990`

Reason, J. (1990). *Human Error.* Cambridge: Cambridge University Press.

**Verification:** bibliographic.

**What it supports here.** The error modes in section 6 — skill-based slips and
lapses, rule-based mistakes, knowledge-based mistakes — as the Generic
Error-Modelling System maps them onto Rasmussen's control levels.

---

## Cited for coverage gaps and stated limitations

These two support the repository's account of what it cannot do. Neither
supports a positive claim.

### `folkard2003`

Folkard, S. & Tucker, P. (2003). Shift work, safety and productivity.
*Occupational Medicine*, 53(2), 95–101. DOI: 10.1093/occmed/kqg047.

**Verification:** primary. The full text was retrieved and the sentence below
read in it. Authorship, title, journal, volume, issue, pages and date were
confirmed by DOI resolution.

**What it supports here.** The time-of-day coverage gap. Discussing an averaged
trend drawn from three studies that "all examined trends in national accident
statistics and corrected for 'exposure' in some manner", Folkard and Tucker
write:

> "apart from a slightly heightened risk from the second to the fifth hour, risk
> increased in an approximately exponential fashion with time on shift such that
> in the twelfth hour it was more than double that during the first 8 h."

The relevance here is the qualifier, not the shape of the curve: every study
feeding that trend had to correct for exposure first. A *rate* claim about hour
of shift requires an exposure denominator, and this repository has none of any
kind. Note also what this entry does **not** license — the author's separate work
on OSHA filings reports raw injury counts by hour of shift, which are not
exposure-corrected and are not comparable to this figure. See
`docs/PROVENANCE.md`.

### `hanecke1998`

Hanecke, K., Tiedemann, S., Nachreiner, F. & Grzech-Sukalo, H. (1998). Accident
risk as a function of hour at work and time of day as determined from accident
data and exposure models for the German working population. *Scandinavian
Journal of Work, Environment & Health*, 24(Suppl 3), 43–48. PMID 9916816.

**Verification:** bibliographic. Title, four-author list, journal, volume,
supplement, page range and year confirmed against the journal's own record; the
journal indexes the first author as Hänecke. The published abstract was read and
supports the description below. The full article was not retrieved.

**What it supports here.** The methodological precedent for the same gap.
Hänecke and colleagues analysed more than 1.2 million accidents for 1994 and,
because German data did not record how long or at what time of day people
actually worked, had to estimate exposure models before any risk could be
calculated; they report an exponentially increasing accident risk beyond the
ninth hour at work. It is cited here for the method rather than the coefficient,
and it is the reason `xw:gap-cream-TimeOfDay` is recorded as a
gap rather than filled with an unadjusted count distribution.

---

## Works referred to in the README but not used as keys

These are named in `README.md` or `docs/PROVENANCE.md` as part of an argument,
but nothing in the ontology or the rule base cites them, so they are not citation
keys. `tests/test_citations.py` requires that every key have an entry and every
entry have a user, which is why they are listed here in a different form rather
than promoted to keys they do not earn. They are recorded because a claim
attributed to a named document should be checkable, whether or not the code
depends on it.

**Boring, R.L. (2010).** How Many Performance Shaping Factors are Necessary for
Human Reliability Analysis? *10th International Probabilistic Safety Assessment
and Management Conference (PSAM10)*, Seattle, WA, 7-11 June 2010.
INL/CON-10-18620. Verification: bibliographic; the record and abstract were
retrieved from OSTI (biblio/1010682). Supports the README's statement that PSF
set sizes already range from single-factor models to fifty or more, and its
examples of 15 PSFs in NUREG-1792 and eight in SPAR-H.

**U.S. Nuclear Regulatory Commission (2014).** *The International HRA Empirical
Study: Lessons Learned from Comparing HRA Method Predictions to HAMMLAB
Simulator Data.* NUREG-2127. Verification: primary for the two claims the README
makes; the report was retrieved (ADAMS ML14227A197), its text extracted, and both
passages read. It reports that after censoring outliers, method-to-method
variability for each human failure event was "one order of magnitude, or slightly
more" in the loss-of-feedwater scenarios and "two orders of magnitude or less" in
the steam-generator-tube-rupture scenarios. On ranking it concludes that "the HRA
predictions mostly correlate with the empirical difficulty", with named
exceptions. That second sentence is the reason the README does not claim the
rankings failed.

**Swain, A.D. & Guttmann, H.E. (1983).** *Handbook of Human Reliability Analysis
with Emphasis on Nuclear Power Plant Applications (THERP).* NUREG/CR-1278,
SAND80-0200. Verification: bibliographic. Named in the README only as one of the
earlier frameworks showing a comparable split of context; no content is
transcribed from it.

**U.S. Nuclear Regulatory Commission (2005).** *Good Practices for Implementing
Human Reliability Analysis (HRA).* NUREG-1792. Verification: bibliographic.
Named in the README as the NRC's 15-PSF good-practice set; no content is
transcribed from it.

---

## Sources deliberately not cited

Two omissions are intentional and worth stating, because their absence might
otherwise look like an oversight.

**Rasmussen (1997) and Leveson (STAMP)** are not cited in support of anything
here. Both argue against decomposing accidents into additive contributing
factors — Rasmussen in favour of modelling work-system constraints, Leveson in
favour of treating safety as control-structure constraint enforcement. This
repository builds a factor-based model. Citing either as friendly authority
would misrepresent them. The tension is real and is stated in the README under
"Theoretical position", not papered over with a citation.

**SPAR-H multipliers, and any human error probability.** No HEP appears anywhere
in this repository. The screening band emitted by the engine is an ordinal label
produced by rules explicitly marked `convention`, and the derivation trace says
so on every run.
