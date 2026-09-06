#!/usr/bin/env python3
"""Generate the human-readable crosswalk from the ontology.

The crosswalk is *derived*, never hand-edited. ``ontology/ehs-hfo.ttl`` is the
single source of truth for every correspondence; this script renders it as
Markdown and CSV so it can be read and diffed without a Turtle parser.

``tests/test_crosswalk.py`` regenerates both artefacts and fails if what is on
disk differs, so a crosswalk edited by hand cannot survive the test suite.

Usage::

    python3 tools/build_crosswalk.py           # write crosswalk/
    python3 tools/build_crosswalk.py --check   # exit 1 if out of date
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from typing import Dict, List, Optional, Sequence, Tuple

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))

from ehs_hfo.ontology import Alignment, Ontology  # noqa: E402

__all__ = ["build_markdown", "build_csv", "write_all", "CROSSWALK_DIR"]

CROSSWALK_DIR = os.path.join(_REPO_ROOT, "crosswalk")

#: Frameworks rendered as columns, in the order the README discusses them.
#: IDHEAS-G is excluded on purpose: it binds to the four *dimensions* via
#: ``ehs:correspondsToIdheasCategory``, not to individual factors, so it has no
#: cell in a factor-by-framework table.
FRAMEWORK_COLUMNS: Tuple[Tuple[str, str], ...] = (
    ("xw:fw-SPARH", "SPAR-H"),
    ("xw:fw-CREAM", "CREAM CPC"),
    ("xw:fw-HFACS", "HFACS"),
    ("xw:fw-HSE-PIF", "HSE PIF"),
)

#: Dimension display order: the order the four contexts are introduced.
DIMENSION_ORDER: Tuple[str, ...] = (
    "ehs:TaskContext",
    "ehs:OperationalContext",
    "ehs:HumanContext",
    "ehs:SystemContext",
)


def _strength_label(ontology: Ontology, alignment: Alignment) -> str:
    """Short lower-case name of an alignment's match strength."""
    curie = alignment.match_strength
    return curie.split(":")[-1].replace("Match", "").lower()


def _dimension_sort_key(curie: str) -> Tuple[int, str]:
    """Sort dimensions into DIMENSION_ORDER, unknown ones last, alphabetically."""
    try:
        return (DIMENSION_ORDER.index(curie), "")
    except ValueError:
        return (len(DIMENSION_ORDER), curie)


def _cell_entries(
    ontology: Ontology, factor_curie: str, framework_curie: str
) -> List[str]:
    """Rendered correspondences for one factor/framework cell.

    Returns an explicit "no counterpart" marker when the ontology asserts one,
    an empty list when nothing is asserted either way.
    """
    entries: List[str] = []
    for alignment in ontology.alignments_for(factor_curie):
        external = ontology.external_factors[alignment.external_factor]
        if external.framework != framework_curie:
            continue
        entries.append(
            f"{external.label} _({_strength_label(ontology, alignment)})_"
        )
    if not entries and framework_curie in ontology.no_counterpart.get(
        factor_curie, ()
    ):
        entries.append("**no counterpart**")
    return sorted(entries)


def _escape_md(text: str) -> str:
    """Make a string safe inside a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


def build_markdown(ontology: Ontology) -> str:
    """Render the full crosswalk as a Markdown document."""
    out = io.StringIO()
    w = out.write

    w("# Crosswalk: local factors to established PSF/PIF frameworks\n\n")
    w(
        "**This file is generated.** It is rendered from `ontology/ehs-hfo.ttl` by\n"
        "`tools/build_crosswalk.py`. Edit the Turtle, not this file; "
        "`tests/test_crosswalk.py`\nfails if the two disagree.\n\n"
    )
    w(
        "Every row states a correspondence that already exists in the published\n"
        "literature. The purpose of the table is to make it hard to mistake this\n"
        "vocabulary for a new taxonomy. It is not one. The four context dimensions are\n"
        "the four PIF context categories of IDHEAS-G (NUREG-2198), and the twenty\n"
        "factors are IDHEAS-G's twenty PIFs, adopted unchanged.\n\n"
    )

    w("## How to read a cell\n\n")
    w(
        "A cell names the counterpart factor in that framework and, in italics, how\n"
        "close the correspondence is. Strengths are **analyst judgements made against\n"
        "transcribed source wording**, not measured agreement. Nobody has adjudicated\n"
        "them but the author, and there is no inter-rater reliability figure to quote.\n\n"
    )
    for curie in (
        "ehs:MatchExact",
        "ehs:MatchClose",
        "ehs:MatchBroader",
        "ehs:MatchNarrower",
        "ehs:MatchPartial",
    ):
        node = ontology.graph.expand(curie)
        label = ontology.graph.literal(node, "rdfs:label") or curie
        definition = ontology.graph.literal(node, "skos:definition") or ""
        w(f"- **{label}** - {definition}\n")
    w(
        "\n`**no counterpart**` is an assertion, not a blank. It says the framework has\n"
        "no factor corresponding to this one, and it is recorded so that it can be\n"
        "argued with.\n\n"
    )
    w(
        "IDHEAS-G has no column. It binds to the four dimensions as whole categories\n"
        "rather than factor by factor; those bindings are listed per dimension below.\n\n"
    )

    # ---- the tables, one per dimension ---------------------------------- #
    w("## Factor tables\n")
    for dim_curie in sorted(ontology.dimensions, key=_dimension_sort_key):
        dimension = ontology.dimensions[dim_curie]
        w(f"\n### {dimension.label}\n\n")
        if dimension.idheas_category:
            external = ontology.external_factors.get(dimension.idheas_category)
            name = external.label if external else dimension.idheas_category
            w(
                f"Renames the IDHEAS-G context category **{name}** "
                f"(`{dimension.idheas_category}`).\n\n"
            )
        if dimension.definition:
            w(f"{_escape_md(dimension.definition)}\n\n")

        headers = ["Factor (this ontology)"] + [n for _, n in FRAMEWORK_COLUMNS]
        w("| " + " | ".join(headers) + " |\n")
        w("| " + " | ".join(["---"] * len(headers)) + " |\n")

        for factor in sorted(
            ontology.factors_in(dim_curie), key=lambda f: f.label
        ):
            cells = [f"**{_escape_md(factor.label)}**"]
            for framework_curie, _ in FRAMEWORK_COLUMNS:
                entries = _cell_entries(ontology, factor.curie, framework_curie)
                cells.append(_escape_md("; ".join(entries)) if entries else "-")
            w("| " + " | ".join(cells) + " |\n")

    # ---- alignment notes ------------------------------------------------ #
    noted = [
        (a, ontology.external_factors[a.external_factor])
        for a in sorted(
            ontology.alignments.values(),
            key=lambda a: (a.local_factor, a.external_factor),
        )
        if a.comment
    ]
    if noted:
        w("\n## Notes on individual rows\n\n")
        w(
            "Rows where the correspondence needed qualifying. These are the places a\n"
            "reviewer is most likely to disagree, which is why they are listed rather\n"
            "than buried in the Turtle.\n\n"
        )
        for alignment, external in noted:
            local = ontology.factor(alignment.local_factor)
            w(
                f"- **{local.label} → {external.label}** "
                f"({_strength_label(ontology, alignment)}) - "
                f"{_escape_md(alignment.comment or '')}\n"
            )

    # ---- coverage gaps -------------------------------------------------- #
    w("\n## Coverage gaps\n\n")
    w(
        "External factors this ontology does not cover. Recorded explicitly, because a\n"
        "crosswalk that lists only its successes is a sales document.\n\n"
    )
    for gap in sorted(
        ontology.coverage_gaps.values(),
        key=lambda g: (
            ontology.external_factors[g.uncovered_factor].framework or "",
            g.curie,
        ),
    ):
        external = ontology.external_factors[gap.uncovered_factor]
        framework = ontology.frameworks.get(external.framework or "")
        framework_label = framework.label if framework else "unknown framework"
        w(f"### {external.label} ({framework_label})\n\n")
        if gap.comment:
            w(" ".join(gap.comment.split()) + "\n\n")
        if gap.source_refs:
            w(f"Sources: {', '.join(f'`{r}`' for r in gap.source_refs)}\n\n")

    # ---- out of scope --------------------------------------------------- #
    out_of_scope = sorted(
        (e for e in ontology.external_factors.values() if e.out_of_scope_note),
        key=lambda e: (e.framework or "", e.curie),
    )
    if out_of_scope:
        w("## Deliberately not crosswalked\n\n")
        w(
            "Entries in the external inventories that are outcomes, structural\n"
            "containers or headings rather than context factors. Listed so the\n"
            "completeness check in `tests/test_crosswalk.py` has something to check\n"
            "against, and so their absence is not read as an oversight.\n\n"
        )
        w("| External entry | Framework | Reason |\n| --- | --- | --- |\n")
        for external in out_of_scope:
            framework = ontology.frameworks.get(external.framework or "")
            label = framework.label if framework else "-"
            w(
                f"| {_escape_md(external.label)} | {_escape_md(label)} "
                f"| {_escape_md(external.out_of_scope_note or '')} |\n"
            )

    # ---- provenance ----------------------------------------------------- #
    w("\n## Source documents\n\n")
    for framework in sorted(
        ontology.frameworks.values(), key=lambda f: f.label
    ):
        w(f"- **{framework.label}** - {framework.citation or 'no citation recorded'}")
        if framework.source_refs:
            w(f" [{', '.join(f'`{r}`' for r in framework.source_refs)}]")
        w("\n")
        if framework.comment:
            w(f" - {' '.join(framework.comment.split())}\n")
    w("\nFull bibliography with verification status: `../CITATIONS.md`.\n")
    return out.getvalue()


def build_csv(ontology: Ontology) -> str:
    """Render every correspondence as one CSV row.

    One row per (local factor, external factor) pair, plus one row per asserted
    absence. Long form rather than a matrix, because a factor can correspond to
    more than one factor in the same framework.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "dimension",
            "dimension_label",
            "factor_curie",
            "factor_label",
            "factor_verbatim_label",
            "framework",
            "framework_label",
            "external_curie",
            "external_label",
            "external_verbatim_label",
            "match_strength",
            "source_refs",
            "note",
        ]
    )

    rows: List[Sequence[str]] = []
    for alignment in ontology.alignments.values():
        factor = ontology.factor(alignment.local_factor)
        external = ontology.external_factors[alignment.external_factor]
        framework = ontology.frameworks.get(external.framework or "")
        dimension = ontology.dimensions[factor.dimension]
        rows.append(
            [
                factor.dimension,
                dimension.label,
                factor.curie,
                factor.label,
                factor.verbatim_label or "",
                external.framework or "",
                framework.label if framework else "",
                external.curie,
                external.label,
                external.verbatim_label or "",
                _strength_label(ontology, alignment),
                " ".join(alignment.source_refs),
                " ".join((alignment.comment or "").split()),
            ]
        )

    for factor_curie, frameworks in ontology.no_counterpart.items():
        factor = ontology.factor(factor_curie)
        dimension = ontology.dimensions[factor.dimension]
        for framework_curie in frameworks:
            framework = ontology.frameworks.get(framework_curie)
            rows.append(
                [
                    factor.dimension,
                    dimension.label,
                    factor.curie,
                    factor.label,
                    factor.verbatim_label or "",
                    framework_curie,
                    framework.label if framework else "",
                    "",
                    "",
                    "",
                    "none",
                    "",
                    "Asserted absence: no counterpart in this framework.",
                ]
            )

    for row in sorted(rows, key=lambda r: (r[0], r[3], r[6], r[8])):
        writer.writerow(row)
    return buffer.getvalue()


def write_all(
    ontology: Optional[Ontology] = None, out_dir: str = CROSSWALK_DIR
) -> Dict[str, str]:
    """Write both artefacts. Returns a mapping of path to content written."""
    ontology = ontology or Ontology.load()
    os.makedirs(out_dir, exist_ok=True)
    artefacts = {
        os.path.join(out_dir, "crosswalk.md"): build_markdown(ontology),
        os.path.join(out_dir, "crosswalk.csv"): build_csv(ontology),
    }
    for path, content in artefacts.items():
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(content)
    return artefacts


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Command line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if the files on disk are out of date",
    )
    parser.add_argument(
        "--out-dir", default=CROSSWALK_DIR, help="output directory"
    )
    args = parser.parse_args(argv)

    ontology = Ontology.load()
    expected = {
        os.path.join(args.out_dir, "crosswalk.md"): build_markdown(ontology),
        os.path.join(args.out_dir, "crosswalk.csv"): build_csv(ontology),
    }

    if args.check:
        stale = []
        for path, content in expected.items():
            if not os.path.exists(path):
                stale.append(f"{path}: missing")
                continue
            with open(path, encoding="utf-8") as handle:
                if handle.read() != content:
                    stale.append(f"{path}: out of date")
        if stale:
            for line in stale:
                print(line, file=sys.stderr)
            print(
                "run: python3 tools/build_crosswalk.py", file=sys.stderr
            )
            return 1
        print("crosswalk is up to date")
        return 0

    for path in write_all(ontology, args.out_dir):
        print(f"wrote {os.path.relpath(path, _REPO_ROOT)}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
