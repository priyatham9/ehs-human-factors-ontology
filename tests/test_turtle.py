"""Tests for the hand-written Turtle parser.

The parser is the only thing standing between the ontology file and everything
downstream, and it has no external dependency to fall back on, so it is tested
directly rather than only through the ontology.
"""

from __future__ import annotations

import unittest

from tests import context  # noqa: F401  (path setup)

from ehs_hfo.turtle import IRI, Literal, TurtleSyntaxError, parse


class TestTurtleBasics(unittest.TestCase):
    """Core syntax: prefixes, triples, and the punctuation shorthands."""

    def test_prefixed_triple(self) -> None:
        graph = parse('@prefix ex: <http://example.org/> . ex:a ex:b ex:c .')
        self.assertEqual(len(graph), 1)
        subject, predicate, obj = graph.triples[0]
        self.assertEqual(subject, IRI("http://example.org/a"))
        self.assertEqual(predicate, IRI("http://example.org/b"))
        self.assertEqual(obj, IRI("http://example.org/c"))

    def test_predicate_object_list_and_object_list(self) -> None:
        graph = parse(
            '@prefix ex: <http://example.org/> .'
            ' ex:a ex:b ex:c , ex:d ; ex:e ex:f .'
        )
        self.assertEqual(len(graph), 3)

    def test_a_is_rdf_type(self) -> None:
        graph = parse('@prefix ex: <http://example.org/> . ex:a a ex:C .')
        self.assertEqual(
            graph.triples[0][1],
            IRI("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
        )

    def test_sparql_style_prefix_directive(self) -> None:
        graph = parse('PREFIX ex: <http://example.org/>\nex:a ex:b ex:c .')
        self.assertEqual(len(graph), 1)

    def test_comments_are_ignored(self) -> None:
        graph = parse(
            "# leading comment\n"
            "@prefix ex: <http://example.org/> .  # trailing\n"
            "ex:a ex:b ex:c .\n"
        )
        self.assertEqual(len(graph), 1)


class TestTurtleLiterals(unittest.TestCase):
    """Literal forms the ontology actually uses."""

    def _object(self, text: str) -> object:
        graph = parse('@prefix ex: <http://example.org/> . ex:a ex:b ' + text + ' .')
        return graph.triples[0][2]

    def test_plain_string(self) -> None:
        value = self._object('"hello"')
        assert isinstance(value, Literal)
        self.assertEqual(value.value, "hello")

    def test_language_tag(self) -> None:
        value = self._object('"hello"@en')
        assert isinstance(value, Literal)
        self.assertEqual(value.lang, "en")

    def test_triple_quoted_string_spans_lines(self) -> None:
        value = self._object('"""line one\nline two"""')
        assert isinstance(value, Literal)
        self.assertIn("\n", value.value)

    def test_escape_sequences(self) -> None:
        value = self._object('"a\\"b\\nc"')
        assert isinstance(value, Literal)
        self.assertEqual(value.value, 'a"b\nc')

    def test_integer_literal_is_typed(self) -> None:
        value = self._object("-1")
        assert isinstance(value, Literal)
        self.assertEqual(value.value, "-1")
        self.assertTrue(str(value.datatype).endswith("integer"))


class TestTurtleErrors(unittest.TestCase):
    """The parser must refuse malformed input rather than guess."""

    def test_unterminated_triple(self) -> None:
        with self.assertRaises(TurtleSyntaxError):
            parse('@prefix ex: <http://example.org/> . ex:a ex:b ex:c')

    def test_undefined_prefix(self) -> None:
        with self.assertRaises(TurtleSyntaxError):
            parse("nope:a nope:b nope:c .")

    def test_unterminated_string(self) -> None:
        with self.assertRaises(TurtleSyntaxError):
            parse('@prefix ex: <http://example.org/> . ex:a ex:b "oops .')

    def test_error_carries_position(self) -> None:
        with self.assertRaises(TurtleSyntaxError) as caught:
            parse("nope:a nope:b nope:c .")
        self.assertGreaterEqual(caught.exception.line, 1)


class TestGraphAccessors(unittest.TestCase):
    """The query surface the ontology loader relies on."""

    def setUp(self) -> None:
        self.graph = parse(
            "@prefix ex: <http://example.org/> .\n"
            '@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .\n'
            '@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n'
            'ex:a a ex:C ; rdfs:label "A"@en ; ex:p ex:x , ex:y .\n'
            'ex:b a ex:C ; rdfs:label "B"@en .\n'
        )

    def test_instances_of(self) -> None:
        self.assertEqual(len(self.graph.instances_of("ex:C")), 2)

    def test_literal_and_literals(self) -> None:
        node = self.graph.expand("ex:a")
        self.assertEqual(self.graph.literal(node, "rdfs:label"), "A")
        self.assertEqual(len(self.graph.objects(node, "ex:p")), 2)

    def test_shorten_round_trips_expand(self) -> None:
        self.assertEqual(self.graph.shorten(self.graph.expand("ex:a")), "ex:a")


class TestRealOntologyParses(unittest.TestCase):
    """The shipped ontology file must parse, and be non-trivial."""

    def test_ontology_file_parses(self) -> None:
        graph = context.ontology().graph
        self.assertGreater(len(graph), 500)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
