"""Export the ontology in standard formats for tool interoperability.

Supports JSON-LD 1.1 and OWL/XML (W3C OWL 2 XML serialisation).
Both formats are deterministic (sorted keys and subjects).
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any, Dict

from .ontology import Ontology
from .turtle import Graph, IRI, BNode, Literal


# ========================================================================== #
# JSON-LD Export
# ========================================================================== #


def export_jsonld(ontology: Ontology) -> str:
    """Export the ontology as JSON-LD 1.1.

    Returns a JSON string with:
    - A @context mapping all known prefixes
    - One node per subject in the ontology
    - Typed literals preserved in their original form
    """
    graph = ontology.graph

    # Build @context from prefixes
    context: Dict[str, str] = {}
    for prefix, namespace in sorted(graph.prefixes.items()):
        context[prefix] = namespace

    # Collect all subjects and their triples, grouped by subject
    subjects_dict: Dict[str, Dict[str, Any]] = {}

    for triple in sorted(graph.triples, key=lambda t: (str(t[0]), t[1].value, str(t[2]))):
        subject_str = _term_to_jsonld(graph, triple[0])
        if isinstance(subject_str, dict) and "@id" in subject_str:
            subject_id = subject_str["@id"]
        else:
            subject_id = str(subject_str)

        predicate_str = graph.shorten(triple[1])
        obj = triple[2]

        if subject_id not in subjects_dict:
            subjects_dict[subject_id] = {"@id": subject_id}

        obj_value = _term_to_jsonld(graph, obj)

        # Handle multiple values for same predicate
        if predicate_str in subjects_dict[subject_id]:
            existing = subjects_dict[subject_id][predicate_str]
            if not isinstance(existing, list):
                subjects_dict[subject_id][predicate_str] = [existing]
            if obj_value not in subjects_dict[subject_id][predicate_str]:
                subjects_dict[subject_id][predicate_str].append(obj_value)
        else:
            subjects_dict[subject_id][predicate_str] = obj_value

    # Build the output document
    output: Dict[str, Any] = {
        "@context": context,
        "@graph": [subjects_dict[key] for key in sorted(subjects_dict.keys())]
    }

    return json.dumps(output, indent=2, ensure_ascii=False, sort_keys=False)


def _term_to_jsonld(graph: Graph, term: object) -> Any:
    """Convert a triple term (subject/object) to JSON-LD representation."""
    if isinstance(term, IRI):
        return {"@id": graph.shorten(term)}
    elif isinstance(term, BNode):
        return {"@id": term.value}
    elif isinstance(term, Literal):
        # Preserve type information for typed literals
        if term.datatype:
            return {
                "@value": term.value,
                "@type": graph.shorten(IRI(term.datatype))
            }
        elif term.lang:
            return {
                "@value": term.value,
                "@language": term.lang
            }
        else:
            return term.value
    else:
        return str(term)


# ========================================================================== #
# OWL/XML Export
# ========================================================================== #


def export_owlxml(ontology: Ontology) -> str:
    """Export the ontology as OWL/XML (W3C OWL 2 XML serialisation).

    Covers classes, object and data properties, individuals, annotations,
    and reified alignments. Output is deterministic (sorted).
    """
    graph = ontology.graph

    # Create root element
    root = ET.Element(
        "Ontology",
        {
            "xmlns": "http://www.w3.org/2002/07/owl#",
            "ontologyIRI": "https://priyatham9.github.io/ehs-human-factors-ontology/ehs-hfo"
        }
    )

    # Add prefix declarations
    for prefix, namespace in sorted(graph.prefixes.items()):
        ET.SubElement(root, "Prefix", {"name": prefix, "IRI": namespace})

    # Extract all classes from rdf:type assertions
    classes: set = set()
    properties: set = set()
    individuals: set = set()

    type_iri = graph.expand("rdf:type").value

    for triple in graph.triples:
        subj, pred, obj = triple

        if isinstance(pred, IRI) and pred.value == type_iri:
            if isinstance(subj, IRI):
                individuals.add(graph.shorten(subj))
            if isinstance(obj, IRI):
                obj_curie = graph.shorten(obj)
                # Filter to only real classes defined in the ontology
                if "ehs:" in obj_curie or "xw:" in obj_curie:
                    classes.add(obj_curie)

    # Find all property predicates used in the graph
    for triple in graph.triples:
        subj, pred, obj = triple
        if isinstance(pred, IRI):
            pred_curie = graph.shorten(pred)
            # Skip RDF/RDFS built-ins and type
            if not pred_curie.startswith("rdf:") and not pred_curie.startswith("rdfs:") and pred_curie != "a":
                if "ehs:" in pred_curie or "xw:" in pred_curie or "skos:" in pred_curie or "dcterms:" in pred_curie:
                    properties.add(pred_curie)

    # Export class declarations
    for class_curie in sorted(classes):
        ET.SubElement(root, "Class", {"IRI": class_curie})

    # Export property declarations
    for prop_curie in sorted(properties):
        # Determine if it's an object or data property
        is_obj_property = True  # Default to object property
        for triple in graph.triples:
            subj, pred, obj = triple
            if isinstance(pred, IRI) and graph.shorten(pred) == prop_curie:
                if isinstance(obj, Literal):
                    is_obj_property = False
                    break

        if is_obj_property:
            ET.SubElement(root, "ObjectProperty", {"IRI": prop_curie})
        else:
            ET.SubElement(root, "DatatypeProperty", {"IRI": prop_curie})

    # Export individuals with their assertions
    for individual_curie in sorted(individuals):
        individual_elem = ET.SubElement(root, "NamedIndividual", {"IRI": individual_curie})

        # Add all property assertions for this individual
        individual_iri = graph.expand(individual_curie)
        assertions: list = []

        for triple in graph.triples:
            subj, pred, obj = triple
            if subj != individual_iri:
                continue

            if isinstance(pred, IRI):
                pred_curie = graph.shorten(pred)
                if pred_curie == "rdf:type":
                    continue

                if isinstance(obj, IRI):
                    obj_curie = graph.shorten(obj)
                    assertions.append((pred_curie, "object", obj_curie))
                elif isinstance(obj, Literal):
                    assertions.append((pred_curie, "data", obj))

        # Add assertions sorted deterministically
        for pred_curie, obj_type, obj_val in sorted(assertions, key=lambda x: (x[0], x[1])):
            if obj_type == "object":
                fact_elem = ET.SubElement(individual_elem, "ObjectPropertyAssertion")
                ET.SubElement(fact_elem, "ObjectProperty", {"IRI": pred_curie})
                ET.SubElement(fact_elem, "NamedIndividual", {"IRI": obj_val})
            else:  # data
                fact_elem = ET.SubElement(individual_elem, "DataPropertyAssertion")
                ET.SubElement(fact_elem, "DataProperty", {"IRI": pred_curie})
                lit_elem = ET.SubElement(fact_elem, "Literal")
                if obj_val.datatype:
                    lit_elem.set("datatypeIRI", obj_val.datatype)
                if obj_val.lang:
                    lit_elem.set("{http://www.w3.org/XML/1998/namespace}lang", obj_val.lang)
                lit_elem.text = obj_val.value

    _indent(root)
    tree_str = ET.tostring(root, encoding="unicode", method="xml")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + tree_str


def _indent(elem: ET.Element, level: int = 0) -> None:
    """Pretty-print an XML element tree."""
    indent_str = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent_str + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent_str
        for child in elem:
            _indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent_str
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent_str


# ========================================================================== #
# Public API
# ========================================================================== #


def export(
    ontology: Ontology,
    format: str = "jsonld",
) -> str:
    """Export the ontology in the specified format.

    Args:
        ontology: The loaded ontology
        format: Export format - 'jsonld' or 'owlxml'

    Returns:
        The serialized ontology in the requested format

    Raises:
        ValueError: If the format is unknown
    """
    if format == "jsonld":
        return export_jsonld(ontology)
    elif format == "owlxml":
        return export_owlxml(ontology)
    else:
        raise ValueError(f"Unknown export format: {format}")
