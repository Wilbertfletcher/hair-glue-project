"""
DuckDB Loading Module

Loads Parquet files into DuckDB warehouse and creates views.
"""

import duckdb
from pathlib import Path


def load_to_duckdb(parquet_path: Path, table_name: str) -> None:
    """Load Parquet file into DuckDB table."""
    conn = duckdb.connect("warehouse.db")
    conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM read_parquet('{parquet_path}')")
    conn.close()
    print(f"Loaded {table_name} from {parquet_path}")


def create_views() -> None:
    """Create warehouse views."""
    conn = duckdb.connect("warehouse.db")

    # v_product_ingredient_counts (assuming it exists or create placeholder)
    conn.execute("""
    CREATE OR REPLACE VIEW v_product_ingredient_counts AS
    SELECT
        p.product_name,
        COUNT(b.chemical_id) as ingredient_count
    FROM dim_product p
    LEFT JOIN bridge_product_chemical b ON p.product_id = b.product_id
    GROUP BY p.product_id, p.product_name
    """)

    # v_hazard_pending_summary
    conn.execute("""
    CREATE OR REPLACE VIEW v_hazard_pending_summary AS
    SELECT
        COUNT(*) as total_chemicals,
        COUNT(CASE WHEN hazard_status = 'PENDING_SOURCE' THEN 1 END) as pending_source_count,
        ROUND(100.0 * COUNT(CASE WHEN hazard_status = 'PENDING_SOURCE' THEN 1 END) / COUNT(*), 2) as pending_source_pct,
        COUNT(CASE WHEN ghs_classes IS NOT NULL OR signal_word IS NOT NULL THEN 1 END) as hazard_populated_count,
        ROUND(100.0 * COUNT(CASE WHEN ghs_classes IS NOT NULL OR signal_word IS NOT NULL THEN 1 END) / COUNT(*), 2) as hazard_populated_pct
    FROM dim_chemical
    """)

    # v_resolution_summary
    conn.execute("""
    CREATE OR REPLACE VIEW v_resolution_summary AS
    SELECT
        s.total_chemicals,
        s.cas_present_count,
        s.resolved_dtxsid_count,
        s.resolved_by_cas_count,
        s.resolved_by_name_count,
        s.unresolved_count,
        s.resolution_rate
    FROM read_parquet('data/curated/fact_resolution_stats.parquet') s
    """)

    # v_unresolved_chemicals
    conn.execute("""
    CREATE OR REPLACE VIEW v_unresolved_chemicals AS
    SELECT
        c.chemical_id,
        c.casrn,
        c.ingredient_normalized,
        c.dtxsid
    FROM dim_chemical_enriched c
    WHERE c.dtxsid IS NULL
    """)

    conn.close()
    print("Views created: v_product_ingredient_counts, v_hazard_pending_summary, v_resolution_summary, v_unresolved_chemicals")