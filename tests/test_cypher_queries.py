from __future__ import annotations

from sociomemory.graph import cypher as Q


def test_static_cypher_queries_do_not_emit_escaped_map_braces():
    queries = [
        value
        for name, value in vars(Q).items()
        if name.isupper() and isinstance(value, str)
    ]

    assert all("{{" not in query and "}}" not in query for query in queries)


def test_static_cypher_queries_avoid_direct_relationship_weight_reads():
    queries = [
        value
        for name, value in vars(Q).items()
        if name.isupper() and isinstance(value, str)
    ]

    assert all(".weight" not in query for query in queries)


def test_merge_node_uses_valid_neo4j_property_map():
    assert "MERGE (n:SocioNode {id: $id, child_id: $child_id})" in Q.MERGE_NODE


def test_builder_queries_preserve_cypher_maps_without_double_braces():
    traverse = Q.build_traverse_with_types(["LIVES_IN"], max_depth=2)
    temporal = Q.build_event_date_query("Visit")

    assert "{{" not in traverse and "}}" not in traverse
    assert "MATCH path = (start:SocioNode {id: $start_id})" in traverse
    assert "{{" not in temporal and "}}" not in temporal
    assert "MATCH (n:SocioNode {child_id: $child_id})" in temporal
    assert "AND n.node_type = 'Visit'" in temporal
    assert ".weight" not in traverse
