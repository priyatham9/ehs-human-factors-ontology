# CSB investigations coded to the crosswalk

First application of the PIF ontology to real incidents. Files:

- `csb_investigations.csv`: 13 U.S. Chemical Safety Board investigations, each with its
  CSB source URL; `coded` says whether any factor was coded.
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
   marked `no` and listed as not coded. Pages for 2024-2026 investigations summarise
   recommendations only; their full reports were not read.

## Limits

One coder, no second-rater agreement. 25 codings across 10 investigations is a worked
demonstration, not a sample of CSB work, and says nothing about how common any factor is.
Factors with no coding (for example Thermal conditions) are absent from these excerpts,
not shown to be absent from the incidents.
