"""A dependency-free parser for the subset of Turtle 1.1 used by this repository.

Why this exists
---------------
The ontology in ``ontology/ehs-hfo.ttl`` is meant to be machine-readable, and a
file nothing reads is documentation with angle brackets. ``rdflib`` is the
obvious tool, but this repository is constrained to the standard library plus
pandas and numpy, so the parser is here.

What it supports
----------------
``@prefix`` / ``@base`` and their SPARQL-style ``PREFIX`` / ``BASE`` spellings;
IRI references; prefixed names; blank node labels, anonymous blank nodes and
blank-node property lists; RDF collections; the ``a`` keyword; predicate-object
lists (``;``) and object lists (``,``); string literals in single, double and
triple-quoted forms with language tags and datatype IRIs; integer, decimal,
double and boolean literals; and ``#`` comments.

What it does not support
------------------------
Escapes in prefixed local names (``\\%`` and ``\\-`` forms), Unicode escapes
beyond ``\\uXXXX`` and ``\\UXXXXXXXX``, and any form of RDF-star. It performs no
entailment: this is a parser, not a reasoner. Nothing here checks that the
document is valid OWL 2 DL.

The parser is strict about what it does support. A syntax error raises
:class:`TurtleSyntaxError` with a line and column, which is the behaviour the
test suite depends on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

__all__ = [
    "WELL_KNOWN_PREFIXES",
    "IRI",
    "BNode",
    "Literal",
    "Term",
    "Triple",
    "Graph",
    "TurtleSyntaxError",
    "parse",
    "parse_file",
]


class TurtleSyntaxError(ValueError):
    """Raised when the document is not in the supported Turtle subset."""

    def __init__(self, message: str, line: int, col: int) -> None:
        super().__init__(f"{message} (line {line}, column {col})")
        self.line = line
        self.col = col


# --------------------------------------------------------------------------- #
# Terms
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class IRI:
    """An absolute IRI."""

    value: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"<{self.value}>"


@dataclass(frozen=True)
class BNode:
    """A blank node, identified by a label that is local to one parse."""

    value: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"_:{self.value}"


@dataclass(frozen=True)
class Literal:
    """An RDF literal.

    Exactly one of ``lang`` and ``datatype`` may be set, per the RDF 1.1 model.
    A plain string literal has ``datatype`` ``xsd:string`` implicitly; this
    parser leaves it as ``None`` rather than materialising it.
    """

    value: str
    lang: Optional[str] = None
    datatype: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        if self.lang:
            return f'"{self.value}"@{self.lang}'
        if self.datatype:
            return f'"{self.value}"^^<{self.datatype}>'
        return f'"{self.value}"'


Term = object  # IRI | BNode | Literal; a union alias kept loose for 3.9.
Triple = Tuple[object, IRI, object]


# --------------------------------------------------------------------------- #
# Tokeniser
# --------------------------------------------------------------------------- #

_WS = " \t\r\n"

# PN_CHARS_BASE is restricted here to ASCII letters plus the common Latin-1
# range. The ontology in this repository is ASCII, so the restriction costs
# nothing and keeps the pattern legible.
_PN_START = re.compile(r"[A-Za-zÀ-˿]")
_PN_CHAR = re.compile(r"[A-Za-z0-9_À-˿̀-ͯ\-]")
_ECHAR = {
    "t": "\t",
    "b": "\b",
    "n": "\n",
    "r": "\r",
    "f": "\f",
    '"': '"',
    "'": "'",
    "\\": "\\",
}


@dataclass(frozen=True)
class _Token:
    kind: str
    value: object
    line: int
    col: int


class _Lexer:
    """Character scanner producing the token stream the parser consumes."""

    def __init__(self, text: str) -> None:
        self._text = text
        self._i = 0
        self._line = 1
        self._col = 1

    # -- low-level helpers -------------------------------------------------- #

    def _peek(self, offset: int = 0) -> str:
        j = self._i + offset
        return self._text[j] if j < len(self._text) else ""

    def _advance(self, n: int = 1) -> str:
        out = self._text[self._i : self._i + n]
        for ch in out:
            if ch == "\n":
                self._line += 1
                self._col = 1
            else:
                self._col += 1
        self._i += n
        return out

    def _error(self, message: str) -> TurtleSyntaxError:
        return TurtleSyntaxError(message, self._line, self._col)

    def _skip_ignorable(self) -> None:
        while self._i < len(self._text):
            ch = self._peek()
            if ch in _WS:
                self._advance()
            elif ch == "#":
                while self._i < len(self._text) and self._peek() != "\n":
                    self._advance()
            else:
                return

    # -- token producers ---------------------------------------------------- #

    def tokens(self) -> Iterator[_Token]:
        """Yield tokens until the input is exhausted."""
        while True:
            self._skip_ignorable()
            if self._i >= len(self._text):
                return
            line, col = self._line, self._col
            ch = self._peek()

            if ch in ".;,[]()":
                self._advance()
                yield _Token("PUNCT", ch, line, col)
            elif ch == "<":
                yield _Token("IRIREF", self._read_iriref(), line, col)
            elif ch == "@":
                yield _Token("DIRECTIVE", self._read_at_word(), line, col)
            elif ch == "^" and self._peek(1) == "^":
                self._advance(2)
                yield _Token("CARET", "^^", line, col)
            elif ch in "\"'":
                yield _Token("STRING", self._read_string(), line, col)
            elif ch == "_" and self._peek(1) == ":":
                self._advance(2)
                yield _Token("BNODE", self._read_pn_local(), line, col)
            elif ch.isdigit() or (ch in "+-" and self._peek(1).isdigit()) or (
                ch == "." and self._peek(1).isdigit()
            ):
                yield _Token("NUMBER", self._read_number(), line, col)
            elif _PN_START.match(ch) or ch == ":":
                yield self._read_name_token(line, col)
            else:
                raise self._error(f"unexpected character {ch!r}")

    def _read_iriref(self) -> str:
        self._advance()  # consume '<'
        out: List[str] = []
        while True:
            if self._i >= len(self._text):
                raise self._error("unterminated IRI reference")
            ch = self._advance()
            if ch == ">":
                return "".join(out)
            if ch == "\\":
                out.append(self._read_unicode_escape())
            elif ch in "<\"{}|^`" or ord(ch) <= 0x20:
                raise self._error(f"illegal character {ch!r} in IRI reference")
            else:
                out.append(ch)

    def _read_unicode_escape(self) -> str:
        marker = self._advance()
        width = {"u": 4, "U": 8}.get(marker)
        if width is None:
            raise self._error(f"unsupported escape \\{marker}")
        digits = self._advance(width)
        if len(digits) != width or any(d not in "0123456789abcdefABCDEF" for d in digits):
            raise self._error("malformed unicode escape")
        return chr(int(digits, 16))

    def _read_at_word(self) -> str:
        self._advance()  # consume '@'
        out: List[str] = []
        while self._peek() and (self._peek().isalnum() or self._peek() == "-"):
            out.append(self._advance())
        if not out:
            raise self._error("empty @ directive or language tag")
        return "".join(out)

    def _read_string(self) -> str:
        quote = self._peek()
        triple = self._text[self._i : self._i + 3] == quote * 3
        delim = quote * 3 if triple else quote
        self._advance(len(delim))
        out: List[str] = []
        while True:
            if self._i >= len(self._text):
                raise self._error("unterminated string literal")
            if self._text[self._i : self._i + len(delim)] == delim:
                self._advance(len(delim))
                return "".join(out)
            ch = self._advance()
            if ch == "\\":
                nxt = self._peek()
                if nxt in _ECHAR:
                    self._advance()
                    out.append(_ECHAR[nxt])
                else:
                    out.append(self._read_unicode_escape())
            elif ch == "\n" and not triple:
                raise self._error("newline in single-quoted string literal")
            else:
                out.append(ch)

    def _read_number(self) -> Tuple[str, str]:
        start = self._i
        if self._peek() in "+-":
            self._advance()
        seen_dot = False
        seen_exp = False
        while self._peek():
            ch = self._peek()
            if ch.isdigit():
                self._advance()
            elif ch == "." and not seen_dot and not seen_exp and self._peek(1).isdigit():
                seen_dot = True
                self._advance()
            elif ch in "eE" and not seen_exp:
                seen_exp = True
                self._advance()
                if self._peek() in "+-":
                    self._advance()
            else:
                break
        text = self._text[start : self._i]
        if seen_exp:
            return text, "http://www.w3.org/2001/XMLSchema#double"
        if seen_dot:
            return text, "http://www.w3.org/2001/XMLSchema#decimal"
        return text, "http://www.w3.org/2001/XMLSchema#integer"

    def _read_pn_local(self) -> str:
        out: List[str] = []
        while self._peek() and (_PN_CHAR.match(self._peek()) or self._peek() == "."):
            # A trailing '.' terminates a statement rather than belonging to the
            # name, so only accept it when another name character follows.
            if self._peek() == "." and not (
                self._peek(1) and _PN_CHAR.match(self._peek(1))
            ):
                break
            out.append(self._advance())
        if not out:
            raise self._error("empty local name")
        return "".join(out)

    def _read_name_token(self, line: int, col: int) -> _Token:
        prefix_chars: List[str] = []
        while self._peek() and _PN_CHAR.match(self._peek()):
            prefix_chars.append(self._advance())
        prefix = "".join(prefix_chars)
        if self._peek() == ":":
            self._advance()
            local = ""
            if self._peek() and (_PN_CHAR.match(self._peek()) or self._peek() == "%"):
                local = self._read_pn_local()
            return _Token("PNAME", (prefix, local), line, col)
        if prefix in ("a", "true", "false"):
            return _Token("KEYWORD", prefix, line, col)
        if prefix.upper() in ("PREFIX", "BASE"):
            return _Token("SPARQL_DIRECTIVE", prefix.upper(), line, col)
        raise TurtleSyntaxError(f"bare word {prefix!r} is not valid here", line, col)


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #

_RDF = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
_XSD_BOOLEAN = "http://www.w3.org/2001/XMLSchema#boolean"


class _Parser:
    """Recursive-descent parser over the token stream."""

    def __init__(self, text: str, base: str = "") -> None:
        self._tokens: List[_Token] = list(_Lexer(text).tokens())
        self._pos = 0
        self._base = base
        self.prefixes: Dict[str, str] = {}
        self.triples: List[Triple] = []
        self._bnode_counter = 0

    # -- token helpers ------------------------------------------------------ #

    def _peek(self, offset: int = 0) -> Optional[_Token]:
        j = self._pos + offset
        return self._tokens[j] if j < len(self._tokens) else None

    def _next(self) -> _Token:
        tok = self._peek()
        if tok is None:
            last = self._tokens[-1] if self._tokens else None
            line = last.line if last else 1
            col = last.col if last else 1
            raise TurtleSyntaxError("unexpected end of document", line, col)
        self._pos += 1
        return tok

    def _expect_punct(self, ch: str) -> _Token:
        tok = self._next()
        if tok.kind != "PUNCT" or tok.value != ch:
            raise TurtleSyntaxError(
                f"expected {ch!r} but found {tok.value!r}", tok.line, tok.col
            )
        return tok

    def _at_punct(self, ch: str) -> bool:
        tok = self._peek()
        return tok is not None and tok.kind == "PUNCT" and tok.value == ch

    def _fresh_bnode(self) -> BNode:
        self._bnode_counter += 1
        return BNode(f"b{self._bnode_counter}")

    # -- entry point -------------------------------------------------------- #

    def parse(self) -> None:
        while self._peek() is not None:
            tok = self._peek()
            assert tok is not None
            if tok.kind == "DIRECTIVE":
                self._parse_at_directive()
            elif tok.kind == "SPARQL_DIRECTIVE":
                self._parse_sparql_directive()
            else:
                self._parse_triples()

    def _parse_at_directive(self) -> None:
        tok = self._next()
        word = str(tok.value).lower()
        if word == "prefix":
            name_tok = self._next()
            if name_tok.kind != "PNAME" or name_tok.value[1] != "":
                raise TurtleSyntaxError(
                    "@prefix requires a prefix label followed by ':'",
                    name_tok.line,
                    name_tok.col,
                )
            iri_tok = self._next()
            if iri_tok.kind != "IRIREF":
                raise TurtleSyntaxError(
                    "@prefix requires an IRI reference", iri_tok.line, iri_tok.col
                )
            self.prefixes[name_tok.value[0]] = self._resolve(str(iri_tok.value))
            self._expect_punct(".")
        elif word == "base":
            iri_tok = self._next()
            if iri_tok.kind != "IRIREF":
                raise TurtleSyntaxError(
                    "@base requires an IRI reference", iri_tok.line, iri_tok.col
                )
            self._base = self._resolve(str(iri_tok.value))
            self._expect_punct(".")
        else:
            raise TurtleSyntaxError(f"unknown directive @{word}", tok.line, tok.col)

    def _parse_sparql_directive(self) -> None:
        tok = self._next()
        if tok.value == "PREFIX":
            name_tok = self._next()
            if name_tok.kind != "PNAME" or name_tok.value[1] != "":
                raise TurtleSyntaxError(
                    "PREFIX requires a prefix label", name_tok.line, name_tok.col
                )
            iri_tok = self._next()
            if iri_tok.kind != "IRIREF":
                raise TurtleSyntaxError(
                    "PREFIX requires an IRI reference", iri_tok.line, iri_tok.col
                )
            self.prefixes[name_tok.value[0]] = self._resolve(str(iri_tok.value))
        else:
            iri_tok = self._next()
            if iri_tok.kind != "IRIREF":
                raise TurtleSyntaxError(
                    "BASE requires an IRI reference", iri_tok.line, iri_tok.col
                )
            self._base = self._resolve(str(iri_tok.value))

    def _resolve(self, value: str) -> str:
        """Resolve an IRI against the current base.

        Only the cases this repository needs are handled: absolute IRIs pass
        through, and a relative reference is appended to the base. Full RFC 3986
        resolution is deliberately not implemented.
        """
        if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]*:", value):
            return value
        return self._base + value

    # -- triples ------------------------------------------------------------ #

    def _parse_triples(self) -> None:
        if self._at_punct("["):
            subject = self._parse_blank_node_property_list()
            if self._at_punct("."):
                self._expect_punct(".")
                return
        elif self._at_punct("("):
            subject = self._parse_collection()
        else:
            subject = self._parse_iri_or_bnode()
        self._parse_predicate_object_list(subject)
        self._expect_punct(".")

    def _parse_predicate_object_list(self, subject: object) -> None:
        while True:
            predicate = self._parse_predicate()
            self._parse_object_list(subject, predicate)
            if self._at_punct(";"):
                while self._at_punct(";"):
                    self._expect_punct(";")
                tok = self._peek()
                if tok is None or (tok.kind == "PUNCT" and tok.value in ".]"):
                    return
                continue
            return

    def _parse_object_list(self, subject: object, predicate: IRI) -> None:
        while True:
            obj = self._parse_object()
            self.triples.append((subject, predicate, obj))
            if self._at_punct(","):
                self._expect_punct(",")
                continue
            return

    def _parse_predicate(self) -> IRI:
        tok = self._peek()
        if tok is not None and tok.kind == "KEYWORD" and tok.value == "a":
            self._next()
            return IRI(_RDF + "type")
        term = self._parse_iri_or_bnode()
        if not isinstance(term, IRI):
            raise TurtleSyntaxError(
                "a blank node cannot be a predicate", tok.line if tok else 1, tok.col if tok else 1
            )
        return term

    def _parse_object(self) -> object:
        tok = self._peek()
        if tok is None:
            raise TurtleSyntaxError("unexpected end of document", 1, 1)
        if tok.kind == "PUNCT" and tok.value == "[":
            return self._parse_blank_node_property_list()
        if tok.kind == "PUNCT" and tok.value == "(":
            return self._parse_collection()
        if tok.kind == "STRING":
            return self._parse_string_literal()
        if tok.kind == "NUMBER":
            self._next()
            text, datatype = tok.value  # type: ignore[misc]
            return Literal(text, datatype=datatype)
        if tok.kind == "KEYWORD" and tok.value in ("true", "false"):
            self._next()
            return Literal(str(tok.value), datatype=_XSD_BOOLEAN)
        return self._parse_iri_or_bnode()

    def _parse_string_literal(self) -> Literal:
        tok = self._next()
        text = str(tok.value)
        nxt = self._peek()
        if nxt is not None and nxt.kind == "DIRECTIVE":
            self._next()
            return Literal(text, lang=str(nxt.value))
        if nxt is not None and nxt.kind == "CARET":
            self._next()
            dt = self._parse_iri_or_bnode()
            if not isinstance(dt, IRI):
                raise TurtleSyntaxError("datatype must be an IRI", nxt.line, nxt.col)
            return Literal(text, datatype=dt.value)
        return Literal(text)

    def _parse_iri_or_bnode(self) -> object:
        tok = self._next()
        if tok.kind == "IRIREF":
            return IRI(self._resolve(str(tok.value)))
        if tok.kind == "PNAME":
            prefix, local = tok.value  # type: ignore[misc]
            if prefix not in self.prefixes:
                raise TurtleSyntaxError(
                    f"undeclared prefix {prefix!r}", tok.line, tok.col
                )
            return IRI(self.prefixes[prefix] + local)
        if tok.kind == "BNODE":
            return BNode(f"label:{tok.value}")
        raise TurtleSyntaxError(
            f"expected an IRI or blank node but found {tok.value!r}", tok.line, tok.col
        )

    def _parse_blank_node_property_list(self) -> BNode:
        self._expect_punct("[")
        node = self._fresh_bnode()
        if not self._at_punct("]"):
            self._parse_predicate_object_list(node)
        self._expect_punct("]")
        return node

    def _parse_collection(self) -> object:
        self._expect_punct("(")
        items: List[object] = []
        while not self._at_punct(")"):
            items.append(self._parse_object())
        self._expect_punct(")")
        if not items:
            return IRI(_RDF + "nil")
        head = self._fresh_bnode()
        current = head
        for index, item in enumerate(items):
            self.triples.append((current, IRI(_RDF + "first"), item))
            if index == len(items) - 1:
                self.triples.append((current, IRI(_RDF + "rest"), IRI(_RDF + "nil")))
            else:
                nxt = self._fresh_bnode()
                self.triples.append((current, IRI(_RDF + "rest"), nxt))
                current = nxt
        return head


# --------------------------------------------------------------------------- #
# Graph
# --------------------------------------------------------------------------- #


#: Namespaces assumed available to :meth:`Graph.expand` even when the document
#: does not declare them. Only well-known, fixed RDF namespaces belong here.
#:
#: This exists because the ``a`` keyword lets a document use ``rdf:type`` without
#: ever declaring the ``rdf`` prefix, and :meth:`Graph.instances_of` expands
#: ``rdf:type`` internally. Without a fallback, a perfectly valid Turtle file
#: would raise ``KeyError`` on lookup rather than on parse. A prefix the document
#: declares always wins over the fallback.
WELL_KNOWN_PREFIXES: Dict[str, str] = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


class Graph:
    """An in-memory set of triples with the few lookups this project needs."""

    def __init__(self, triples: Sequence[Triple], prefixes: Dict[str, str]) -> None:
        self.triples: List[Triple] = list(triples)
        self.prefixes: Dict[str, str] = dict(prefixes)
        self._by_subject: Dict[object, List[Triple]] = {}
        self._by_predicate: Dict[str, List[Triple]] = {}
        for triple in self.triples:
            self._by_subject.setdefault(triple[0], []).append(triple)
            self._by_predicate.setdefault(triple[1].value, []).append(triple)

    def __len__(self) -> int:
        return len(self.triples)

    # -- name handling ------------------------------------------------------ #

    def expand(self, curie: str) -> IRI:
        """Turn ``prefix:local`` into a full IRI.

        Prefixes declared by the document take precedence; the fixed namespaces
        in :data:`WELL_KNOWN_PREFIXES` are consulted only as a fallback, so a
        document that uses ``a`` without declaring ``rdf`` can still be queried.
        """
        if curie.startswith("<") and curie.endswith(">"):
            return IRI(curie[1:-1])
        if ":" not in curie:
            raise KeyError(f"{curie!r} is not a prefixed name")
        prefix, local = curie.split(":", 1)
        namespace = self.prefixes.get(prefix) or WELL_KNOWN_PREFIXES.get(prefix)
        if namespace is None:
            raise KeyError(f"undeclared prefix {prefix!r}")
        return IRI(namespace + local)

    def shorten(self, iri: IRI) -> str:
        """Return the shortest prefixed name for ``iri``, or the IRI in brackets."""
        best: Optional[str] = None
        for prefix, namespace in self.prefixes.items():
            if iri.value.startswith(namespace):
                candidate = f"{prefix}:{iri.value[len(namespace):]}"
                if best is None or len(candidate) < len(best):
                    best = candidate
        return best if best is not None else f"<{iri.value}>"

    # -- lookups ------------------------------------------------------------ #

    def objects(self, subject: object, predicate: str) -> List[object]:
        """All objects of ``subject predicate ?o``. ``predicate`` is a CURIE."""
        pred = self.expand(predicate).value
        return [t[2] for t in self._by_subject.get(subject, []) if t[1].value == pred]

    def value(self, subject: object, predicate: str) -> Optional[object]:
        """The single object of ``subject predicate ?o``, or ``None``.

        Raises if more than one object is present, because every use of this
        method in the project is over a functional property and a silent pick
        would hide a modelling error.
        """
        found = self.objects(subject, predicate)
        if not found:
            return None
        if len(found) > 1:
            raise ValueError(
                f"expected at most one {predicate} on {subject!r}, found {len(found)}"
            )
        return found[0]

    def subjects(self, predicate: str, obj: object) -> List[object]:
        """All subjects of ``?s predicate obj``."""
        pred = self.expand(predicate).value
        return [t[0] for t in self._by_predicate.get(pred, []) if t[2] == obj]

    def instances_of(self, class_curie: str) -> List[object]:
        """All subjects asserted to be ``rdf:type`` of the named class."""
        return self.subjects("rdf:type", self.expand(class_curie))

    def literal(self, subject: object, predicate: str) -> Optional[str]:
        """The lexical form of a single literal object, or ``None``."""
        found = self.value(subject, predicate)
        if found is None:
            return None
        if not isinstance(found, Literal):
            raise ValueError(f"{predicate} on {subject!r} is not a literal")
        return found.value

    def literals(self, subject: object, predicate: str) -> List[str]:
        """Lexical forms of all literal objects for the predicate."""
        return [o.value for o in self.objects(subject, predicate) if isinstance(o, Literal)]


def parse(text: str, base: str = "") -> Graph:
    """Parse Turtle source text into a :class:`Graph`."""
    parser = _Parser(text, base=base)
    parser.parse()
    return Graph(parser.triples, parser.prefixes)


def parse_file(path: str, base: str = "") -> Graph:
    """Parse a Turtle file from disk."""
    with open(path, "r", encoding="utf-8") as handle:
        return parse(handle.read(), base=base)
