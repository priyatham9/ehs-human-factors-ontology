# A Foundry-style ontology for the PIF crosswalk

An independent design in the style of a Palantir Foundry Ontology (object types, link
types, action types, functions). It is not affiliated with Palantir, needs no Foundry
account, and reads only files committed in this repository. It mirrors the conventions of
`ehs-osha-analysis` (`src/ehs_osha/ontology/`) and `ehs-chemical-peers`
(`src/chempeers/ontology/`): a declarative `spec.json`, a validating runtime, an
append-only action log, SQLite and JSON export, standard library only.

Code: `src/ehs_hfo/foundry/` (named `foundry` because `ehs_hfo.ontology` is the existing
OWL/Turtle loader). Spec: `src/ehs_hfo/foundry/spec.json`. Tests:
`tests/test_foundry_ontology.py`. What the data covers: [ontology-coverage.md](ontology-coverage.md).

```
python3 -m ehs_hfo.foundry --out build/ --coverage-md docs/ontology-coverage.md
```

## Sources

| File | Becomes |
|---|---|
| `ontology/ehs-hfo.ttl` | ContextDimension, Pif, Framework, FrameworkItem |
| `crosswalk/crosswalk.csv` | CrosswalkEntry (match strength close, partial, broader) and AssertedAbsence (`none`) |
| `crosswalk/pif_rules.csv` | Rule |
| `incidents/csb_investigations.csv` | Investigation |
| `incidents/csb_coding.csv` | EvidenceExcerpt |

Incident data does exist, but only as the CSB set above: investigations with a csb.gov URL
and quoted passages coded to PIFs. There are no other incidents, and none were added. The
quotes are the retrieval tool's excerpts and were not checked against the full reports (see
`incidents/README.md`).

## Object types

| Object type | Key | Role |
|---|---|---|
| ContextDimension | `dimension_curie` | The four context dimensions; points at its IDHEAS-G category. |
| Pif | `factor_curie` | A performance-influencing factor. |
| Framework | `framework_curie` | CREAM, HFACS, HSE PIFs, SPAR-H, IDHEAS-G. |
| FrameworkItem | `external_curie` | A factor or category of a framework. |
| CrosswalkEntry | `entry_key` | Join object: PIF to framework item with match strength. Editable review fields. |
| AssertedAbsence | `absence_key` | The ontology says the framework has no counterpart. Separate so an absence is never read as a match. |
| Rule | `rule_id` | A curated suggester phrase rule. Editable `status`. |
| Investigation | `investigation_id` | A CSB investigation (the incident object). |
| EvidenceExcerpt | `evidence_key` | Join object: a quoted passage coding a PIF to an investigation. Editable review fields. |

IDHEAS-G is the framework the task brief names. In the committed data it has no
factor-level crosswalk entries: its categories are bound to context dimensions
(`dimension_idheas_item` link). The coverage table reports this as dimension-level items,
not as zero coverage.

## Link types

| Link | Source to target | Cardinality |
|---|---|---|
| `pif_dimension` | Pif to ContextDimension | many_to_one |
| `dimension_idheas_item` | ContextDimension to FrameworkItem | many_to_one |
| `item_framework` | FrameworkItem to Framework | many_to_one |
| `entry_pif`, `entry_item`, `entry_framework` | CrosswalkEntry to Pif, FrameworkItem, Framework | many_to_one |
| `absence_pif`, `absence_framework` | AssertedAbsence to Pif, Framework | many_to_one |
| `rule_pif`, `rule_item` | Rule to Pif, FrameworkItem | many_to_one |
| `excerpt_investigation`, `excerpt_pif` | EvidenceExcerpt to Investigation, Pif | many_to_one |
| `pif_framework_item` | Pif to FrameworkItem, through CrosswalkEntry | many_to_many; `match_strength` is a link property; rejected entries hidden |
| `investigation_pif` | Investigation to Pif, through EvidenceExcerpt | many_to_many; `evidence_type` is a link property; rejected excerpts hidden |

PIFs reach incidents through `investigation_pif`, and reach the crosswalk through
`pif_framework_item`, so one traversal runs incident to PIF to framework item.

## Actions and the audit log

| Action | Effect |
|---|---|
| `flag_crosswalk_entry` | Entry goes `under_review`; still traversable. |
| `reject_crosswalk_entry` | Entry goes `rejected`; leaves traversal and coverage. |
| `reject_evidence_excerpt` | Excerpt goes `rejected`; the PIF-to-investigation link and evidence counts drop it. |
| `retire_rule` | Rule `status` becomes `retired`; `rules_triggered` skips it. |

`ObjectStore.apply()` is the only way to change an object after load. It checks
parameters (allowed values, length, `required_when`) and submission criteria, edits only
properties the spec marks editable, and appends actor, UTC time, parameters and the before
and after of each edit to the action log. A rejected action changes and logs nothing.
`edit_history(type, key)` returns one object's edits. Writeback lives in the store and its
exports; the committed CSV and TTL files are never modified.

## Functions

All are pure over an `ObjectStore` and honour writeback.

* `framework_coverage(store, framework, pif_curies=None, min_strength="broader")`: items
  reached, entries by strength, PIFs with a counterpart, asserted absent, or unaddressed.
* `rules_triggered(store, pif_curies)`: active rules for a factor set.
* `rules_triggered_by_text(store, text)`: runs active rules through `ehs_hfo.suggest`.
* `pif_evidence(store, pif)`: findings, recommendations and investigations for a PIF.
* `coverage_table(store)`: the data behind `ontology-coverage.md`. A test regenerates that
  page and fails if the committed copy differs.

None of these computes a human error probability, and coverage here means "the crosswalk
has an entry", not that a framework is validated against outcomes.

## Export

`export_sqlite` writes one table per object type (typed columns, enforced primary key,
arrays as JSON text), a `link_<name>` table per many-to-many link, `action_log` and
`ontology_spec`. `export_json` writes the same content as strict JSON, including the
link-integrity report (resolved, null, dangling, hidden per link).
