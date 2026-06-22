from __future__ import annotations

from sociomemory.graph.edges import EdgeType

MERGE_NODE = """
MERGE (n:SocioNode {id: $id, child_id: $child_id})
ON CREATE SET n += $props, n.created_at = $now, n.node_type = $node_type
ON MATCH SET n += $props, n.updated_at = $now, n.node_type = $node_type
RETURN n
"""

GET_NODE_BY_ID = """
MATCH (n:SocioNode {id: $id})
RETURN n
"""

GET_NODES_BY_TYPE = """
MATCH (n:SocioNode {child_id: $child_id, node_type: $node_type})
RETURN n
ORDER BY n.created_at DESC
"""

GET_ALL_NODES = """
MATCH (n:SocioNode {child_id: $child_id})
RETURN n
"""

DELETE_NODE = """
MATCH (n:SocioNode {id: $id})
DETACH DELETE n
"""

ERASE_CHILD = """
MATCH (n:SocioNode {child_id: $child_id})
DETACH DELETE n
"""

NODE_COUNT = """
MATCH (n:SocioNode {child_id: $child_id})
RETURN count(n) AS count
"""

MERGE_EDGE = """
MATCH (a:SocioNode {id: $source_id})
MATCH (b:SocioNode {id: $target_id})
MERGE (a)-[r:{edge_type}]->(b)
ON CREATE SET r += $props, r.created_at = $now
ON MATCH SET r += {
               weight: CASE
                 WHEN coalesce(properties(r)['weight'], 0.0) < $weight THEN $weight
                 ELSE properties(r)['weight']
               END
             },
             r.updated_at = $now
RETURN r
"""

GET_EDGES_FROM = """
MATCH (a:SocioNode {id: $node_id})-[r]->(b:SocioNode)
RETURN type(r) AS edge_type, r AS rel, b AS target
"""

GET_EDGES_TO = """
MATCH (a:SocioNode)-[r]->(b:SocioNode {id: $node_id})
RETURN type(r) AS edge_type, r AS rel, a AS source
"""

EDGE_COUNT = """
MATCH (n:SocioNode {child_id: $child_id})-[r]->()
RETURN count(r) AS count
"""


# NOTE: Neo4j forbids parameters in the variable-length bound (`*1..$n`); the
# depth must be a literal. Use build_traverse()/build_neighborhood() so the
# int-coerced depth is inlined safely (coercion also prevents injection).
def build_traverse(max_depth: int = 5) -> str:
    depth = _bounded_hops(max_depth)
    return f"""
MATCH path = (start:SocioNode {{id: $start_id}})-[r*1..{depth}]->(end:SocioNode)
WHERE ALL(rel IN relationships(path) WHERE coalesce(properties(rel)['weight'], 1.0) >= $min_confidence)
RETURN nodes(path) AS path_nodes, relationships(path) AS path_rels
LIMIT $limit
"""


SHORTEST_PATH = """
MATCH (a:SocioNode {id: $source_id}), (b:SocioNode {id: $target_id})
MATCH path = shortestPath((a)-[*]-(b))
RETURN [n IN nodes(path) | n.id] AS node_ids,
       length(path) AS path_length
"""


def build_neighborhood(radius: int = 2) -> str:
    hops = _bounded_hops(radius)
    return f"""
MATCH (n:SocioNode {{id: $node_id}})-[*1..{hops}]-(neighbor:SocioNode)
WHERE neighbor.child_id = $child_id
RETURN DISTINCT neighbor
"""


FIND_INFERENCE_CHAIN = """
MATCH path = (a:SocioNode {child_id: $child_id, node_type: $from_type})
             -[r*1..6]->
             (b:SocioNode {child_id: $child_id, node_type: $to_type})
RETURN [n IN nodes(path) | n] AS path_nodes,
       [rel IN relationships(path) | {type: type(rel), weight: coalesce(properties(rel)['weight'], 1.0)}] AS path_rels,
       length(path) AS path_length
ORDER BY path_length ASC
LIMIT 10
"""

COACHING_SUBGRAPH = """
MATCH path = (c:SocioNode {id: $child_node_id})-[*1..6]->(impl:SocioNode {node_type: 'Implication'})
WHERE impl.child_id = $child_id
RETURN nodes(path) AS path_nodes, relationships(path) AS path_rels
ORDER BY impl.confidence DESC
LIMIT 20
"""

FIND_CONTRADICTIONS = """
MATCH (a:SocioNode {child_id: $child_id})-[r:CONTRADICTS]->(b:SocioNode)
RETURN a, b, coalesce(properties(r)['weight'], 0.5) AS tension_score
ORDER BY tension_score DESC
"""

FIND_COMPETING_IMPLICATIONS = """
MATCH (a:SocioNode {child_id: $child_id, node_type: 'Implication'})
MATCH (b:SocioNode {child_id: $child_id, node_type: 'Implication'})
WHERE a.id < b.id
  AND a.dimension = b.dimension
  AND a.direction <> b.direction
RETURN a, b
"""

MARK_STALE_CASCADE = """
MATCH (:SocioNode {id: $node_id})-[:DERIVES*1..10]->(downstream:SocioNode)
SET downstream.stale = true
RETURN count(downstream) AS marked_count
"""

GET_STALE_NODES = """
MATCH (n:SocioNode {child_id: $child_id, stale: true})
RETURN n
ORDER BY n.created_at ASC
"""

GET_DERIVES_INPUTS = """
MATCH (input:SocioNode)-[:DERIVES]->(target:SocioNode {id: $node_id})
RETURN input
"""

QUERY_BY_EVENT_DATE = """
MATCH (n:SocioNode {child_id: $child_id})
WHERE n.event_date IS NOT NULL
  AND n.event_date >= $start
  AND n.event_date <= $end
  AND ($node_type IS NULL OR n.node_type = $node_type)
RETURN n
ORDER BY n.event_date ASC
"""

GET_TIMELINE = """
MATCH (n:SocioNode {child_id: $child_id})
WHERE n.event_date IS NOT NULL
RETURN n
ORDER BY n.event_date ASC
"""

VISIT_PATTERN = """
MATCH (c:SocioNode {child_id: $child_id, node_type: 'Child'})-[:VISITED]->(v:SocioNode)-[:AT]->(p:SocioNode)
WHERE v.event_date >= $start AND v.event_date <= $end
RETURN p.place_type AS place_type, p.place_subtype AS subtype,
       count(v) AS visit_count,
       collect(v.event_date) AS dates
ORDER BY visit_count DESC
"""

GET_PROVENANCE_CHAIN = """
MATCH path = (source:SocioNode)-[:DERIVES*0..10]->(target:SocioNode {id: $node_id})
WHERE source.child_id = $child_id
RETURN [n IN nodes(path) | {
    id: n.id,
    node_type: n.node_type,
    source_chunk: n.source_chunk,
    document_date: n.document_date
}] AS provenance_chain
ORDER BY length(path) DESC
LIMIT 5
"""

COMPUTE_CONVERGENCE = """
MATCH (source:SocioNode)-[:INDICATES|DERIVES]->(target:SocioNode {id: $node_id})
RETURN count(DISTINCT source) AS convergence_count
"""

AGGREGATE_PROFILE = """
MATCH (c:SocioNode {id: $child_node_id, node_type: 'Child'})
OPTIONAL MATCH (c)-[:LIVES_IN]->(area:SocioNode {node_type: 'Neighborhood'})
OPTIONAL MATCH (area)-[:HAS_CONTEXT]->(econ:SocioNode {node_type: 'Economic'})
OPTIONAL MATCH (area)-[:HAS_CONTEXT]->(safety:SocioNode {node_type: 'Safety'})
OPTIONAL MATCH (area)-[:HAS_CONTEXT]->(culture:SocioNode {node_type: 'Cultural'})
OPTIONAL MATCH (area)-[:HAS_CONTEXT]->(transport:SocioNode {node_type: 'Transport'})
OPTIONAL MATCH (area)-[:HAS_CONTEXT]->(re:SocioNode {node_type: 'RealEstate'})
OPTIONAL MATCH (c)-[:ATTENDS]->(school:SocioNode {node_type: 'School'})
OPTIONAL MATCH (c)<-[:PARENT_OF]-(parent:SocioNode {node_type: 'Parent'})
OPTIONAL MATCH (parent)-[:WORKS_AT]->(employer:SocioNode {node_type: 'Employer'})
OPTIONAL MATCH (income:SocioNode {child_id: $child_id, node_type: 'Income'})
OPTIONAL MATCH (c)-[:VISITED]->(:SocioNode)-[:AT]->(place:SocioNode)
OPTIONAL MATCH (c)-[:INDICATES|DERIVES*1..3]->(religious:SocioNode {node_type: 'Religious'})
OPTIONAL MATCH (c)-[:INDICATES|DERIVES*1..3]->(lifestyle:SocioNode {node_type: 'Lifestyle'})
OPTIONAL MATCH (c)-[:INDICATES|DERIVES*1..3]->(sensory:SocioNode {node_type: 'SensoryEvidence'})
RETURN
    area, econ, safety, culture, transport, re,
    school, parent, employer, income,
    collect(DISTINCT place) AS places,
    collect(DISTINCT religious) AS religious_nodes,
    collect(DISTINCT lifestyle) AS lifestyle_nodes,
    collect(DISTINCT sensory) AS sensory_nodes
"""


def build_merge_edge(edge_type: str) -> str:
    relationship = EdgeType(edge_type).value
    return MERGE_EDGE.replace("{edge_type}", relationship)


def build_traverse_with_types(edge_types: list[str], max_depth: int = 5) -> str:
    if edge_types:
        rel_filter = "|".join(EdgeType(edge_type).value for edge_type in edge_types)
        depth = _bounded_hops(max_depth)
        return f"""
MATCH path = (start:SocioNode {{id: $start_id}})-[r:{rel_filter}*1..{depth}]->(end:SocioNode)
WHERE ALL(rel IN relationships(path) WHERE coalesce(properties(rel)['weight'], 1.0) >= $min_confidence)
  AND end.child_id = $child_id
RETURN nodes(path) AS path_nodes, relationships(path) AS path_rels
LIMIT $limit
"""
    return build_traverse(max_depth)


def build_event_date_query(node_type: str | None = None) -> str:
    return QUERY_BY_EVENT_DATE


def _bounded_hops(value: int) -> int:
    hops = int(value)
    if not 1 <= hops <= 10:
        raise ValueError("graph traversal depth must be between 1 and 10")
    return hops
