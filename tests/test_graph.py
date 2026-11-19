import pytest
import numpy as np
from synthrel.core.models import (
    DatabaseSchemaConfig,
    TableConfig,
    ForeignKeyConfig,
    TemporalDependencyConfig,
    TemporalOffsetConfig,
)
from synthrel.core.graph import SchemaDependencyGraph
from synthrel.core.temporal import TemporalEngine
from synthrel.generators.distributions import DistributionSampler


def test_topological_sort_linear():
    """Tests simple linear A -> B -> C dependency."""
    cfg = DatabaseSchemaConfig(
        name="test_schema",
        tables={
            "c": TableConfig(
                foreign_keys={"b_id": ForeignKeyConfig(references="b.id")}
            ),
            "a": TableConfig(),
            "b": TableConfig(
                foreign_keys={"a_id": ForeignKeyConfig(references="a.id")}
            ),
        },
    )
    graph = SchemaDependencyGraph(cfg)
    order = graph.get_generation_order()
    assert order == ["a", "b", "c"]


def test_cyclic_dependency_detection():
    """Tests that cyclic dependencies are caught."""
    cfg = DatabaseSchemaConfig(
        name="cyclic_schema",
        tables={
            "orders": TableConfig(
                foreign_keys={"shipment_id": ForeignKeyConfig(references="shipments.id")}
            ),
            "shipments": TableConfig(
                foreign_keys={"order_id": ForeignKeyConfig(references="orders.id")}
            ),
        },
    )
    graph = SchemaDependencyGraph(cfg)
    cycles = graph.detect_cycles()
    assert len(cycles) > 0
    with pytest.raises(ValueError, match="Cyclic dependency detected"):
        graph.get_generation_order()


def test_temporal_offset_integrity():
    """Tests that temporal offset ensures parent_time <= child_time."""
    sampler = DistributionSampler(seed=123)
    engine = TemporalEngine(sampler)

    size = 5000
    parent_ts = engine.generate_timeline("2024-01-01T00:00:00", "2024-06-01T00:00:00", size)

    dep_cfg = TemporalDependencyConfig(
        parent_field="parent.created_at",
        offset=TemporalOffsetConfig(distribution="exponential", min_seconds=60, scale_seconds=3600),
    )
    child_ts = engine.apply_temporal_offset(parent_ts, dep_cfg)

    is_valid, violations = engine.validate_temporal_integrity(parent_ts, child_ts)
    assert is_valid is True
    assert violations == 0
