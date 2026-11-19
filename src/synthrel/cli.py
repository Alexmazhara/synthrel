"""
Command line interface for SynthRel data generator.
"""
from pathlib import Path
import time
import typer
import yaml
from rich.console import Console
from rich.table import Table

from synthrel.core.models import DatabaseSchemaConfig
from synthrel.core.graph import SchemaDependencyGraph
from synthrel.core.temporal import TemporalEngine
from synthrel.generators.distributions import DistributionSampler

app = typer.Typer(
    name="synthrel",
    help="Synthetic Relational Data Generator for DBMS Stress-Testing",
    add_completion=False,
)
console = Console()


def load_config(config_path: Path) -> DatabaseSchemaConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return DatabaseSchemaConfig.model_validate(data)


@app.command()
def validate(
    config_file: Path = typer.Argument(
        Path("configs/ecommerce_rules.yaml"),
        help="Path to YAML schema configuration",
    )
):
    """
    Validates YAML schema configuration and checks for cycles in dependency graph.
    """
    console.print(f"[bold blue]Loading configuration from:[/bold blue] {config_file}")
    try:
        config = load_config(config_file)
        graph = SchemaDependencyGraph(config)
        cycles = graph.detect_cycles()

        if cycles:
            console.print("[bold red]ERROR: Cyclic dependencies detected:[/bold red]")
            for cycle in cycles:
                console.print(f"  [red]->[/red] {' -> '.join(cycle + [cycle[0]])}")
            raise typer.Exit(code=1)

        generation_order = graph.get_generation_order()

        console.print("[bold green]SUCCESS: Configuration is valid and DAG is acyclic![/bold green]\n")
        
        table = Table(title="Topological Generation Order")
        table.add_column("Step", justify="right", style="cyan")
        table.add_column("Table", style="magenta")
        table.add_column("Rows", justify="right", style="green")
        table.add_column("Predecessors (Must exist first)", style="yellow")

        for idx, table_name in enumerate(generation_order, start=1):
            rows = config.tables[table_name].target_rows
            preds = ", ".join(graph.get_dependencies_for_table(table_name)) or "None (Root)"
            table.add_row(str(idx), table_name, f"{rows:,}", preds)

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Validation failed:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command()
def export_mermaid(
    config_file: Path = typer.Argument(
        Path("configs/ecommerce_rules.yaml"),
        help="Path to YAML schema configuration",
    )
):
    """
    Exports the dependency graph to Mermaid markdown.
    """
    config = load_config(config_file)
    graph = SchemaDependencyGraph(config)
    mermaid_code = graph.to_mermaid()
    console.print(mermaid_code)


@app.command()
def verify_temporal_cascade(
    samples: int = typer.Option(10000, help="Number of records to simulate in temporal cascade")
):
    """
    Demonstrates and mathematically verifies a 4-level temporal cascade:
    Customer.created_at -> Order.created_at -> Payment.date -> Shipment.shipped_at -> Shipment.delivered_at
    """
    console.print(f"[bold blue]Simulating temporal cascade on {samples:,} records...[/bold blue]")
    t_start_gen = time.perf_counter()
    sampler = DistributionSampler(seed=42)
    engine = TemporalEngine(sampler)

    # 1. Customers
    cust_created = engine.generate_timeline("2023-01-01T00:00:00", "2024-01-01T00:00:00", samples)

    # 2. Orders (exponential offset, min 1h, scale 7d)
    from synthrel.core.models import TemporalDependencyConfig, TemporalOffsetConfig
    order_cfg = TemporalDependencyConfig(
        parent_field="customers.created_at",
        offset=TemporalOffsetConfig(distribution="exponential", min_seconds=3600, scale_seconds=604800, max_seconds=31536000)
    )
    order_created = engine.apply_temporal_offset(cust_created, order_cfg)

    # 3. Payments (exponential offset, min 1m, scale 30m)
    pay_cfg = TemporalDependencyConfig(
        parent_field="orders.created_at",
        offset=TemporalOffsetConfig(distribution="exponential", min_seconds=60, scale_seconds=1800, max_seconds=172800)
    )
    payment_dates = engine.apply_temporal_offset(order_created, pay_cfg)

    # 4. Shipments: shipped_at (normal offset, min 2h, mean 24h)
    ship_cfg = TemporalDependencyConfig(
        parent_field="payments.payment_date",
        offset=TemporalOffsetConfig(distribution="normal", min_seconds=7200, mean_seconds=86400, std_seconds=28800, max_seconds=432000)
    )
    shipped_at = engine.apply_temporal_offset(payment_dates, ship_cfg)

    # 5. Shipments: delivered_at (normal offset, min 1d, mean 3d)
    deliv_cfg = TemporalDependencyConfig(
        parent_field="shipments.shipped_at",
        offset=TemporalOffsetConfig(distribution="normal", min_seconds=86400, mean_seconds=259200, std_seconds=86400, max_seconds=1209600)
    )
    delivered_at = engine.apply_temporal_offset(shipped_at, deliv_cfg)
    t_end_gen = time.perf_counter()

    # Verification
    t_start_val = time.perf_counter()
    ok1, v1 = engine.validate_temporal_integrity(cust_created, order_created)
    ok2, v2 = engine.validate_temporal_integrity(order_created, payment_dates)
    ok3, v3 = engine.validate_temporal_integrity(payment_dates, shipped_at)
    ok4, v4 = engine.validate_temporal_integrity(shipped_at, delivered_at)
    t_end_val = time.perf_counter()

    gen_duration = t_end_gen - t_start_gen
    val_duration = t_end_val - t_start_val
    total_timestamps = samples * 5
    throughput = total_timestamps / gen_duration if gen_duration > 0 else 0

    table = Table(title="Temporal Integrity Verification Results")
    table.add_column("Constraint Chain", style="cyan")
    table.add_column("Total Rows", justify="right")
    table.add_column("Violations", justify="right")
    table.add_column("Integrity Rate", justify="right", style="green")

    def row(label, viol):
        rate = f"{(samples - viol) / samples * 100:.2f}%"
        table.add_row(label, f"{samples:,}", str(viol), rate)

    row("Customer created <= Order created", v1)
    row("Order created <= Payment date", v2)
    row("Payment date <= Shipped at", v3)
    row("Shipped at <= Delivered at", v4)

    console.print(table)
    if ok1 and ok2 and ok3 and ok4:
        console.print("[bold green]ALL TEMPORAL INVARIANTS SATISFIED (100.00% integrity)![/bold green]")
    else:
        console.print("[bold red]FAIL: Invariants were violated![/bold red]")

    # Performance Benchmark Summary
    perf_table = Table(title="Benchmark Performance Metrics", show_header=True)
    perf_table.add_column("Metric", style="yellow")
    perf_table.add_column("Value", justify="right", style="cyan")

    perf_table.add_row("Total Events Generated (5 levels)", f"{total_timestamps:,}")
    perf_table.add_row("Generation Time", f"{gen_duration:.4f} sec ({gen_duration * 1000:.1f} ms)")
    perf_table.add_row("Throughput (Generation Speed)", f"{throughput:,.0f} timestamps/sec")
    perf_table.add_row("Integrity Verification Time", f"{val_duration:.4f} sec ({val_duration * 1000:.1f} ms)")

    console.print("\n", perf_table)


if __name__ == "__main__":
    app()
