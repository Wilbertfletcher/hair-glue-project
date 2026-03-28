#!/usr/bin/env python3
"""
Hair Glue Project Pipeline CLI

Commands:
- ingest-cscp --csv <path>: Ingest CSCP CSV, build dimensions, write Parquet
- build-warehouse: Load Parquet into DuckDB warehouse with views
"""

import argparse
import sys
from pathlib import Path


from pipeline.extract.cscp import parse_cscp_csv
from pipeline.transform.build_dims_facts import (
    build_dim_product,
    build_dim_chemical,
    build_bridge_product_chemical,
)
from pipeline.transform.enrich_chemspider import (
    enrich_chemicals_with_chemspider,
)
from pipeline.transform.enrich_ctx import enrich_chemicals_with_ctx
from pipeline.load.to_parquet import write_parquet
from pipeline.load.to_duckdb import load_to_duckdb, create_views


def cmd_ingest_cscp(csv_path: str) -> None:
    """Ingest CSCP CSV, build dimensions, write Parquet files."""
    print(f"Loading CSCP CSV from {csv_path}...")
    cscp_df = parse_cscp_csv(csv_path)

    print("Building dim_chemical...")
    dim_chemical = build_dim_chemical(cscp_df)

    print("Building dim_product...")
    dim_product = build_dim_product(cscp_df)

    print("Building bridge_product_chemical...")
    bridge_df = build_bridge_product_chemical(
        cscp_df, dim_product, dim_chemical
    )

    # Write Parquet files
    curated_dir = Path("data/curated")
    curated_dir.mkdir(parents=True, exist_ok=True)

    write_parquet(dim_chemical, curated_dir / "dim_chemical.parquet")
    write_parquet(dim_product, curated_dir / "dim_product.parquet")
    write_parquet(bridge_df, curated_dir / "bridge_product_chemical.parquet")

    print("Ingestion complete. Parquet files written to data/curated/")


def cmd_build_warehouse() -> None:
    """Load Parquet into DuckDB warehouse with views."""
    print("Building DuckDB warehouse...")
    curated_dir = Path("data/curated")

    # Load tables
    load_to_duckdb(curated_dir / "dim_product.parquet", "dim_product")
    load_to_duckdb(curated_dir / "dim_chemical.parquet", "dim_chemical")
    load_to_duckdb(
        curated_dir / "bridge_product_chemical.parquet",
        "bridge_product_chemical"
    )

    # Create views
    create_views()

    print("Warehouse built. Views created.")


def cmd_enrich_chemspider() -> None:
    """Enrich chemical dimension with ChemSpider structure data."""
    print("Enriching chemicals with ChemSpider data...")
    curated_dir = Path("data/curated")

    dim_chemical_path = curated_dir / "dim_chemical.parquet"
    enriched_path = curated_dir / "dim_chemical_chemspider.parquet"

    enrich_chemicals_with_chemspider(
        str(dim_chemical_path), str(enriched_path)
    )

    # Replace the original file
    enriched_path.replace(dim_chemical_path)
    print("Chemical dimension enriched with ChemSpider data and updated.")


def cmd_enrich_ctx() -> None:
    """Enrich chemicals with CompTox CTX structure/identifier data."""
    input_path = "data/curated/dim_chemical.parquet"
    output_path = "data/curated/dim_chemical_enriched.parquet"
    stats_path = "data/curated/fact_resolution_stats.parquet"
    enrich_chemicals_with_ctx(input_path, output_path, stats_path)
    print(
        f"CTX enrichment complete. Output: {output_path}\nStats: {stats_path}"
    )


def cmd_enrich_regulatory() -> None:
    """Fetch regulatory data from CompTox + PubChem (TSCA, Prop 65, REACH, IARC)."""
    import importlib
    mod = importlib.import_module("warehouse.source_regulatory_data")
    mod.main()


def main() -> None:
    parser = argparse.ArgumentParser(description="Hair Glue Project Pipeline")
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )

    # ingest-cscp command
    ingest_parser = subparsers.add_parser(
        "ingest-cscp", help="Ingest CSCP CSV"
    )
    ingest_parser.add_argument(
        "--csv", required=True, help="Path to CSCP CSV file"
    )

    # build-warehouse command
    subparsers.add_parser("build-warehouse", help="Build DuckDB warehouse")

    # enrich-hazards command
    subparsers.add_parser(
        "enrich-hazards", help="Enrich chemicals with hazard data"
    )

    # enrich-chemspider command
    subparsers.add_parser(
        "enrich-chemspider", help="Enrich chemicals with ChemSpider data"
    )

    # enrich-ctx command
    subparsers.add_parser(
        "enrich-ctx", help="Enrich chemicals with CompTox CTX data"
    )

    # enrich-regulatory command
    subparsers.add_parser(
        "enrich-regulatory",
        help="Fetch regulatory data (TSCA, Prop 65, REACH, IARC) from CompTox + PubChem",
    )

    args = parser.parse_args()

    if args.command == "ingest-cscp":
        cmd_ingest_cscp(args.csv)
    elif args.command == "build-warehouse":
        cmd_build_warehouse()
    elif args.command == "enrich-hazards":
        print("enrich-hazards command is not yet implemented.")
        sys.exit(1)
    elif args.command == "enrich-chemspider":
        cmd_enrich_chemspider()
    elif args.command == "enrich-ctx":
        cmd_enrich_ctx()
    elif args.command == "enrich-regulatory":
        cmd_enrich_regulatory()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
