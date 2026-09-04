# Synthetic scenario corpus

Everything under this directory is **fabricated**. Read that literally.

The 48 JSON files in `scenarios/` were produced by `generate_scenarios.py` from a
seeded pseudo-random number generator. They are not observations. They are not
derived from OSHA filings, from incident records, from any employer's data, or
from any real event. No establishment, employer, worker or incident is
represented, in whole or in part.

## Why it exists

To exercise the rule engine, and nothing else. Made-up inputs can establish
software properties, so that is all this corpus is used for:

- evaluation terminates on every scenario
- derivation traces stay well-formed and every derived fact is reachable from
  the scenario inputs
- every rule in the base is reachable by at least one input
- the banding rules behave monotonically — degrading a factor never improves the
  band
- the unassessed-factor path is exercised, since a factor omitted from a
  scenario is treated as unknown rather than as satisfactory

`tests/test_synthetic.py` and `tests/test_engine.py` are the consumers.

## What no one may do with it

**No number computed from this corpus is an empirical finding about anything.**

The distribution of screening bands across these 48 files is a property of the
sampling weights in `_ARCHETYPES`, which the author picked by hand. It measures
those weights. It does not measure how often real work is degraded, how often
chemical operations run non-routine, or how any population of real scenarios
would band. Quoting a frequency from this corpus as though it described real
work would be a fabrication, and the fact that the number was computed by
running real code does not change that.

If a headline number in a paper, a README, a slide or a petition can be traced
back to this directory, it is wrong and it should be removed.

## Guardrails

Four, layered so that a file cannot quietly lose its label:

1. Every generated file carries `"synthetic": true` and a `provenance` string
   spelling out what the data is.
2. Every file carries a `generator` block naming the script and the archetype,
   with a note that frequencies over the corpus measure the sampling weights.
3. `Scenario.from_json_file` reads both fields through to the report, and the
   assessment output prints a banner for any scenario flagged synthetic.
4. `tests/test_synthetic.py` fails if any file in `scenarios/` is missing the
   flag, the provenance header, or the generator block.

## Reproducing it

Output is a pure function of `--seed` and `--count`, so the committed files can
be checked rather than trusted:

```
python3 synthetic/generate_scenarios.py --check    # verify what is on disk
python3 synthetic/generate_scenarios.py            # regenerate in place
```

`--check` exits non-zero if any committed file differs from what the generator
produces, if a file is missing, or if there is a file in `scenarios/` the
generator did not write. The test suite runs it.

Defaults are `--seed 20260904` and `--count 48`. Changing either changes the
whole corpus; regenerate and commit the result rather than editing a scenario by
hand.

## Real scenarios

The one hand-written scenario in the repository is
`examples/reactor_startup_nonroutine.json`. It is **not** synthetic in this
sense and does not live here — it is an illustrative worked example written by
hand to demonstrate a specific chain of reasoning, and it carries
`"synthetic": false` with its own provenance note. It is still not a record of
any real event, and it contains no site data. It is an illustration, and the
README says so where it is used.
