"""
Cypher query library — all reusable Neo4j queries in one place.
Every query here is a module-level string constant or a builder function.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Node operations
# ---------------------------------------------------------------------------

MERGE_NODE = """
MERGE (n:SocioNode {{id: $id, child_id: $child_id}})
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

# ---------------------------------------------------------------------------
# Edge operations
# ---------------------------------------------------------------------------

MERGE_EDGE = """
MATCH (a:SocioNode {id: $source_id})
MATCH (b:SocioNode {id: $target_id})
MERGE (a)-[r:{edge_type}]->(b)
ON CREATE SET r += $props, r.created_at = $now
ON MATCH SET r.weight = CASE WHEN r.weight < $weight THEN $weight ELSE r.weight END,
             r.updated_at = $now
RETURN r
"""

GET_EDGES_FROM = """
MATCH (a:SocioNode {{id: $node_id}})-[r]->(b:SocioNode)
RETURN type(r) AS edge_type, r AS rel, b AS target
"""

GET_EDGES_TO = """
MATCH (a:SocioNode)-[r]->(b:SocioNode {{id: $node_id}})
RETURN type(r) AS edge_type, r AS rel, a AS source
"""

EDGE_COUNT = """
MATCH (n:SocioNode {child_id: $child_id})-[r]->()
RETURN count(r) AS count
"""

# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------

TRAVERSE = """
MATCH path = (start:SocioNode {id: $start_id})-[r*1..$max_depth]->(end:SocioNode)
WHERE ALL(rel IN relationships(path) WHERE rel.weight >= $min_confidence)
RETURN nodes(path) AS path_nodes, relationships(path) AS path_rels
LIMIT $limit
"""

SHORTEST_PATH = """
MATCH (a:SocioNode {id: $source_id}), (b:SocioNode {id: $target_id})
MATCH path = shortestPath((a)-[*]-(b))
RETURN [n IN nodes(path) | n.id] AS node_ids,
       length(path) AS path_length
"""

NEIGHBORHOOD = """
MATCH (n:SocioNode {id: $node_id})-[*1..$radius]-(neighbor:SocioNode)
WHERE neighbor.child_id = $child_id
RETURN DISTINCT neighbor
"""

FIND_INFERENCE_CHAIN = """
MATCH path = (a:SocioNode {child_id: $child_id, node_type: $from_type})
             -[r*1..6]->
             (b:SocioNode {child_id: $child_id, node_type: $to_type})
RETURN [n IN nodes(path) | n] AS path_nodes,
       [rel IN relationships(path) | {type: type(rel), weight: rel.weight}] AS path_rels,
       length(path) AS path_length
ORDER BY path_length ASC
LIMIT 10
"""

# ---------------------------------------------------------------------------
# Coaching subgraph
# ---------------------------------------------------------------------------

COACHING_SUBGRAPH = """
MATCH path = (c:SocioNode {id: $child_node_id})-[*1..6]->(impl:SocioNode {node_type: 'Implication'})
WHERE impl.child_id = $child_id
RETURN nodes(path) AS path_nodes, relationships(path) AS path_rels
ORDER BY impl.confidence DESC
LIMIT 20
"""

# ---------------------------------------------------------------------------
# Contradiction / trade-off detection
# ---------------------------------------------------------------------------

FIND_CONTRADICTIONS = """
MATCH (a:SocioNode {child_id: $child_id})-[r:CONTRADICTS]->(b:SocioNode)
RETURN a, b, r.weight AS tension_score
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

# ---------------------------------------------------------------------------
# Versioning (UPDATES / EXTENDS / DERIVES)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Temporal queries (dual-layer timestamps)
# ---------------------------------------------------------------------------

QUERY_BY_EVENT_DATE = """
MATCH (n:SocioNode {child_id: $child_id})
WHERE n.event_date IS NOT NULL
  AND n.event_date >= $start
  AND n.event_date <= $end
{type_filter}
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

# ---------------------------------------------------------------------------
# Provenance (source chunk tracing)
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Confidence / convergence
# ---------------------------------------------------------------------------

COMPUTE_CONVERGENCE = """
MATCH (source:SocioNode)-[:INDICATES|DERIVES]->(target:SocioNode {id: $node_id})
RETURN count(DISTINCT source) AS convergence_count
"""

# ---------------------------------------------------------------------------
# Profile aggregation (single-query profile computation)
# ---------------------------------------------------------------------------

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
OPTIONAL MATCH (c)-[:INDICATES|:DERIVES*1..3]->(religious:SocioNode {node_type: 'Religious'})
OPTIONAL MATCH (c)-[:INDICATES|:DERIVES*1..3]->(lifestyle:SocioNode {node_type: 'Lifestyle'})
OPTIONAL MATCH (c)-[:INDICATES|:DERIVES*1..3]->(sensory:SocioNode {node_type: 'SensoryEvidence'})
RETURN
    area, econ, safety, culture, transport, re,
    school, parent, employer, income,
    collect(DISTINCT place) AS places,
    collect(DISTINCT religious) AS religious_nodes,
    collect(DISTINCT lifestyle) AS lifestyle_nodes,
    collect(DISTINCT sensory) AS sensory_nodes
"""

def build_merge_edge(edge_type: str) -> str:
    """Build a MERGE edge Cypher with the given relationship type."""
    return MERGE_EDGE.replace("{edge_type}", edge_type)

def build_traverse_with_types(edge_types: list[str], max_depth: int = 5) -> str:
    """Build a traversal query filtered to specific edge types."""
    if edge_types:
        rel_filter = "|".join(edge_types)
        return f"""
MATCH path = (start:SocioNode {{id: $start_id}})-[r:{rel_filter}*1..{max_depth}]->(end:SocioNode)
WHERE ALL(rel IN relationships(path) WHERE rel.weight >= $min_confidence)
  AND end.child_id = $child_id
RETURN nodes(path) AS path_nodes, relationships(path) AS path_rels
LIMIT $limit
"""
    return TRAVERSE

def build_event_date_query(node_type: str | None = None) -> str:
    """Build temporal query, optionally filtered by node type."""
    type_filter = f"AND n.node_type = '{node_type}'" if node_type else ""
    return QUERY_BY_EVENT_DATE.format(type_filter=type_filter)
