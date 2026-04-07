from __future__ import annotations

from sociomemory.graph.edges import EdgeType
from sociomemory.graph.nodes import NodeType

ALLOWED_EDGES: dict[tuple[NodeType, EdgeType], list[NodeType]] = {
    (NodeType.CHILD, EdgeType.LIVES_IN): [NodeType.NEIGHBORHOOD],
    (NodeType.CHILD, EdgeType.ATTENDS): [NodeType.SCHOOL],
    (NodeType.CHILD, EdgeType.VISITED): [NodeType.VISIT],
    (NodeType.PARENT, EdgeType.PARENT_OF): [NodeType.CHILD],
    (NodeType.PARENT, EdgeType.WORKS_AT): [NodeType.EMPLOYER],
    (NodeType.NEIGHBORHOOD, EdgeType.LOCATED_IN): [NodeType.CITY],
    (NodeType.CITY, EdgeType.LOCATED_IN): [NodeType.STATE],
    (NodeType.STATE, EdgeType.LOCATED_IN): [NodeType.COUNTRY],
    (NodeType.NEIGHBORHOOD, EdgeType.HAS_CONTEXT): [
        NodeType.ECONOMIC, NodeType.CULTURAL, NodeType.SAFETY,
        NodeType.TRANSPORT, NodeType.REAL_ESTATE,
    ],
    (NodeType.NEIGHBORHOOD, EdgeType.NEAR_TO): [NodeType.PLACE, NodeType.SCHOOL, NodeType.THERAPY_CENTER],
    (NodeType.VISIT, EdgeType.AT): [NodeType.PLACE],
    (NodeType.VISIT, EdgeType.INDICATES): [
        NodeType.RELIGIOUS, NodeType.LIFESTYLE, NodeType.SENSORY_EVIDENCE,
        NodeType.THERAPY_OPPORTUNITY, NodeType.DIETARY, NodeType.COMMUNITY,
    ],
    (NodeType.REAL_ESTATE, EdgeType.DERIVES): [NodeType.INCOME],
    (NodeType.SCHOOL, EdgeType.DERIVES): [NodeType.INCOME],
    (NodeType.EMPLOYER, EdgeType.DERIVES): [NodeType.INCOME],
    (NodeType.INCOME, EdgeType.IMPLIES): [NodeType.IMPLICATION],
    (NodeType.SAFETY, EdgeType.IMPLIES): [NodeType.IMPLICATION],
    (NodeType.TRANSPORT, EdgeType.IMPLIES): [NodeType.IMPLICATION],
    (NodeType.IMPLICATION, EdgeType.CONTRADICTS): [NodeType.IMPLICATION],
}


def validate_edge(source_type: NodeType, edge_type: EdgeType, target_type: NodeType) -> bool:
    allowed_targets = ALLOWED_EDGES.get((source_type, edge_type))
    if allowed_targets is None:
        return True  # Permissive: unknown combos allowed
    return target_type in allowed_targets
