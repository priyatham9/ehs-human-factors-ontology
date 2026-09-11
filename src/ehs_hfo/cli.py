"""Command-line entry point.

    python -m ehs_hfo assess examples/reactor_startup_nonroutine.json
    python -m ehs_hfo factors
    python -m ehs_hfo crosswalk --framework xw:fw-SPARH
    python -m ehs_hfo gaps
    python -m ehs_hfo rules
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from .assessment import assess, render_text
from .export import export
from .facts import Scenario
from .ontology import Ontology
from .rules import build_program


def _cmd_assess(args: argparse.Namespace) -> int:
    ontology = Ontology.load(args.ontology)
    scenario = Scenario.from_json_file(args.scenario)
    assessment = assess(scenario, ontology)
    if args.json:
        payload = {
            "scenario_id": scenario.scenario_id,
            "synthetic": scenario.synthetic,
            "screening_band": assessment.screening_band,
            "coverage": {
                "assessed": assessment.coverage[0],
                "total": assessment.coverage[1],
            },
            "incomplete": assessment.incomplete,
            "elevated_error_modes": assessment.elevated_error_modes,
            "aggravated_error_modes": assessment.aggravated_error_modes,
            "unsupported_control_demands": assessment.unsupported_demands,
            "unmitigated_degradations": assessment.unmitigated,
            "rules_fired": assessment.result.rules_fired(),
            "band_trace": assessment.band_trace(),
            "disclaimer": (
                "Ordinal screening label. Not a human error probability, not a "
                "rate, not calibrated against outcome data."
            ),
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_text(assessment, show_traces=not args.no_traces))
    return 0


def _cmd_factors(args: argparse.Namespace) -> int:
    ontology = Ontology.load(args.ontology)
    for dim_curie in sorted(ontology.dimensions):
        dimension = ontology.dimensions[dim_curie]
        print(f"{dimension.label}  (IDHEAS-G: {dimension.idheas_category})")
        for factor in ontology.factors_in(dim_curie):
            print(f"  {factor.curie}")
            print(f"      label:    {factor.label}")
            if factor.verbatim_label:
                print(f"      NUREG-2198 wording: {factor.verbatim_label}")
            for proxy in factor.observable_proxies:
                print(f"      proposed proxy (unvalidated): {proxy}")
            for note in factor.boundary_notes:
                print(f"      boundary: {note}")
        print()
    return 0


def _cmd_crosswalk(args: argparse.Namespace) -> int:
    ontology = Ontology.load(args.ontology)
    rows = sorted(
        ontology.alignments.values(),
        key=lambda a: (a.local_factor, a.external_factor),
    )
    for alignment in rows:
        external = ontology.external_factors[alignment.external_factor]
        if args.framework and external.framework != args.framework:
            continue
        strength = alignment.match_strength.split(":")[-1].replace("Match", "").lower()
        print(
            f"{ontology.factor(alignment.local_factor).label}"
            f" -[{strength}]->  {external.label}"
            f"  ({external.framework})  [{', '.join(alignment.source_refs)}]"
        )
    for factor_curie, frameworks in sorted(ontology.no_counterpart.items()):
        for framework in frameworks:
            if args.framework and framework != args.framework:
                continue
            print(
                f"{ontology.factor(factor_curie).label}"
                f" -[none]->  (no counterpart in {framework})"
            )
    return 0


def _cmd_gaps(args: argparse.Namespace) -> int:
    ontology = Ontology.load(args.ontology)
    for gap in sorted(ontology.coverage_gaps.values(), key=lambda g: g.curie):
        external = ontology.external_factors[gap.uncovered_factor]
        print(f"{external.label}  ({external.framework})")
        if gap.comment:
            for line in gap.comment.splitlines():
                print(f"    {line.strip()}")
        print()
    return 0


def _cmd_rules(args: argparse.Namespace) -> int:
    program = build_program()
    print(f"{len(program.rules)} rules in {len(program.strata)} strata")
    for depth, stratum in enumerate(program.strata):
        print(f"\nStratum {depth}")
        for rule in stratum:
            refs = ", ".join(rule.source_refs) if rule.source_refs else "no source"
            print(f"  {rule.rule_id}  [{rule.basis}; {refs}]")
            print(f"    {rule}")
    return 0



def _cmd_export(args: argparse.Namespace) -> int:
    ontology = Ontology.load(args.ontology)
    output = export(ontology, format=args.format)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Exported {args.format} to {args.out}")
    else:
        print(output)
    return 0

def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser."""
    parser = argparse.ArgumentParser(
        prog="ehs_hfo",
        description=(
            "Ontology, crosswalk and rule engine for contextual human-error "
            "screening. Produces no probabilities."
        ),
    )
    parser.add_argument(
        "--ontology",
        default=None,
        help="path to ehs-hfo.ttl (defaults to the copy in this repository)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    assess_parser = sub.add_parser("assess", help="evaluate one scenario JSON file")
    assess_parser.add_argument("scenario")
    assess_parser.add_argument(
        "--json", action="store_true", help="emit machine-readable output"
    )
    assess_parser.add_argument(
        "--no-traces", action="store_true", help="omit derivation traces"
    )
    assess_parser.set_defaults(func=_cmd_assess)

    factors_parser = sub.add_parser("factors", help="list the factors by dimension")
    factors_parser.set_defaults(func=_cmd_factors)

    crosswalk_parser = sub.add_parser("crosswalk", help="print the crosswalk")
    crosswalk_parser.add_argument(
        "--framework",
        default=None,
        help="restrict to one framework, e.g. xw:fw-SPARH",
    )
    crosswalk_parser.set_defaults(func=_cmd_crosswalk)

    gaps_parser = sub.add_parser("gaps", help="print recorded coverage gaps")
    gaps_parser.set_defaults(func=_cmd_gaps)

    rules_parser = sub.add_parser("rules", help="print the rule base and its strata")
    rules_parser.set_defaults(func=_cmd_rules)


    export_parser = sub.add_parser("export", help="export ontology in standard formats")
    export_parser.add_argument(
        "--format",
        choices=["jsonld", "owlxml"],
        default="jsonld",
        help="export format (default: jsonld)",
    )
    export_parser.add_argument(
        "--out",
        default=None,
        help="output file path (default: print to stdout)",
    )
    export_parser.set_defaults(func=_cmd_export)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point. Returns a process exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover - thin wrapper
    sys.exit(main())
