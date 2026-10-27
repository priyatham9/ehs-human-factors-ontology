"""Build ``docs/suggester.html`` from the suggester evaluation.

Every number on the page is computed here from ``incidents/`` and
``crosswalk/pif_rules.csv``; ``tests/test_suggester.py`` fails if the committed
page differs from this output.

    python3 tools/build_suggester_page.py --write
"""

from __future__ import annotations

import html
import os
import sys
from collections import Counter
from typing import Dict, Sequence

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO_ROOT, "src"))
sys.path.insert(0, _REPO_ROOT)

from ehs_hfo.ontology import Ontology  # noqa: E402
from tools.evaluate_suggester import evaluate, macro_recall, ratio, summarise  # noqa: E402

OUTPUT = os.path.join(_REPO_ROOT, "docs", "suggester.html")
SITE = "https://priyatham9.github.io/ehs-human-factors-ontology/"

CSS = """
:root{color-scheme:light;--paper:#F7F7F3;--surface:#FFFFFF;--ink:#101311;--ink-2:#3A403C;--muted:#666D68;--rule:#D6D7CE;--accent:#1E40AF;--warn:#8A5A00;--warn-wash:#FBF0DC}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--paper:#0A0C10;--surface:#12151C;--ink:#EAECF2;--ink-2:#BFC4CF;--muted:#838A99;--rule:#262B36;--accent:#7C9EFF;--warn:#E3B25F;--warn-wash:#241C0C}}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 "Archivo",ui-sans-serif,system-ui,sans-serif}
.wrap{max-width:960px;margin:0 auto;padding:0 16px}
header.top{border-bottom:1px solid var(--rule);padding:12px 0;font-size:14px}
header.top a{color:var(--accent);margin-right:14px}
h1{font-size:clamp(28px,5vw,44px);line-height:1.1;margin:32px 0 8px}
h2{margin:36px 0 8px;font-size:22px}
code,.mono{font-family:"IBM Plex Mono",ui-monospace,Menlo,Consolas,monospace;font-size:.9em}
a{color:var(--accent)}
.warn{background:var(--warn-wash);border-left:4px solid var(--warn);padding:12px 16px;margin:20px 0}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:14px;margin:12px 0}
th,td{border-bottom:1px solid var(--rule);padding:6px 8px;text-align:left;vertical-align:top}
th{font-weight:600}
td.n{text-align:right;font-variant-numeric:tabular-nums}
footer{border-top:1px solid var(--rule);margin-top:48px;padding:20px 0;color:var(--muted);font-size:14px}
pre{background:var(--surface);border:1px solid var(--rule);padding:12px;overflow-x:auto;font-size:13px}
"""


def e(text: object) -> str:
    return html.escape(str(text))


def per_pif_table(ont: Ontology, per: Dict[str, Counter], gold: Counter) -> str:
    rows = []
    for f in sorted(set(per) | set(gold), key=lambda x: (-gold[x], x)):
        c = per.get(f, Counter())
        rows.append(
            f"<tr><td>{e(ont.factor(f).label)}</td><td class=n>{gold[f]}</td><td class=n>{c['tp']}</td>"
            f"<td class=n>{c['fp']}</td><td class=n>{c['fn']}</td>"
            f"<td class=n>{ratio(c['tp'], c['tp'] + c['fp'])}</td><td class=n>{ratio(c['tp'], c['tp'] + c['fn'])}</td></tr>")
    return ("<div class=scroll><table><thead><tr><th>PIF</th><th>Gold</th><th>TP</th><th>FP</th><th>FN</th>"
            "<th>Precision</th><th>Recall</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>")


def overall_rows(results: Dict[str, Counter], nrules: Dict[str, int]) -> str:
    rows = []
    for name, per in results.items():
        tp, fp, fn = summarise(per)
        rows.append(
            f"<tr><td>{e(name)}</td><td class=n>{nrules[name]}</td><td class=n>{tp}</td><td class=n>{fp}</td>"
            f"<td class=n>{fn}</td><td class=n>{ratio(tp, tp + fp)}</td><td class=n>{ratio(tp, tp + fn)}</td>"
            f"<td class=n>{macro_recall(per)}</td></tr>")
    return "".join(rows)


TABLE_HEAD = ("<div class=scroll><table><thead><tr><th>Rule set</th><th>Rules</th><th>TP</th><th>FP</th>"
              "<th>FN</th><th>Precision</th><th>Recall</th><th>Macro recall</th></tr></thead><tbody>")


def render(ont: Ontology) -> str:
    n_inv, n_pairs, gold, results, nrules = evaluate(ont)
    d_inv, d_pairs, d_gold, d_res, d_rules = evaluate(ont, "development")
    h_inv, h_pairs, h_gold, h_res, h_rules = evaluate(ont, "held_out")
    curated_name = next(n for n in results if n.startswith("curated (")
                        )
    title = "PIF suggester - ehs-human-factors-ontology"
    desc = ("A rule-based, no-ML suggester from incident narrative text to the 20 PIFs, with every "
            "suggestion traced to the crosswalk, evaluated against hand-coded CSB incidents.")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}" />
<link rel="canonical" href="{SITE}suggester.html" />
<style>{CSS}</style>
</head>
<body>
<header class="top"><div class="wrap"><a href="https://priyatham9.github.io/grounded/">Grounded</a><a href="{SITE}">ehs-human-factors-ontology</a><a href="{SITE}crosswalk.html">Crosswalk</a><b>Suggester</b></div></header>
<main class="wrap">
<h1>From incident narrative to candidate PIFs, with the rule shown</h1>
<p>A keyword and phrase matcher. No machine learning. Each suggestion names the rule that fired, the words it matched,
and the crosswalk alignment the rule is traced to. It is a prompt for a human coder, not a coding.</p>
<div class="warn"><b>Read the result with this in mind.</b> The test text is the set of quoted CSB passages that the
{n_pairs} gold codings were made from, across {n_inv} coded investigations and {len(gold)} PIFs. Recall therefore measures
vocabulary overlap with text a coder already marked, not discovery in free-running narratives. The investigations split into a
<b>development</b> cohort ({d_inv} investigations, {d_pairs} pairs), which the rule author had read when writing the curated
rules, and a <b>held-out</b> cohort ({h_inv} investigations, {h_pairs} pairs), coded after the rules were committed and not
used to change them. Only the held-out figures are out of sample. The same person coded both cohorts and wrote the rules, and
the held-out quotes are mostly recommendation wording from summary pages, picked by searching each factor's topic, which favours keyword
matches and inflates recall. Precision is against an incomplete gold standard.
Counts are small: one pair moves a PIF's score by many points.</div>

<h2>Held-out cohort (out of sample)</h2>
{TABLE_HEAD}{overall_rows(h_res, h_rules)}</tbody></table></div>
<p>In the held-out cohort the curated and the &ldquo;without development-derived rules&rdquo; rows are identical, because no
rule phrase was taken from these quotes.</p>
<h2>Development cohort (resubstitution)</h2>
{TABLE_HEAD}{overall_rows(d_res, d_rules)}</tbody></table></div>
<h2>All coded investigations</h2>
{TABLE_HEAD}{overall_rows(results, nrules)}</tbody></table></div>
<p>The baseline, which was not tuned on any incident, finds a minority of the gold pairs in both cohorts. The majority-class
control (always predict the most frequent development PIF) shows how much of any precision figure here is base rate. Per-PIF
tables for the held-out cohort:</p>
<h2>Per PIF, curated rules, held-out cohort</h2>
{per_pif_table(ont, h_res[curated_name], h_gold)}
<p>Per-PIF tables for the other rule sets and for all investigations are in
<a href="https://github.com/priyatham9/ehs-human-factors-ontology/blob/main/incidents/suggester_eval.md">incidents/suggester_eval.md</a>.
Only {len(gold)} of the 20 PIFs have any gold coding, so recall for the other {20 - len(gold)} is untested; for those, the rules can only
score false positives here.</p>

<h2>How the rules are traced</h2>
<p>Each row of <a href="https://github.com/priyatham9/ehs-human-factors-ontology/blob/main/crosswalk/pif_rules.csv">crosswalk/pif_rules.csv</a>
gives a phrase, a PIF, and an external factor (SPAR-H, CREAM, HFACS or HSE) that the ontology aligns to that PIF; a test fails if
the alignment does not exist. A hit therefore unwinds as phrase, PIF, external factor, citation. A trailing <code>*</code>
matches any word ending. The baseline rule set is derived by code from the ontology's own labels, with no choice made by hand.</p>
<pre>python3 -m ehs_hfo suggest narrative.txt
python3 -m ehs_hfo suggest narrative.txt --json
python3 -m ehs_hfo suggest narrative.txt --rules baseline
python3 tools/evaluate_suggester.py --write</pre>

<h2>What would make it a real test</h2>
<p>The held-out cohort meets the &ldquo;rules frozen before the test text is read&rdquo; condition. It does not meet the
other two: it is coded by the rule author, and it is quotes from summary pages, not full narratives. A second coder, and
full-report text, are still needed.</p>
</main>
<footer><div class="wrap">Priyatham Chimmani. Independent research. Generated by <span class="mono">tools/build_suggester_page.py</span>
from <span class="mono">incidents/</span> and <span class="mono">crosswalk/pif_rules.csv</span>.</div></footer>
</body>
</html>
"""


def main(argv: Sequence[str]) -> int:
    text = render(Ontology.load())
    if "--write" in argv:
        with open(OUTPUT, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
