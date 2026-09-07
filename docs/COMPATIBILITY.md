# Compatibility of SRK/GEMS error types with IDHEAS-G failure modes

This document exists because an internal reviewer pointed out, correctly,
that the ontology had taken the twenty IDHEAS-G performance influencing
factors (PIFs) out of the structure that gives them meaning. In NUREG-2198
a PIF is not a free-standing context variable. Its applicability and its
effect are stated relative to a macrocognitive function (detection,
understanding, decisionmaking, action execution, interteam coordination) and
to the cognitive failure modes of that function. The earlier version of this
repository bolted the PIF list onto Rasmussen's skill-rule-knowledge (SRK)
levels and Reason's generic error-modelling system (GEMS) with no argument
for why that was allowed, and its roll-up rules aggregated PIFs across a
whole context category, which IDHEAS-G does not do.

What changed, in one paragraph: `ontology/ehs-hfo.ttl` now carries the five
macrocognitive functions as `ehs:MacrocognitiveFunction` individuals, one
function-level `ehs:CognitiveFailureMode` for each, and two properties on
every PIF, `ehs:appliesToFunction` and `ehs:affectsFailureMode`, so that a
PIF's reach is stated per function rather than globally. The engine's
dimension roll-up (old R07 to R09 and old R31) is gone. In its place are
function-specific rules (R07, R08, R09, R12, R13, R31, R35) whose
conclusions carry the function and failure mode they belong to, and the
derivation trace prints both. The SRK/GEMS rules (R10, R11, R20 to R24) are
retained, and the rest of this document says on what terms.

## The two vocabularies

IDHEAS-G (NUREG-2198) models a human action as a chain of macrocognitive
functions. Each function has failure modes, and PIFs are the context
conditions that raise the likelihood of those failure modes. The unit of
analysis is "this function, failing in this way, under these PIFs".

Rasmussen (1983) classifies performance by the cognitive control level in
use: skill-based, rule-based, knowledge-based. Reason (1990) attaches an
error type to each level: skill-based slips and lapses, rule-based mistakes,
knowledge-based mistakes. The unit of analysis is "this level of control,
producing this kind of error".

These are different cuts through the same phenomena. One is organised by
what the operator is doing (function); the other by how the operator is
doing it (control level). Neither source maps one onto the other, and this
repository does not claim that either author endorsed such a mapping.

## The mapping, as asserted in the ontology

The ontology records the mapping with `ehs:approximatesFailureMode` on each
error mode. It is the repository author's mapping and is marked as such in
the property's comment.

| SRK/GEMS error mode | Approximates IDHEAS-G failure mode of | Quality |
|---|---|---|
| skill-based slip or lapse | action execution | clean |
| rule-based mistake | decisionmaking | partial |
| knowledge-based mistake | understanding, decisionmaking | partial |

### Where the mapping is clean

Skill-based slips and lapses are execution failures of a correct intention.
IDHEAS-G's action execution function is the carrying out of a selected
response. A slip (wrong motor action) or a lapse (omitted step) is a failure
of exactly that function. The correspondence holds in both directions: an
action-execution failure with correct detection, understanding and decision
is, in GEMS terms, a slip or lapse.

### Where the mapping is not clean

Rule-based mistakes are the correct execution of a wrong rule, or the
misapplication of a good one. That is a decision failure, so the mapping to
decisionmaking is defensible. But rule selection in GEMS is triggered by
pattern recognition, and a wrong rule is often chosen because the situation
was misread. That part of the mechanism belongs to IDHEAS-G understanding,
not decisionmaking. The ontology maps rule-based mistakes to decisionmaking
only and accepts that it understates the understanding component.

Knowledge-based mistakes are failures of reasoning in a novel situation.
IDHEAS-G splits that reasoning into understanding (build the situation
model) and decisionmaking (choose a response from it). Rasmussen and Reason
do not split it. The ontology maps the knowledge-based mistake to both
functions, which is honest about the ambiguity but means a single GEMS
error type fans out to two IDHEAS-G failure modes and cannot be pushed back
to one.

Detection has no SRK/GEMS counterpart. Failure to notice a cue is not a
slip, a rule-based mistake or a knowledge-based mistake in Reason's scheme;
Reason treats attentional failure as a precursor to slips rather than as an
error type of its own. Interteam coordination likewise has no counterpart:
SRK and GEMS are single-operator models. The ontology therefore has PIFs
(workplace visibility, noise and communication pathways, staffing, team and
organisation factors, among others) that apply to detection or interteam
coordination and predispose to no SRK/GEMS error mode at all. That gap is
real and is left visible.

## What follows for the rules

1. Rules R07, R08, R09, R12 and R13 reason only in IDHEAS-G terms. They read
   `factorAppliesToFunction` and `factorAffectsFailureMode` and their
   conclusions name the function and the failure mode. These rules are the
   ones that carry the "IDHEAS-G structure" claim.
2. Rules R10, R11 and R20 to R24 reason only in SRK/GEMS terms. They read
   `factorPredisposesTo` and `factorRaisesDemandOn`, which are interpretive
   links the ontology marks as such. These rules do not depend on the
   function structure and do not feed it.
3. No rule converts a conclusion from one vocabulary into the other. The
   `approximatesFailureMode` property is documentation for the reader; the
   engine does not fire on it. A knowledge-based mistake flag and a failure
   of understanding flag in the same report are two readings of the same
   inputs, not one finding derived from the other.
4. The screening bands (R30 to R35, all marked `convention`) read both
   vocabularies. That is a design choice by the author of this repository
   with no source behind it, and the trace says so on every band line.

## What is therefore not claimed

- Not claimed: that NUREG-2198 defines or endorses the function assignment
  of each PIF given here. IDHEAS-G does state PIF effects per function, but
  the specific assignments in the `.ttl` are the repository author's reading
  and are marked with a boundary note on every factor.
- Not claimed: that IDHEAS-G's finer failure modes within each function are
  modelled. Only the function-level failure is present.
- Not claimed: that SRK/GEMS error types are equivalent to IDHEAS-G failure
  modes. The mapping is one-to-one in one case, one-to-many in another, and
  absent for two functions.
- Not claimed: any effect size, weight, multiplier or probability for any
  PIF on any failure mode. The engine produces ordinal flags and traces.
- Not claimed: that aggregating PIFs across a context category (task,
  operational, human, system) has any basis. That aggregation has been
  removed. The four dimensions remain only as the grouping in which the
  factors are listed and reported, matching the IDHEAS-G category names.

## Where to look

- Classes and properties: `ontology/ehs-hfo.ttl`, sections 6a and the
  object-property block.
- Function table for all twenty factors: `crosswalk/crosswalk.md`, section
  "Macrocognitive function applicability".
- Rules: `src/ehs_hfo/rules.py`; run `PYTHONPATH=src python3 -m ehs_hfo rules`.
- Worked example with function-level trace:
  `PYTHONPATH=src python3 -m ehs_hfo assess examples/reactor_startup_nonroutine.json`.
- Tests: `tests/test_macrocognitive.py`, `tests/test_reactor_scenario.py`.
