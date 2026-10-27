#!/usr/bin/env python3
"""Blinded second-coder protocol for the CSB incident codings.

The first coder wrote the PIF rules and coded the incidents in
``incidents/csb_coding.csv``. This tool lets an independent coder code the same
excerpts without seeing those codes, then measures agreement. Standard library only.

    python3 tools/second_coder.py export-sheet  [--out FILE]   # blank coding sheet
    python3 tools/second_coder.py export-codebook [--out FILE] # PIF list the coder may use
    python3 tools/second_coder.py report SHEET [SHEET ...] [--markdown]

The sheet holds the investigation name, source URL and quoted excerpt. It never
holds the existing codes, the evidence type (finding or recommendation), or the
cohort, because each of those would reveal how the first coder read the excerpt.

Unit of analysis: one excerpt. For each PIF, coder 1 either coded the excerpt
to it or did not; so did coder 2. Kappa and percent agreement are computed on
that 2x2 table over the excerpts coder 2 rated. Excerpts are the first coder's
quotes, so every excerpt carries at least one first-coder code; agreement is
measured on a sample selected by coder 1 and prevalence is not representative.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import sys
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Set

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))
sys.path.insert(0, _REPO_ROOT)

from ehs_hfo.ontology import Ontology  # noqa: E402
from tools.build_csb_coding import CODING, INVESTIGATIONS, read  # noqa: E402

SHEET_FIELDS = ["excerpt_id", "investigation", "source_url", "excerpt", "pifs", "coder_notes"]
NONE_TOKEN = "NONE"
SEPARATOR = ";"


def excerpt_id(investigation_id: str, quoted_text: str) -> str:
    """Stable id from the investigation and quote, so it does not depend on row order."""
    digest = hashlib.sha256(f"{investigation_id}\n{quoted_text}".encode("utf-8")).hexdigest()
    return "x" + digest[:10]


def excerpts() -> List[Dict[str, str]]:
    """Unique (investigation, quote) excerpts, ordered by id (not by investigation or factor)."""
    inv = {r["investigation_id"]: r for r in read(INVESTIGATIONS)}
    seen: Dict[str, Dict[str, str]] = {}
    for r in read(CODING):
        eid = excerpt_id(r["investigation_id"], r["quoted_text"])
        seen.setdefault(
            eid,
            {
                "excerpt_id": eid,
                "investigation": inv[r["investigation_id"]]["name"],
                "source_url": inv[r["investigation_id"]]["source_url"],
                "excerpt": r["quoted_text"],
            },
        )
    return sorted(seen.values(), key=lambda e: e["excerpt_id"])


def first_coder_sets() -> Dict[str, Set[str]]:
    """excerpt_id -> set of factor CURIEs coded by the first coder."""
    out: Dict[str, Set[str]] = defaultdict(set)
    for r in read(CODING):
        out[excerpt_id(r["investigation_id"], r["quoted_text"])].add(r["factor_curie"])
    return dict(out)


def _write(rows: Iterable[Dict[str, str]], fields: Sequence[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(fields), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    return buf.getvalue()


def sheet_csv() -> str:
    return _write(({**e, "pifs": "", "coder_notes": ""} for e in excerpts()), SHEET_FIELDS)


def codebook_csv(ont: Ontology) -> str:
    rows = [
        {
            "factor_curie": f.curie,
            "label": f.label,
            "dimension": f.dimension,
            "note": f.comment or "",
        }
        for f in sorted(ont.factors.values(), key=lambda f: f.curie)
    ]
    return _write(rows, ["factor_curie", "label", "dimension", "note"])


class SheetError(ValueError):
    """A returned sheet is malformed."""


def parse_sheet(text: str, ont: Ontology, valid_ids: Optional[Set[str]] = None) -> Dict[str, Set[str]]:
    """Return excerpt_id -> set of CURIEs for rated excerpts.

    ``pifs`` is a ``;``-separated list of CURIEs (``ehs:Staffing``) or local names
    (``Staffing``). ``NONE`` means the coder rated the excerpt and found no PIF. A
    blank cell means not rated and the excerpt is left out of the comparison.
    """
    valid = valid_ids if valid_ids is not None else {e["excerpt_id"] for e in excerpts()}
    reader = csv.DictReader(io.StringIO(text))
    missing = {"excerpt_id", "pifs"} - set(reader.fieldnames or [])
    if missing:
        raise SheetError(f"missing column(s): {', '.join(sorted(missing))}")
    names = {f.local_name.lower(): f.curie for f in ont.factors.values()}
    out: Dict[str, Set[str]] = {}
    for n, row in enumerate(reader, start=2):
        eid = (row["excerpt_id"] or "").strip()
        if eid not in valid:
            raise SheetError(f"line {n}: unknown excerpt_id {eid!r}")
        if eid in out:
            raise SheetError(f"line {n}: duplicate excerpt_id {eid}")
        cell = (row["pifs"] or "").strip()
        if not cell:
            continue
        if cell.upper() == NONE_TOKEN:
            out[eid] = set()
            continue
        picked: Set[str] = set()
        for tok in (t.strip() for t in cell.split(SEPARATOR)):
            if not tok:
                continue
            if tok.upper() == NONE_TOKEN:
                raise SheetError(f"line {n}: NONE cannot be combined with PIFs")
            curie = tok if tok in ont.factors else names.get((tok[4:] if tok.startswith("ehs:") else tok).lower())
            if curie is None:
                raise SheetError(f"line {n}: unknown PIF {tok!r}")
            picked.add(curie)
        out[eid] = picked
    return out


def cohen_kappa(a: int, b: int, c: int, d: int) -> Optional[float]:
    """Kappa for a 2x2 table: a both yes, b only rater 1, c only rater 2, d both no.

    Returns None when chance agreement is 1 (a rater used one category throughout),
    where kappa is undefined.
    """
    n = a + b + c + d
    if n == 0:
        return None
    po = (a + d) / n
    pe = ((a + b) * (a + c) + (c + d) * (b + d)) / (n * n)
    if pe == 1:
        return None
    return (po - pe) / (1 - pe)


def agreement(
    first: Dict[str, Set[str]], second: Dict[str, Set[str]], factors: Iterable[str]
) -> List[Dict[str, object]]:
    """Per-PIF table over excerpts rated by the second coder, for PIFs either coder used."""
    rated = [e for e in second if e in first]
    used = {f for e in rated for f in first[e] | second[e]}
    rows: List[Dict[str, object]] = []
    for f in sorted(set(factors) & used):
        a = sum(1 for e in rated if f in first[e] and f in second[e])
        b = sum(1 for e in rated if f in first[e] and f not in second[e])
        c = sum(1 for e in rated if f not in first[e] and f in second[e])
        d = len(rated) - a - b - c
        rows.append(
            {
                "factor": f,
                "n": len(rated),
                "both": a,
                "only_coder1": b,
                "only_coder2": c,
                "neither": d,
                "percent_agreement": 100 * (a + d) / len(rated),
                "kappa": cohen_kappa(a, b, c, d),
            }
        )
    return rows


def pooled(rows: Sequence[Dict[str, object]]) -> Optional[Dict[str, object]]:
    """Kappa over all (excerpt, PIF) decisions pooled across the PIFs in ``rows``."""
    if not rows:
        return None
    a, b, c, d = (sum(int(r[k]) for r in rows) for k in ("both", "only_coder1", "only_coder2", "neither"))
    return {
        "decisions": a + b + c + d,
        "percent_agreement": 100 * (a + d) / (a + b + c + d),
        "kappa": cohen_kappa(a, b, c, d),
    }


def _fmt(x: Optional[float], digits: int = 2) -> str:
    return "undefined" if x is None else f"{x:.{digits}f}"


def render(
    sheets: Dict[str, Dict[str, Set[str]]], first: Dict[str, Set[str]], ont: Ontology, markdown: bool
) -> str:
    lines: List[str] = []
    for name, second in sheets.items():
        rows = agreement(first, second, ont.factors)
        n = len([e for e in second if e in first])
        lines.append(f"Coder sheet {name}: {n} excerpts rated")
        lines.append("")
        head = ["PIF", "both", "only 1", "only 2", "neither", "% agree", "kappa"]
        body = [
            [
                ont.factor(str(r["factor"])).label,
                str(r["both"]),
                str(r["only_coder1"]),
                str(r["only_coder2"]),
                str(r["neither"]),
                f"{r['percent_agreement']:.1f}",
                _fmt(r["kappa"]),  # type: ignore[arg-type]
            ]
            for r in rows
        ]
        p = pooled(rows)
        if p:
            body.append(
                [
                    "All PIFs pooled",
                    "",
                    "",
                    "",
                    "",
                    f"{p['percent_agreement']:.1f}",
                    _fmt(p["kappa"]),  # type: ignore[arg-type]
                ]
            )
        if markdown:
            lines.append("| " + " | ".join(head) + " |")
            lines.append("|" + "---|" * len(head))
            lines += ["| " + " | ".join(r) + " |" for r in body]
        else:
            lines.append("\t".join(head))
            lines += ["\t".join(r) for r in body]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("export-sheet", "export-codebook"):
        p = sub.add_parser(name)
        p.add_argument("--out", help="write here instead of stdout")
    rep = sub.add_parser("report", help="agreement between coder 1 and each returned sheet")
    rep.add_argument("sheets", nargs="+")
    rep.add_argument("--markdown", action="store_true")
    args = parser.parse_args(argv)

    if args.command in ("export-sheet", "export-codebook"):
        text = sheet_csv() if args.command == "export-sheet" else codebook_csv(Ontology.load())
        if args.out:
            with open(args.out, "w", encoding="utf-8", newline="") as h:
                h.write(text)
        else:
            sys.stdout.write(text)
        return 0

    ont = Ontology.load()
    parsed: Dict[str, Dict[str, Set[str]]] = {}
    for path in args.sheets:
        with open(path, encoding="utf-8", newline="") as h:
            try:
                parsed[os.path.basename(path)] = parse_sheet(h.read(), ont)
            except SheetError as exc:
                print(f"{path}: {exc}", file=sys.stderr)
                return 2
    sys.stdout.write(render(parsed, first_coder_sets(), ont, args.markdown))
    return 0


if __name__ == "__main__":
    sys.exit(main())
