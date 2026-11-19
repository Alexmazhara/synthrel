"""
Pydantic models for configuration, schema definition, and dependency rules.
"""
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field


class TemporalOffsetConfig(BaseModel):
    distribution: Literal["constant", "uniform", "exponential", "normal"] = "uniform"
    min_seconds: int = 0
    max_seconds: int = 86400
    scale_seconds: Optional[int] = None
    mean_seconds: Optional[int] = None
    std_seconds: Optional[int] = None


class TemporalDependencyConfig(BaseModel):
    parent_field: str  # e.g., "orders.created_at" or "shipments.shipped_at"
    relation: Literal["greater_or_equal", "greater", "less_or_equal", "less"] = "greater_or_equal"
    offset: Optional[TemporalOffsetConfig] = None


class ColumnConfig(BaseModel):
    type: str  # autoincrement, datetime, numeric, integer, categorical, email, etc.
    values: Optional[List[Any]] = None
    weights: Optional[List[float]] = None
    min: Optional[Union[int, float]] = None
    max: Optional[Union[int, float]] = None
    prefix: Optional[str] = None
    range: Optional[List[str]] = None
    distribution: Optional[str] = None
    from_field: Optional[str] = None
    temporal_dependency: Optional[TemporalDependencyConfig] = None


class ForeignKeyConfig(BaseModel):
    references: str  # e.g., "customers.id"
    distribution: Literal["uniform", "zipf", "cardinality_range", "unique_parent"] = "uniform"
    alpha: Optional[float] = 1.5  # Zipf parameter
    min_per_parent: Optional[int] = 1
    max_per_parent: Optional[int] = 5


class TableConfig(BaseModel):
    target_rows: int = Field(default=1000, gt=0)
    primary_key: str = "id"
    foreign_keys: Dict[str, ForeignKeyConfig] = Field(default_factory=dict)
    columns: Dict[str, ColumnConfig] = Field(default_factory=dict)


class GlobalSettings(BaseModel):
    seed: int = 42
    default_start_time: str = "2023-01-01T00:00:00"
    default_end_time: str = "2025-01-01T00:00:00"


class DatabaseSchemaConfig(BaseModel):
    version: str = "1.0"
    name: str
    description: Optional[str] = None
    global_settings: GlobalSettings = Field(default_factory=GlobalSettings)
    tables: Dict[str, TableConfig]
