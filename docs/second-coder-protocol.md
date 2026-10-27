# Blinded second-coder protocol

## Why this exists

The person who wrote the PIF suggester rules also coded the CSB incident excerpts in
`incidents/csb_coding.csv`. That is a known limitation: there is no inter-rater reliability
figure, and the suggester evaluation (`incidents/suggester_eval.md`) scores rules against codings
made by their own author. This protocol lets an independent person code the same excerpts without
seeing the existing codes, and measures how often the two agree.

**Status: no second coder has contributed yet, so there are no agreement figures.** None are
reported in this repository, and the tool produces numbers only from a real returned sheet.

## What the second coder receives

```
python3 tools/second_coder.py export-sheet --out coding_sheet.csv
python3 tools/second_coder.py export-codebook --out pif_codebook.csv
```

- `coding_sheet.csv` has one row per distinct quoted excerpt (67 at the time of writing), with the
  investigation name, the CSB source URL and the excerpt text. The `pifs` column is blank.
  Rows are ordered by a hash of the excerpt, not by investigation or factor.
- Withheld on purpose: the first coder's PIF codes, whether the passage is a CSB finding or a
  recommendation, and the development/held-out cohort. Each would reveal how the first coder read
  the excerpt.
- `pif_codebook.csv` lists the 20 PIFs (`ehs:` CURIE, label, dimension). The coder should also read
  the factor definitions in `ontology/ehs-hfo.ttl` and the coding rule in `incidents/README.md`:
  code a factor only when the quoted passage directly states the condition the factor names, with
  no inference beyond the quote.

Do not read `incidents/csb_coding.csv`, `incidents/csb_coding.md` or `incidents/suggester_eval.md`
before finishing the sheet. Opening the source URL to read the surrounding report is allowed and
encouraged when an excerpt is a fragment; note that you did so in `coder_notes`.

## How to fill the sheet

For each row, put in `pifs`:

- one or more PIFs separated by `;`, as CURIEs (`ehs:Staffing`) or local names (`Staffing`); or
- `NONE` if you read the excerpt and no PIF is directly stated; or
- leave blank if you did not rate the row. Blank rows are left out of the comparison.

Rate every row you can. Skipping the hard ones biases agreement upwards. Use `coder_notes` freely;
it is not scored.

## Contributing a sheet by pull request

1. Fork the repository and export the sheet and codebook as above, on a clean checkout.
2. Code it independently, without the first coder's files open.
3. Save it as `incidents/second_coder/<your-github-handle>.csv`, keeping the header row.
4. Check it parses and see your own numbers: `python3 tools/second_coder.py report incidents/second_coder/<handle>.csv`.
   Fix any reported format error (unknown excerpt id, unknown PIF, `NONE` mixed with PIFs).
5. Open a pull request containing only that file. In the description state your relevant
   background (for example "EHS practitioner, 6 years" or "human factors researcher"), roughly how
   long the coding took, and whether you saw the first coder's codes beforehand. A coder who had
   seen them is not blinded, and the sheet will be labelled accordingly rather than discarded.
6. Do not edit `incidents/csb_coding.csv` in the same pull request. Disagreements are reported,
   not resolved by overwriting the first coder.

Contributor credit is by GitHub handle in the sheet's file name and, if the coder wishes, in
`CITATION.cff` and the changelog.

## What is computed

```
python3 tools/second_coder.py report incidents/second_coder/*.csv [--markdown]
```

Unit of analysis: one excerpt. For each PIF, each coder either assigned it to the excerpt or did
not, which gives a 2x2 table over the excerpts the second coder rated. Per PIF the report gives
the four cell counts, percent agreement (both yes plus both no, over rated excerpts) and Cohen's
kappa, `(po - pe) / (1 - pe)`. Kappa is shown as `undefined` when one coder used a single
category for that PIF throughout, because chance agreement is then 1. A pooled row treats every
(excerpt, PIF) decision as one table. PIFs neither coder used are not listed. Each sheet is
reported separately; sheets from different coders are never merged.

## Limits of the design

- **Selected sample.** The excerpts are the first coder's quotes, so each carries at least one
  first-coder code, and passages were found by searching on each factor's topic. Agreement here
  is agreement on that sample. It does not estimate agreement on whole reports, and does not
  measure whether a second coder would have found the same passages in the first place.
- **Sparse PIFs.** Most PIFs have a handful of codings, so per-PIF kappa is unstable and
  confidence intervals would be wide. The tool does not compute intervals; with fewer than about
  ten rated positives for a PIF, treat its kappa as indicative at most.
- **Prevalence.** When a PIF is rare among the rated excerpts, kappa can be low despite high
  percent agreement. Read the two together with the cell counts.
- **Excerpt text only.** Excerpts are fragments returned by a web-fetch tool (see
  `incidents/README.md`); a second coder may reasonably want context the fragment lacks.
- **Pooled kappa is descriptive.** Pooling PIFs treats decisions as independent, which they are not.
- **Evidence type.** The first coder's finding/recommendation labels are not part of this
  comparison.

## Not in scope

This protocol does not adjudicate disagreements, change any existing coding, retune the suggester
rules, or establish that either coder is correct. If second-coder sheets arrive, any
reconciliation should be a separate, documented step.
