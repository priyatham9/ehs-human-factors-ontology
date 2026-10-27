"""Transparent rule-based suggester: incident narrative text to candidate PIFs.

No machine learning. Every suggestion names the rule that fired, the exact
words it matched, and the crosswalk alignment the rule is traced to.

Two rule sets:

``curated``
    ``crosswalk/pif_rules.csv``. Phrase rules written by hand. Each rule cites
    an external factor (``external_curie``) that the ontology aligns to the
    rule's PIF, so a reader can follow phrase -> PIF -> external framework
    factor -> citation. Written after the author had read the 25 CSB codings
    in ``incidents/``; see ``docs/suggester.html`` for what that means for
    the evaluation.
``baseline``
    Derived mechanically from the ontology's own wording: a stemmed word is a
    rule for a PIF when it appears in that PIF's label, verbatim label or
    aligned external labels and in no other PIF's. No tuning against incidents.

Suggestions are screening prompts for a human coder, not codings.
"""

from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

from .ontology import Ontology

RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "crosswalk",
    "pif_rules.csv",
)

_STOPWORDS = frozenset(
    "and the for with from that this other level nature task tasks work "
    "working conditions condition factors factor adequacy availability "
    "quality general time".split()
)


@dataclass(frozen=True)
class Rule:
    rule_id: str
    factor_curie: str
    phrase: str
    external_curie: str
    rationale: str
    pattern: "re.Pattern[str]"
    seen_in_set: bool = False


@dataclass(frozen=True)
class Hit:
    rule: Rule
    matched_text: str


def compile_phrase(phrase: str) -> "re.Pattern[str]":
    """Whole-word, case-insensitive match; a trailing ``*`` on a word matches any ending."""
    parts = []
    for word in phrase.split():
        body = re.escape(word.rstrip("*"))
        parts.append(body + (r"\w*" if word.endswith("*") else r"(?!\w)"))
    return re.compile(r"(?<!\w)" + r"\s+".join(parts), re.IGNORECASE)


def load_curated(path: str = RULES_PATH) -> List[Rule]:
    with open(path, encoding="utf-8", newline="") as handle:
        return [
            Rule(r["rule_id"], r["factor_curie"], r["phrase"], r["external_curie"],
                 r["rationale"], compile_phrase(r["phrase"]),
                 r.get("phrase_seen_in_incident_set") == "yes")
            for r in csv.DictReader(handle)
        ]


def _stem(word: str) -> str:
    return word[:5] if len(word) >= 6 else word


def build_baseline(ontology: Ontology) -> List[Rule]:
    """Words unique to one PIF's label/aligned-label vocabulary, stemmed to 5 letters."""
    vocab: Dict[str, Dict[str, str]] = {}
    for factor in ontology.factors.values():
        texts = [(factor.label, "")]
        if factor.verbatim_label:
            texts.append((factor.verbatim_label, ""))
        for al in ontology.alignments.values():
            if al.local_factor == factor.curie:
                ext = ontology.external_factors[al.external_factor]
                texts.append((ext.label, ext.curie))
        words: Dict[str, str] = {}
        for text, ext_curie in texts:
            for w in re.findall(r"[a-z]+", text.lower()):
                if len(w) >= 4 and w not in _STOPWORDS:
                    words.setdefault(_stem(w), ext_curie)
        vocab[factor.curie] = words
    owners: Dict[str, List[str]] = {}
    for curie, words in vocab.items():
        for stem in words:
            owners.setdefault(stem, []).append(curie)
    rules: List[Rule] = []
    n = 0
    for curie in sorted(vocab):
        for stem in sorted(vocab[curie]):
            if len(owners[stem]) == 1:
                n += 1
                rules.append(Rule(
                    f"B{n:03d}", curie, stem + "*", vocab[curie][stem],
                    "word from PIF/aligned-factor label", compile_phrase(stem + "*")))
    return rules


def suggest(text: str, rules: Sequence[Rule]) -> Dict[str, List[Hit]]:
    """Map each suggested PIF curie to the rule hits that support it."""
    out: Dict[str, List[Hit]] = {}
    for rule in rules:
        for m in rule.pattern.finditer(text):
            out.setdefault(rule.factor_curie, []).append(Hit(rule, m.group(0)))
    return out


def render(suggestions: Dict[str, List[Hit]], ontology: Ontology) -> str:
    if not suggestions:
        return "No rule fired. This is not evidence that no PIF applies.\n"
    lines: List[str] = []
    for curie, hits in sorted(suggestions.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        lines.append(f"{ontology.factor(curie).label}  ({curie})  {len(hits)} hit(s)")
        for h in hits:
            ext = ontology.external_factors.get(h.rule.external_curie)
            via = f"{ext.label} [{ext.framework}]" if ext else "PIF wording"
            lines.append(f'    {h.rule.rule_id}  "{h.matched_text}"  <- rule "{h.rule.phrase}"  via {via}')
    lines.append("")
    lines.append("Screening prompts for a human coder; not codings. Absence of a suggestion is not evidence of absence.")
    return "\n".join(lines) + "\n"


def to_json(suggestions: Dict[str, List[Hit]]) -> List[dict]:
    return [
        {"factor": curie,
         "hits": [{"rule_id": h.rule.rule_id, "rule_phrase": h.rule.phrase,
                   "matched_text": h.matched_text, "crosswalk_source": h.rule.external_curie}
                  for h in hits]}
        for curie, hits in sorted(suggestions.items())
    ]


def read_text(path: Optional[str], stdin) -> str:
    if path in (None, "-"):
        return stdin.read()
    with open(path, encoding="utf-8") as handle:
        return handle.read()


__all__: Iterable[str] = [
    "Rule", "Hit", "load_curated", "build_baseline", "suggest", "render", "to_json",
    "compile_phrase", "read_text", "RULES_PATH",
]
