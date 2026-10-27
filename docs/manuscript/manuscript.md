# A traceable crosswalk of IDHEAS-G performance-influencing factors, a rule-based narrative suggester, and a held-out evaluation on Chemical Safety Board excerpts

**Status: UNSUBMITTED DRAFT.** This manuscript has not been submitted to any journal, conference or preprint server, and has not been posted anywhere other than this repository. It has had no peer review and no second-coder check. Version of the software described: `ehs-human-factors-ontology` 0.1.0 plus the unreleased changes listed in `CHANGELOG.md`.

**Author:** Priyatham Chimmani (single author; no affiliation or ORCID is declared in this repository, see TODO list).

**Format note:** Markdown, IMRaD order. Bracketed tags such as [N03] after a figure point to a row of the numbers register in Appendix A, which gives the repository file the figure comes from and the exact string a test searches for. `tests/test_manuscript.py` checks every register row.

## Read first: three caveats that govern every performance figure

1. **Same-coder caveat.** One person (the author) wrote the rules in `crosswalk/pif_rules.csv`, coded both evaluation cohorts, and selected the excerpts. No second coder has coded anything. The agreement and accuracy figures below are therefore not inter-rater or independent-validation figures.
2. **Excerpt-sourcing caveat.** The evaluation text is the set of quoted passages the gold labels were coded from, not full incident reports. Recall therefore measures whether the rules' vocabulary reaches words a coder had already pointed at, not discovery in free-running narratives. The held-out passages were requested by factor topic (training, procedures, alarms and so on) and are mostly Chemical Safety Board (CSB) recommendation wording from summary pages, which inflates recall.
3. **Small, incomplete gold standard.** Gold labels exist only for PIFs with a quoted passage, so some false positives may be real conditions nobody coded. The development-cohort scores are resubstitution (optimistic); the held-out cohort is small enough that one pair moves recall by about 2.4 points [N20], and no confidence interval is claimed.

## Abstract

**Background.** Human reliability analysis (HRA) and incident investigation use overlapping taxonomies of the conditions that shape human performance, so findings coded in one taxonomy are hard to compare with another. **Methods.** We encode the 20 performance-influencing factors (PIFs) in 4 context dimensions of IDHEAS-G [N01][N02] as an OWL/Turtle ontology with a crosswalk of 90 factor-level alignments [N03] to SPAR-H, CREAM, HFACS and the HSE PIF list. A transparent phrase-rule suggester (97 curated rules [N10]; no learned component) proposes candidate PIFs from incident text, each hit traceable through the crosswalk to an external factor. We evaluated it against hand-coded excerpts from U.S. Chemical Safety Board investigations, split into a development cohort (coded before the rules were written) and a held-out cohort (coded afterwards with the rules frozen). The ontology and crosswalk are also exported as SKOS, and a blinded second-coder protocol was built. **Results.** On the development cohort (resubstitution, 25 gold pairs) the curated rules reached precision 0.74 and recall 0.80 [N17]. On the held-out cohort (42 gold pairs) they reached precision 0.86 and recall 0.71 [N18]. A majority-class control reached precision 0.69 and recall 0.21 on the held-out cohort [N19]. **Conclusions.** The result is a worked, reproducible demonstration, not a validated tool. It rests on one coder, on excerpts rather than full reports, and on a small sample. No second-coder data exists, so no inter-rater reliability is reported.

## 1 Introduction

Most HRA methods describe the context of a human action through a set of factors that make error more or less likely. SPAR-H uses eight performance shaping factors (Gertman et al. 2005), CREAM uses nine common performance conditions (Hollnagel 1998), HFACS classifies preconditions, supervisory factors and organisational influences for accident investigation (Shappell and Wiegmann 2000; Shappell et al. 2006), and the UK Health and Safety Executive (HSE) publishes a PIF list (HSE 1999). IDHEAS-G (NUREG-2198, U.S. Nuclear Regulatory Commission 2021) defines 20 PIFs grouped into four context categories. Boring (2010) documents that PSF sets already range from one factor to fifty or more, and Groth and Mosleh (2012) report that existing sets are not defined precisely enough to be interpreted consistently. Adding another taxonomy would worsen that problem, so this work does not propose one.

**What is not claimed as new.** The four context categories and the 20 PIFs are adopted from IDHEAS-G unchanged. Two of the four dimension labels are identical to IDHEAS-G's and two are synonyms. The contributions are (i) a machine-readable encoding with a declared match strength and a citation on every alignment, (ii) automated checks that keep the crosswalk complete and consistent with its source, (iii) a rule-based suggester whose every hit unwinds to the crosswalk, (iv) a held-out evaluation of that suggester with its limits stated, (v) a SKOS export, and (vi) a blinded second-coder protocol and agreement tool. Item (vi) has produced no agreement data.

## 2 Methods

### 2.1 Ontology and crosswalk

The ontology (`ontology/ehs-hfo.ttl`) is hand-written OWL/Turtle. It holds the 4 context dimensions and 20 PIFs, five external frameworks with their complete factor inventories (78 external entries in all [N04]), and reified alignments between a PIF and an external factor. Each alignment has a match strength (exact, close, broader, narrower, partial), and 6 absences are asserted explicitly [N05]. Strengths are the author's judgement. CREAM conditions were transcribed from Shirali et al. (2019), a secondary source, rather than from Hollnagel (1998). The crosswalk files in `crosswalk/` are generated from the Turtle by `tools/build_crosswalk.py` and a test fails if they disagree. The repository also contains a forward-chaining rule engine with derivation traces (24 rules [N09]); it is not evaluated in this manuscript beyond its description.

### 2.2 Rule-based suggester

`python -m ehs_hfo suggest` takes narrative text and returns candidate PIFs using phrase rules only. The curated set has 97 rules in `crosswalk/pif_rules.csv` [N10]. Each rule pairs a phrase with a PIF and with an external SPAR-H, CREAM, HFACS or HSE factor that the ontology aligns to that PIF; a test fails if that alignment is missing. A baseline set of 59 rules is derived by code from the ontology's own labels: a stemmed word becomes a rule for a PIF if it occurs in that PIF's label vocabulary and in no other PIF's [N10]. A majority-class control always predicts the most frequent development-cohort PIF (Team and organisation factors).

### 2.3 Incident coding and cohorts

Text was retrieved from csb.gov pages and final-report PDFs through a web-fetch tool that returns excerpts and truncates long sentences. The repository lists 28 CSB investigations [N13]. A factor is coded for an investigation only when a quoted passage directly states the condition the factor names, with no inference beyond the quote. Each coding is typed as a CSB finding or a CSB recommendation. Quotes were not checked against the full PDFs.

The **development cohort** is 13 listed investigations, of which 10 are coded (25 pairs) [N12]. It was coded before the rules were written, and the author had read those quotes, so scores on it are resubstitution. A variant that removes the 11 rules whose phrase was taken from those quotes (86 rules remain) is reported beside it [N16]. The **held-out cohort** is 15 further investigations of which 13 are coded (42 pairs) [N12][N22]. They were coded after the rules were committed, and `crosswalk/pif_rules.csv` was not edited afterwards. Two held-out investigations returned no findings or recommendations text and are not coded. In all, 23 investigations are coded, giving 67 (investigation, PIF) pairs over 10 distinct PIFs [N11].

### 2.4 Evaluation

The narrative for an investigation is the concatenation of its quoted passages. A prediction is a set of PIFs per investigation; precision and recall are computed over (investigation, PIF) pairs. `tools/evaluate_suggester.py` generates `incidents/suggester_eval.md`, and a test regenerates and compares it.

### 2.5 SKOS export

`tools/build_skos.py` (standard library only) generates `docs/skos/ehs-hfo-skos.ttl` and `.jsonld` from the ontology. It publishes the PIFs as a SKOS concept scheme (dimensions as top concepts), one scheme per external framework, and the alignments as mapping properties from PIF to external factor: close as `skos:closeMatch`, broader as `skos:broadMatch`, partial as `skos:relatedMatch`, with `skos:exactMatch` and `skos:narrowMatch` unused because none is asserted. Each dimension additionally has a `skos:closeMatch` to its IDHEAS-G category. The 6 asserted absences cannot be expressed in SKOS and are not exported. Tests regenerate and diff the files and parse them back without network access; this is not validation by an external SKOS validator.

### 2.6 Second-coder protocol

`tools/second_coder.py` exports the coded excerpts as a coding sheet with no existing PIF codes, evidence types or cohort shown, ordered by a hash of the excerpt. It imports a returned sheet with validation and reports per-PIF and pooled Cohen's kappa and percent agreement. The unit of analysis is the excerpt. Kappa is reported as undefined when a coder used one category throughout. The protocol is in `docs/second-coder-protocol.md`; contributors return a sheet by pull request.

## 3 Results

### 3.1 Crosswalk

The crosswalk has 90 alignments: 34 close, 23 broader, 0 narrower, 33 partial and 0 exact [N06]. By framework the counts are SPAR-H 16, CREAM 22, HFACS 23 and HSE 29 [N07]. Fourteen PIFs have a counterpart in all four frameworks and six in three [N08]. Because no alignment is exact, no mapping is claimed as an identity.

### 3.2 Suggester, held-out and development cohorts

Table 1 reports the curated rules on both cohorts, exactly as in `incidents/suggester_eval.md`. The two cohorts must not be read as one estimate: the first is resubstitution, the second is out of sample but subject to the excerpt-sourcing and same-coder caveats above.

**Table 1.** Curated rule set (97 rules). TP, FP, FN are counts of (investigation, PIF) pairs.

| Cohort | Investigations | Gold pairs | TP | FP | FN | Precision | Recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Development (resubstitution) | 10 | 25 | 20 | 7 | 5 | 0.74 | 0.80 |
| Held-out | 13 | 42 | 30 | 5 | 12 | 0.86 | 0.71 |

Source rows: [N17] and [N18]. On the development cohort the curated set without the quote-derived phrases scored precision 0.74 and recall 0.56 (14 of 25 pairs) [N17]. Recall fell from 0.80 to 0.71 between cohorts while precision rose from 0.74 to 0.86. The held-out recall of 0.71 is above the 0.56 of the variant without quote-derived phrases, which is the fairer comparison, but that comparison is across different cohorts and is descriptive only.

**Controls.** The untuned baseline recovered 5 of 25 development pairs (precision 0.31) and 10 of 42 held-out pairs (precision 0.42, recall 0.24) [N17][N18]. The majority-class control reached precision 0.69 and recall 0.21 on the held-out cohort [N19]. Time pressure and stress (2 held-out pairs) was missed by the curated rules [N21]. Ten of the 20 PIFs have gold coding in either cohort, so the rules for the other ten are untested [N23].

### 3.3 SKOS export

The export contains 90 mapping triples (34 `closeMatch`, 23 `broadMatch`, 33 `relatedMatch`) plus 4 dimension-to-IDHEAS-G `closeMatch` triples, 38 `closeMatch` in all [N14]. All parse back to exactly the generated triples in the repository's tests.

### 3.4 Second coder

No second coder has contributed, and no agreement statistic exists or is reported [N15]. The tool computes numbers only from a returned sheet. The coding sheet contains 67 excerpts [N15].

## 4 Discussion

**What the held-out result supports.** The curated rules, frozen before the held-out excerpts were coded, recovered 30 of 42 pairs with 5 false positives. That is some evidence that the phrase rules are not merely memorising the development quotes. It is not evidence about performance on whole incident reports.

**What it does not support.** (1) Same coder: the rule author coded both cohorts, so coder expectations may have shaped the labels; this is the main reason a second-coder check is needed. (2) Excerpt sourcing: the input text is the evidence the labels were drawn from, and the held-out excerpts were chosen by topic, so recall is inflated by construction. (3) The gold standard is incomplete, so precision is measured against an undercount of true conditions. (4) Only 10 of 20 PIFs appear in the gold data. (5) Sample size is 42 held-out pairs and no interval is given. (6) CSB investigations concern chemical-industry incidents, whereas IDHEAS-G, SPAR-H and CREAM were developed mainly for nuclear power and HFACS for aviation, so domain transfer is an extension the sources do not license.

**Other limitations.** The alignment strengths are single-author judgements, without agreement testing. CREAM is transcribed from a secondary source. Excerpts are web-fetch fragments and were not checked against the full PDFs. Pages for the most recent investigations summarise recommendations only.

**Next step.** The decisive test is full-report narratives coded by someone other than the rule author, using the blinded protocol in section 2.6. Until then the performance figures should be cited together with these caveats.

## 5 Data and code availability

All code, data and generated tables are in the repository `priyatham9/ehs-human-factors-ontology` (MIT licence). Python 3.9 or later, standard library only. Every table in this manuscript can be regenerated with `python3 tools/evaluate_suggester.py` and `python3 tools/build_skos.py --check`, and `python3 -m unittest discover -s tests -t .` includes the manuscript check. The scenario corpus in `synthetic/` is fabricated and labelled as such; no figure in this manuscript depends on it. No archival DOI has been minted (see TODO list).

## 6 Declarations

Author contributions: sole author. Funding: none declared. Competing interests: none declared. No human subjects were involved; incident text comes from public CSB web pages and reports and is quoted in short excerpts with source URLs. No endorsement by the CSB, the NRC, HSE, any standards body or the authors of the mapped frameworks is claimed.

## 7 References

Only references verified for `CITATIONS.md` are cited. The status column repeats the state recorded there (primary: document retrieved and the cited claim read; bibliographic: record confirmed, text not read).

| Reference | Status in `CITATIONS.md` |
| --- | --- |
| Boring, R.L. (2010). How many performance shaping factors are necessary for human reliability analysis? *10th International Probabilistic Safety Assessment and Management Conference (PSAM10)*, Seattle, WA. INL/CON-10-18620. OSTI 1010682. | bibliographic |
| Gertman, D.I., Blackman, H.S., Marble, J.L., Byers, J.C. and Smith, C.L. (2005). *The SPAR-H Human Reliability Analysis Method.* NUREG/CR-6883, INL/EXT-05-00509. U.S. Nuclear Regulatory Commission. | primary |
| Groth, K.M. and Mosleh, A. (2012). A data-informed PIF hierarchy for model-based human reliability analysis. *Reliability Engineering and System Safety*, 108, 154-174. https://doi.org/10.1016/j.ress.2012.08.006 | bibliographic |
| Health and Safety Executive (1999). *Reducing Error and Influencing Behaviour.* HSG48. HSE Books. ISBN 978-0-7176-2452-2. | primary (PIF list PDF); book bibliographic |
| Hollnagel, E. (1998). *Cognitive Reliability and Error Analysis Method (CREAM).* Elsevier. ISBN 978-0-08-042848-2. | bibliographic |
| Shappell, S.A. and Wiegmann, D.A. (2000). *The Human Factors Analysis and Classification System (HFACS).* DOT/FAA/AM-00/7. Federal Aviation Administration. | primary |
| Shappell, S., Detwiler, C., Holcomb, K., Hackworth, C., Boquet, A. and Wiegmann, D. (2006). *Human Error and Commercial Aviation Accidents: A Comprehensive, Fine-Grained Analysis Using HFACS.* DOT/FAA/AM-06/18. Federal Aviation Administration. | primary |
| Shirali, G.A., Hosseinzadeh, T., Ahamadi Angali, K. and Rostam Niakan Kalhori, S. (2019). Modifying a method for human reliability assessment based on CREAM-BN: a case study in control room of a petrochemical plant. *MethodsX*, 6, 300-315. https://doi.org/10.1016/j.mex.2019.02.008 | primary |
| U.S. Nuclear Regulatory Commission (2021). *The General Methodology of an Integrated Human Event Analysis System (IDHEAS-G).* NUREG-2198. J. Xing, Y.J. Chang and J. DeJesus Segarra. ADAMS ML21127A272. | primary |

## 8 TODO: references and items not verified

These are deliberately not cited as support above, because they were not verified in this repository or this environment (no access to external sites).

- [ ] Cohen, J. (1960), the original kappa paper, for the agreement statistic in section 2.6. Verify bibliographic details before citing.
- [ ] A kappa interpretation convention (for example Landis and Koch 1977), if the second-coder results are ever interpreted. Verify before citing.
- [ ] The W3C SKOS Reference Recommendation (2009). It is linked in `docs/skos.md` but is not in `CITATIONS.md`; verify the citation details before citing.
- [ ] Prior work on automatic classification of incident narratives to human-factors taxonomies. No such reference is verified here, and none is claimed; a literature search is needed before any novelty statement.
- [ ] Prior published CSB-based human-factors analyses, for the discussion of domain transfer.
- [ ] Author ORCID and affiliation (none declared in `CITATION.cff`).
- [ ] An archival DOI (Zenodo metadata exists in the repository, but no release or deposit has been made).
- [ ] Full-report coding by a second coder; replace the CSB excerpts with full-report narratives.
- [ ] Choose a target venue and follow its format; nothing has been submitted.

## Appendix A. Numbers register

Every figure in this manuscript that comes from the repository appears below with the file it comes from and the exact string that `tests/test_manuscript.py` searches for in that file (a `\|` in a string stands for a literal pipe). Rows marked "recomputed" are also recomputed by the test from the data files, not only searched.

| ID | Value as written | Source file | Search string | Recomputed |
| --- | --- | --- | --- | --- |
| N01 | 20 PIFs | README.md | `It provides 20 PIFs, 90 alignments` | yes |
| N02 | 4 context dimensions | docs/skos.md | `The 4 context dimensions, 20 performance-influencing factors` | yes |
| N03 | 90 alignments | docs/methods-note.md | `- Factor-level alignments: 90.` | yes |
| N04 | 78 external entries | docs/methods-note.md | `- External entries transcribed: 78 across 5 frameworks.` | yes |
| N05 | 6 absences | docs/methods-note.md | `- Asserted absences (no counterpart): 6.` | yes |
| N06 | 34 close, 23 broader, 0 narrower, 33 partial, 0 exact | docs/methods-note.md | `\| **All** \| 34 \| 23 \| 0 \| 33 \| 0 \| 90 \|` | yes |
| N07 | SPAR-H 16, CREAM 22, HFACS 23, HSE 29 | docs/methods-note.md | `\| HSE PIF list \| 14 \| 5 \| 0 \| 10 \| 0 \| 29 \|` | yes |
| N08 | Fourteen | docs/methods-note.md | `- Local factors aligned in 4 of 4 frameworks: 14.` | no |
| N09 | 24 rules | docs/methods-note.md | `- Rules: 24, of which 18 are marked` | no |
| N10 | 97 curated rules, 59 baseline rules | incidents/suggester_eval.md | `\| baseline (words unique to a PIF's ontology labels; not tuned) \| 59 \| 10 \| 14 \| 32 \| 0.42 \| 0.24 \| 0.17 \|` | yes |
| N11 | 23 investigations, 67 pairs, 10 PIFs | incidents/suggester_eval.md | `Data: 23 coded investigations, 67 (investigation, PIF) gold pairs over 10 distinct PIFs` | yes |
| N12 | 25 pairs; development 10 coded investigations; held-out 13 investigations, 42 pairs | incidents/suggester_eval.md | `## Held-out cohort (13 investigations, 42 pairs, rules not fit to these)` | yes |
| N13 | 28 CSB investigations | incidents/README.md | `28 U.S. Chemical Safety Board investigations` | yes |
| N14 | 90 mapping triples; 38 closeMatch | docs/skos.md | `triples, 38 in the file` | no |
| N15 | 67 excerpts; no second coder | docs/second-coder-protocol.md | `**Status: no second coder has contributed yet, so there are no agreement figures.**` | yes |
| N16 | 11 rules; 86 remain | incidents/suggester_eval.md | `\| curated without the rules whose phrase was taken from the development quotes \| 86 \| 14 \| 5 \| 11 \| 0.74 \| 0.56 \| 0.43 \|` | yes |
| N17 | precision 0.74 and recall 0.80; development curated TP 20, FP 7, FN 5; baseline 5 TP, 0.31; no-quote variant 14 TP, 0.56 | incidents/suggester_eval.md | `\| curated (crosswalk/pif_rules.csv; written after reading the development quotes) \| 97 \| 20 \| 7 \| 5 \| 0.74 \| 0.80 \| 0.82 \|` | yes |
| N18 | precision 0.86 and recall 0.71; held-out curated TP 30, FP 5, FN 12; baseline 10 TP, 0.42, 0.24 | incidents/suggester_eval.md | `\| curated (crosswalk/pif_rules.csv; written after reading the development quotes) \| 97 \| 30 \| 5 \| 12 \| 0.86 \| 0.71 \| 0.65 \|` | yes |
| N19 | precision 0.69 and recall 0.21; majority-class control, held-out | incidents/suggester_eval.md | `\| majority-class control (always predict Team and organisation factors) \| 1 \| 9 \| 4 \| 33 \| 0.69 \| 0.21 \| 0.14 \|` | yes |
| N20 | about 2.4 points | docs/methods-note.md | `by about 2.4 points` | yes |
| N21 | Time pressure and stress, 2 held-out pairs, missed | incidents/suggester_eval.md | `\| Time pressure and stress \| 2 \| 0 \| 0 \| 2 \| n/a \| 0.00 \|` | yes |
| N22 | 15 further investigations, 13 coded | incidents/README.md | `(the 15 added` | yes |
| N23 | Ten of the 20 PIFs; have gold coding | docs/methods-note.md | `Ten of the 20 PIFs have gold coding in either cohort` | yes |
