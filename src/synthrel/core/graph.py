"""
Dependency graph analysis and topological sorting for relational schemas.
"""
from typing import Dict, List, Set, Tuple
import networkx as nx

from synthrel.core.models import DatabaseSchemaConfig


class SchemaDependencyGraph:
    """
    Constructs a Directed Acyclic Graph (DAG) representing:
    1. Foreign Key dependencies between tables (Parent -> Child).
    2. Cross-table Temporal dependencies (Parent event -> Child event).
    """

    def __init__(self, config: DatabaseSchemaConfig):
        self.config = config
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self) -> None:
        # 1. Add all tables as nodes
        for table_name in self.config.tables.keys():
            self.graph.add_node(table_name)

        # 2. Add edges from Foreign Keys (Parent -> Child)
        for table_name, table_cfg in self.config.tables.items():
            for col_name, fk_cfg in table_cfg.foreign_keys.items():
                parent_table = fk_cfg.references.split(".")[0]
                if parent_table != table_name:  # Self-referencing handled separately
                    self.graph.add_edge(parent_table, table_name, kind="foreign_key", col=col_name)

            # 3. Add edges from Cross-table Temporal Dependencies
            for col_name, col_cfg in table_cfg.columns.items():
                if col_cfg.temporal_dependency:
                    parent_ref = col_cfg.temporal_dependency.parent_field
                    parent_table = parent_ref.split(".")[0]
                    if parent_table != table_name:
                        self.graph.add_edge(parent_table, table_name, kind="temporal", col=col_name)

    def detect_cycles(self) -> List[List[str]]:
        """Finds any circular dependencies that would break topological order."""
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except Exception:
            return []

    def get_generation_order(self) -> List[str]:
        """
        Calculates the topological order for table generation.
        Raises ValueError if cyclic dependencies are detected.
        """
        cycles = self.detect_cycles()
        if cycles:
            cycle_desc = " -> ".join(cycles[0] + [cycles[0][0]])
            raise ValueError(
                f"Cyclic dependency detected in schema graph: {cycle_desc}. "
                "Circular dependencies must be resolved via nullable fields or deferrable constraints."
            )
        return list(nx.topological_sort(self.graph))

    def get_dependencies_for_table(self, table_name: str) -> List[str]:
        """Returns direct parents (tables that must be generated before this table)."""
        return list(self.graph.predecessors(table_name))

    def get_dependents_for_table(self, table_name: str) -> List[str]:
        """Returns direct children (tables that depend on this table)."""
        return list(self.graph.successors(table_name))

    def to_mermaid(self) -> str:
        """Exports the graph to Mermaid markdown format for documentation/thesis."""
        lines = ["flowchart TD"]
        for node in self.graph.nodes():
            row_count = self.config.tables[node].target_rows
            lines.append(f'    {node}["{node}<br/>({row_count:,} rows)"]')

        for u, v, data in self.graph.edges(data=True):
            kind = data.get("kind", "")
            col = data.get("col", "")
            label = f"{kind}: {col}" if col else kind
            lines.append(f'    {u} -->|"{label}"| {v}')

        return "\n".join(lines)
