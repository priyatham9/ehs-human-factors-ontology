"""Tests for the Datalog evaluator.

These are about the evaluator's semantics, not about human factors. They use
small hand-built programs so a failure points at the engine rather than at the
rule base. The properties checked are the ones the auditability claim rests on:
evaluation reaches a unique fixpoint, negation is stratified, and every derived
fact carries a justification that bottoms out in supplied input.
"""

from __future__ import annotations

import unittest

from tests import context  # noqa: F401  (path setup)

from ehs_hfo.engine import Program, StratificationError
from ehs_hfo.facts import Fact, Pattern, Rule, RuleError, Var


def _p(predicate: str, *args: object) -> Pattern:
    """Positive pattern; strings are constants, Var instances are variables."""
    return Pattern(predicate, tuple(args))


def _not(predicate: str, *args: object) -> Pattern:
    """Negative body literal."""
    return Pattern(predicate, tuple(args), negated=True)


class TestRuleSafety(unittest.TestCase):
    """A rule must be range-restricted or it cannot be grounded."""

    def test_unbound_head_variable_is_rejected(self) -> None:
        with self.assertRaises(RuleError):
            Rule(
                rule_id="R-bad-head",
                description="head variable never bound in the body",
                body=(_p("a", Var("X")),),
                head=_p("b", Var("Y")),
                source_refs=("x",),
            )

    def test_variable_only_in_negative_literal_is_rejected(self) -> None:
        with self.assertRaises(RuleError):
            Rule(
                rule_id="R-bad-neg",
                description="Y appears only under negation",
                body=(_p("a", Var("X")), _not("b", Var("Y"))),
                head=_p("c", Var("X")),
                source_refs=("x",),
            )

    def test_literature_rule_must_cite(self) -> None:
        with self.assertRaises(RuleError):
            Rule(
                rule_id="R-uncited",
                description="claims literature basis with no source",
                body=(_p("a", Var("X")),),
                head=_p("b", Var("X")),
                basis="literature",
            )

    def test_convention_rule_may_omit_a_source(self) -> None:
        rule = Rule(
            rule_id="R-convention",
            description="threshold chosen by the author",
            body=(_p("a", Var("X")),),
            head=_p("b", Var("X")),
            basis="convention",
        )
        self.assertEqual(rule.basis, "convention")

    def test_unknown_basis_is_rejected(self) -> None:
        with self.assertRaises(RuleError):
            Rule(
                rule_id="R-basis",
                description="",
                body=(_p("a", Var("X")),),
                head=_p("b", Var("X")),
                basis="vibes",
            )


class TestEvaluation(unittest.TestCase):
    """Fixpoint behaviour on small programs."""

    def test_transitive_closure(self) -> None:
        program = Program(
            [
                Rule(
                    rule_id="R-base",
                    description="an edge is a path",
                    body=(_p("edge", Var("X"), Var("Y")),),
                    head=_p("path", Var("X"), Var("Y")),
                    basis="convention",
                ),
                Rule(
                    rule_id="R-step",
                    description="a path extended by an edge is a path",
                    body=(
                        _p("path", Var("X"), Var("Y")),
                        _p("edge", Var("Y"), Var("Z")),
                    ),
                    head=_p("path", Var("X"), Var("Z")),
                    basis="convention",
                ),
            ]
        )
        result = program.evaluate(
            [
                Fact("edge", ("a", "b")),
                Fact("edge", ("b", "c")),
                Fact("edge", ("c", "d")),
            ]
        )
        self.assertTrue(result.holds("path", "a", "d"))
        self.assertFalse(result.holds("path", "d", "a"))

    def test_recursion_terminates(self) -> None:
        """A cycle in the data must not stop evaluation reaching a fixpoint."""
        program = Program(
            [
                Rule(
                    rule_id="R-base",
                    description="",
                    body=(_p("edge", Var("X"), Var("Y")),),
                    head=_p("path", Var("X"), Var("Y")),
                    basis="convention",
                ),
                Rule(
                    rule_id="R-step",
                    description="",
                    body=(
                        _p("path", Var("X"), Var("Y")),
                        _p("edge", Var("Y"), Var("Z")),
                    ),
                    head=_p("path", Var("X"), Var("Z")),
                    basis="convention",
                ),
            ]
        )
        result = program.evaluate(
            [Fact("edge", ("a", "b")), Fact("edge", ("b", "a"))]
        )
        self.assertTrue(result.holds("path", "a", "a"))

    def test_evaluation_is_order_independent(self) -> None:
        """The perfect model does not depend on the order facts arrive in."""
        program = context.program()
        ontology = context.ontology()
        from ehs_hfo.facts import Scenario
        from ehs_hfo.rules import base_facts

        scenario = Scenario(
            scenario_id="order-test",
            factor_levels={
                "ehs:Training": "ehs:LevelDegraded",
                "ehs:ScenarioFamiliarity": "ehs:LevelSeverelyDegraded",
            },
        )
        facts = base_facts(scenario, ontology)
        forward = program.evaluate(facts)
        backward = program.evaluate(list(reversed(facts)))
        self.assertEqual(forward.facts, backward.facts)


class TestNegation(unittest.TestCase):
    """Negation as failure, and the stratification that makes it well-defined."""

    def test_negation_as_failure(self) -> None:
        program = Program(
            [
                Rule(
                    rule_id="R-neg",
                    description="",
                    body=(_p("thing", Var("X")), _not("flagged", Var("X"))),
                    head=_p("clean", Var("X")),
                    basis="convention",
                )
            ]
        )
        result = program.evaluate(
            [
                Fact("thing", ("a",)),
                Fact("thing", ("b",)),
                Fact("flagged", ("b",)),
            ]
        )
        self.assertTrue(result.holds("clean", "a"))
        self.assertFalse(result.holds("clean", "b"))

    def test_negation_inside_a_cycle_is_refused(self) -> None:
        """An unstratifiable program must fail loudly, not pick an answer."""
        with self.assertRaises(StratificationError):
            Program(
                [
                    Rule(
                        rule_id="R-p",
                        description="",
                        body=(_p("d", Var("X")), _not("q", Var("X"))),
                        head=_p("p", Var("X")),
                        basis="convention",
                    ),
                    Rule(
                        rule_id="R-q",
                        description="",
                        body=(_p("d", Var("X")), _not("p", Var("X"))),
                        head=_p("q", Var("X")),
                        basis="convention",
                    ),
                ]
            )

    def test_duplicate_rule_id_is_refused(self) -> None:
        with self.assertRaises(RuleError):
            Program(
                [
                    Rule(
                        rule_id="R-dup",
                        description="",
                        body=(_p("a", Var("X")),),
                        head=_p("b", Var("X")),
                        basis="convention",
                    ),
                    Rule(
                        rule_id="R-dup",
                        description="",
                        body=(_p("a", Var("X")),),
                        head=_p("c", Var("X")),
                        basis="convention",
                    ),
                ]
            )


class TestBuiltins(unittest.TestCase):
    """The two guards the rule base uses."""

    def _program(self, guard: Pattern) -> Program:
        return Program(
            [
                Rule(
                    rule_id="R-guard",
                    description="",
                    body=(_p("d", Var("X")), _p("d", Var("Y")), guard),
                    head=_p("pair", Var("X"), Var("Y")),
                    basis="convention",
                )
            ]
        )

    def test_neq_excludes_identical_bindings(self) -> None:
        program = self._program(
            Pattern("neq", (Var("X"), Var("Y")), builtin=True)
        )
        result = program.evaluate([Fact("d", ("a",)), Fact("d", ("b",))])
        self.assertFalse(result.holds("pair", "a", "a"))
        self.assertTrue(result.holds("pair", "a", "b"))
        self.assertTrue(result.holds("pair", "b", "a"))

    def test_lt_fires_once_per_unordered_pair(self) -> None:
        program = self._program(
            Pattern("lt", (Var("X"), Var("Y")), builtin=True)
        )
        result = program.evaluate([Fact("d", ("a",)), Fact("d", ("b",))])
        self.assertTrue(result.holds("pair", "a", "b"))
        self.assertFalse(result.holds("pair", "b", "a"))


class TestProvenance(unittest.TestCase):
    """The derivation trace is the point of the whole exercise."""

    def setUp(self) -> None:
        self.program = Program(
            [
                Rule(
                    rule_id="R-1",
                    description="b follows from a",
                    body=(_p("a", Var("X")),),
                    head=_p("b", Var("X")),
                    source_refs=("srcA",),
                ),
                Rule(
                    rule_id="R-2",
                    description="c follows from b",
                    body=(_p("b", Var("X")),),
                    head=_p("c", Var("X")),
                    source_refs=("srcB",),
                ),
            ]
        )
        self.result = self.program.evaluate([Fact("a", ("x",))])

    def test_every_derived_fact_has_a_justification(self) -> None:
        for fact in self.result.derived_facts():
            with self.subTest(fact=str(fact)):
                justification = self.result.justifications[fact]
                self.assertFalse(justification.is_base)
                self.assertTrue(justification.derivations)

    def test_base_facts_are_marked_base(self) -> None:
        base = self.result.justifications[Fact("a", ("x",))]
        self.assertTrue(base.is_base)

    def test_trace_names_the_rule_and_reaches_the_input(self) -> None:
        lines = self.result.explain(Fact("c", ("x",)))
        joined = "\n".join(lines)
        self.assertIn("R-2", joined)
        self.assertIn("R-1", joined)
        self.assertIn("given", joined)

    def test_trace_carries_the_citation(self) -> None:
        joined = "\n".join(self.result.explain(Fact("c", ("x",))))
        self.assertIn("srcB", joined)

    def test_every_derived_fact_traces_back_to_base_facts(self) -> None:
        """No conclusion may rest on anything but supplied input and rules."""
        base = set(self.result.base_facts())
        for fact in self.result.derived_facts():
            with self.subTest(fact=str(fact)):
                frontier = [fact]
                seen = set()
                reached = set()
                while frontier:
                    current = frontier.pop()
                    if current in seen:
                        continue
                    seen.add(current)
                    justification = self.result.justifications[current]
                    if justification.is_base:
                        reached.add(current)
                        continue
                    for derivation in justification.derivations:
                        frontier.extend(derivation.support)
                self.assertTrue(reached.issubset(base))
                self.assertTrue(reached, "trace reached no input fact")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
