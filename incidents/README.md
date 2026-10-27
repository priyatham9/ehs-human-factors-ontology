# CSB investigations coded to the crosswalk

First application of the PIF ontology to real incidents. Files:

- `csb_investigations.csv`: 28 U.S. Chemical Safety Board investigations, each with its
  CSB source URL; `coded` says whether any factor was coded; `cohort` is `development`
  (the first 13, listed before the suggester rules were written) or `held_out` (the 15 added
  afterwards).
- `csb_coding.csv`: one row per (investigation, factor) with a quoted passage.
- `csb_coding.md`: generated readable view (`python3 tools/build_csb_coding.py --write`).

## Method

1. Text was retrieved from csb.gov pages and final-report PDFs through a web-fetch tool
   that returns excerpts (it truncates long sentences). Quotes are those returned
   excerpts; they were not checked against the full PDF, so verify a quote against the
   linked source before relying on it.
2. A factor is coded only when a quoted passage directly states the condition the factor
   names (for example 12-hour shifts for 29 or more days under Mental fatigue). No
   inference beyond the quote.
3. `evidence_type` is `finding` (CSB's stated finding or report text) or
   `recommendation` (CSB recommendation wording). A recommendation shows what the CSB
   chose to address; it is weaker evidence of cause than a finding.
4. Investigations whose fetched page offered nothing codable without interpretation are
   marked `no` and listed as not coded. Pages for 2023-2026 investigations summarise
   recommendations only; their full reports were not read.
5. The 15 held-out investigations were added with the same method, from csb.gov
   investigation or news-release pages found on the CSB completed-investigations list.
   Their rules were frozen first: `crosswalk/pif_rules.csv` was not edited after they were
   coded. Passages were requested by topic (training, procedures, alarms and so on), so the
   quotes favour the vocabulary of those topics. Where the fetched excerpt was a fragment
   the fragment is what is quoted. Two held-out investigations (KMCO, Sunoco Nederland)
   returned no findings or recommendations text and are marked not coded; a third candidate,
   Optima Belle, returned a page that was a superseded OSHA-standard recommendation rather
   than the incident, and was left out.

## Limits

One coder, no second-rater agreement. 67 codings across 23 investigations is a worked
demonstration, not a sample of CSB work, and says nothing about how common any factor is.
Factors with no coding (for example Thermal conditions) are absent from these excerpts,
not shown to be absent from the incidents.

## Suggester evaluation

`suggester_eval.md` scores the rule-based PIF suggester (`python -m ehs_hfo suggest`)
against these codings, separately for the development cohort (resubstitution) and the
held-out cohort (rules not written with these quotes in view). The text it reads is the
quotes, so the scores measure vocabulary overlap; see that file and `docs/suggester.html`
for the caveats.
