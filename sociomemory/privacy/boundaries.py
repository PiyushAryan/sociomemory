from __future__ import annotations

from sociomemory.graph.nodes import DataLevel, Node, NodeType

NODE_SENSITIVITY_DEFAULTS: dict[NodeType, DataLevel] = {
    NodeType.CHILD: DataLevel.PERSONAL,
    NodeType.PARENT: DataLevel.PERSONAL,
    NodeType.FAMILY: DataLevel.PERSONAL,
    NodeType.NEIGHBORHOOD: DataLevel.PERSONAL,
    NodeType.CITY: DataLevel.CONTEXTUAL,
    NodeType.STATE: DataLevel.PUBLIC,
    NodeType.COUNTRY: DataLevel.PUBLIC,
    NodeType.PLACE: DataLevel.CONTEXTUAL,
    NodeType.SCHOOL: DataLevel.PERSONAL,
    NodeType.EMPLOYER: DataLevel.PERSONAL,
    NodeType.THERAPY_CENTER: DataLevel.CONTEXTUAL,
    NodeType.ECONOMIC: DataLevel.CONTEXTUAL,
    NodeType.CULTURAL: DataLevel.CONTEXTUAL,
    NodeType.SAFETY: DataLevel.PUBLIC,
    NodeType.TRANSPORT: DataLevel.PUBLIC,
    NodeType.REAL_ESTATE: DataLevel.CONTEXTUAL,
    NodeType.INCOME: DataLevel.SENSITIVE,
    NodeType.VISIT: DataLevel.PERSONAL,
    NodeType.SENSORY_EVIDENCE: DataLevel.PERSONAL,
    NodeType.THERAPY_OPPORTUNITY: DataLevel.CONTEXTUAL,
    NodeType.RELIGIOUS: DataLevel.SENSITIVE,
    NodeType.DIETARY: DataLevel.PERSONAL,
    NodeType.LIFESTYLE: DataLevel.CONTEXTUAL,
    NodeType.COMMUNITY: DataLevel.PERSONAL,
    NodeType.IMPLICATION: DataLevel.CONTEXTUAL,
    NodeType.TRADEOFF: DataLevel.CONTEXTUAL,
    NodeType.SIGNAL: DataLevel.PERSONAL,
}

LEVEL_ORDER = [DataLevel.PUBLIC, DataLevel.CONTEXTUAL, DataLevel.PERSONAL, DataLevel.SENSITIVE]


class DataBoundary:
    def get_default_sensitivity(self, node_type: NodeType) -> DataLevel:
        return NODE_SENSITIVITY_DEFAULTS.get(node_type, DataLevel.CONTEXTUAL)

    def filter_nodes(self, nodes: list[Node], max_level: DataLevel) -> list[Node]:
        max_idx = LEVEL_ORDER.index(max_level)
        return [n for n in nodes if LEVEL_ORDER.index(n.sensitivity) <= max_idx]

    def redact_node(self, node: Node, max_level: DataLevel) -> Node | None:
        max_idx = LEVEL_ORDER.index(max_level)
        node_idx = LEVEL_ORDER.index(node.sensitivity)
        if node_idx > max_idx:
            return None
        safe_props = {
            k: v
            for k, v in node.properties.items()
            if k not in ("exact_address", "phone", "id_number")
        }
        return node.model_copy(update={"properties": safe_props})
