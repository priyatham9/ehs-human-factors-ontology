"""Build the ontology and export it: ``python3 -m ehs_hfo.foundry --out DIR``.

Objects come from the committed files only. Output goes to ``--out`` (and
``--coverage-md`` if given) only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Optional

from .export import export_json, export_sqlite
from .materialise import build_store
from .report import render_coverage_md


def main(argv: Optional[List[str]] = None) -> int:
    """Materialise, print a census and the link integrity report, write the exports."""
    ap = argparse.ArgumentParser(description="Build and export the human-factors ontology.")
    ap.add_argument("--out", type=Path, help="directory for ontology.sqlite and ontology.json")
    ap.add_argument("--coverage-md", type=Path, help="write the 'what the crosswalk covers' page here")
    args = ap.parse_args(argv)
    store = build_store()
    print("objects:")
    for name in store.spec.object_types:
        print(f"  {name}: {len(store.objects(name))}")
    print("links:")
    for name, c in store.integrity_report().items():
        print(f"  {name}: {json.dumps(c, sort_keys=True)}")
    if args.out:
        print("wrote", export_sqlite(store, args.out / "ontology.sqlite"))
        print("wrote", export_json(store, args.out / "ontology.json"))
    if args.coverage_md:
        args.coverage_md.parent.mkdir(parents=True, exist_ok=True)
        args.coverage_md.write_text(render_coverage_md(store), encoding="utf-8")
        print("wrote", args.coverage_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
