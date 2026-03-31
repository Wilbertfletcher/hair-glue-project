#!/usr/bin/env python3
"""
Hair Glue Project — Interactive Dashboard

Streamlit-based web interface for exploring hair-glue product hazard data.

Run:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

WAREHOUSE = Path("warehouse")


@st.cache_data
def load_data():
    """Load all warehouse Parquet files."""
    data = {}
    files = {
        "products": "dim_products.parquet",
        "ingredients": "dim_ingredients.parquet",
        "fact_pi": "fact_product_ingredients.parquet",
        "identity": "ingredient_identity_matched.parquet",
        "ref_chemicals": "ref_chemicals.parquet",
        "hazard_ref": "ref_chemicals_hazard.parquet",
        "hazard_classes": "dim_hazard_classes.parquet",
        "fact_hazards": "fact_chemical_hazards.parquet",
        "product_hazards": "product_hazard_summary.parquet",
        "brands": "dim_brands.parquet",
        "categories": "category_hazard_analysis.parquet",
    }
    for key, fname in files.items():
        path = WAREHOUSE / fname
        if path.exists():
            data[key] = pd.read_parquet(path)
        else:
            data[key] = pd.DataFrame()
    return data


def page_overview(data):
    """Project overview / executive summary page."""
    st.header("Executive Summary")

    products = data["products"]
    ingredients = data["ingredients"]
    identity = data["identity"]
    ph = data["product_hazards"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Products", len(products))
    col2.metric("Unique Ingredients", len(ingredients))
    col3.metric("Identity Match Rate", f"{identity['canonical_name'].notna().mean():.0%}")

    if len(ph) > 0 and 'hazard_flag' in ph.columns:
        high_pct = (ph['hazard_flag'] == 'HIGH').mean()
        col4.metric("High Hazard Products", f"{high_pct:.0%}")

    st.divider()

    # Hazard distribution
    if len(ph) > 0 and 'hazard_flag' in ph.columns:
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Hazard Flag Distribution")
            flag_counts = ph['hazard_flag'].value_counts().reset_index()
            flag_counts.columns = ['Hazard Flag', 'Count']
            color_map = {'HIGH': '#e74c3c', 'MEDIUM': '#f39c12', 'LOW': '#2ecc71', 'NO_DATA': '#95a5a6'}
            fig = px.pie(flag_counts, values='Count', names='Hazard Flag',
                         color='Hazard Flag', color_discrete_map=color_map)
            fig.update_layout(margin=dict(t=20, b=20))
            st.plotly_chart(fig, width='stretch')

        with col_right:
            st.subheader("Hazard Score Distribution")
            fig = px.histogram(ph, x='hazard_score', nbins=20,
                               color_discrete_sequence=['#3498db'])
            fig.update_layout(xaxis_title="Hazard Score", yaxis_title="Products",
                              margin=dict(t=20, b=20))
            st.plotly_chart(fig, width='stretch')

    # Category analysis
    cats = data["categories"]
    if len(cats) > 0:
        st.subheader("Category Risk Overview")
        fig = px.bar(cats.sort_values('avg_hazard_score', ascending=True),
                     x='avg_hazard_score', y='category_raw', orientation='h',
                     color='pct_high_hazard',
                     color_continuous_scale='RdYlGn_r',
                     labels={'avg_hazard_score': 'Avg Hazard Score',
                             'category_raw': 'Category',
                             'pct_high_hazard': '% High Hazard'})
        fig.update_layout(margin=dict(t=20, b=20), height=350)
        st.plotly_chart(fig, width='stretch')


def page_products(data):
    """Product browser with search and hazard details."""
    st.header("Product Browser")

    products = data["products"]
    ph = data["product_hazards"]
    identity = data["identity"]

    if len(products) == 0:
        st.warning("No product data available.")
        return

    # Merge product info with hazard summary
    if len(ph) > 0:
        merged = products.merge(ph, on='product_id', how='left', suffixes=('', '_hz'))
    else:
        merged = products.copy()

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        search = st.text_input("Search products", placeholder="Type product name...")
    with col2:
        categories = ['All'] + sorted(merged['category_raw'].dropna().unique().tolist())
        selected_cat = st.selectbox("Category", categories)
    with col3:
        if 'hazard_flag' in merged.columns:
            flags = ['All'] + sorted(merged['hazard_flag'].dropna().unique().tolist())
            selected_flag = st.selectbox("Hazard Level", flags)
        else:
            selected_flag = 'All'

    # Apply filters
    filtered = merged.copy()
    if search:
        filtered = filtered[filtered['product_name'].str.contains(search, case=False, na=False)]
    if selected_cat != 'All':
        filtered = filtered[filtered['category_raw'] == selected_cat]
    if selected_flag != 'All' and 'hazard_flag' in filtered.columns:
        filtered = filtered[filtered['hazard_flag'] == selected_flag]

    st.caption(f"Showing {len(filtered)} of {len(merged)} products")

    # Display table
    display_cols = ['product_name', 'brand', 'company', 'category_raw']
    if 'hazard_score' in filtered.columns:
        display_cols += ['hazard_score', 'hazard_flag', 'num_ingredients']
    st.dataframe(
        filtered[display_cols].rename(columns={
            'product_name': 'Product', 'brand': 'Brand', 'company': 'Company',
            'category_raw': 'Category', 'hazard_score': 'Hazard Score',
            'hazard_flag': 'Risk Level', 'num_ingredients': '# Ingredients'
        }),
        width='stretch',
        height=400,
    )

    # Product detail
    st.divider()
    st.subheader("Product Detail")
    product_names = sorted(filtered['product_name'].tolist())
    if product_names:
        selected_product = st.selectbox("Select a product", product_names)
        prod_row = merged[merged['product_name'] == selected_product].iloc[0]
        pid = prod_row['product_id']

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Brand:** {prod_row.get('brand', 'N/A')}")
            st.markdown(f"**Company:** {prod_row.get('company', 'N/A')}")
            st.markdown(f"**Category:** {prod_row.get('category_raw', 'N/A')}")
        with col_b:
            if 'hazard_score' in prod_row:
                st.markdown(f"**Hazard Score:** {prod_row.get('hazard_score', 'N/A')}")
                st.markdown(f"**Risk Level:** {prod_row.get('hazard_flag', 'N/A')}")
                if 'carcinogen_count' in prod_row:
                    st.markdown(f"**Carcinogen ingredients:** {int(prod_row.get('carcinogen_count', 0))}")

        # Show ingredients for this product
        if len(identity) > 0:
            prod_ingredients = identity[identity['product_id'] == pid]
            if len(prod_ingredients) > 0:
                st.markdown("**Ingredients:**")
                ing_display = prod_ingredients[['ingredient_raw', 'casrn', 'canonical_name', 'match_source']].copy()
                ing_display.columns = ['Ingredient', 'CAS #', 'Canonical Name', 'Match Source']
                st.dataframe(ing_display, width='stretch', hide_index=True)


def page_chemicals(data):
    """Chemical search and hazard profile viewer."""
    st.header("Chemical Database")

    hazard_ref = data["hazard_ref"]
    identity = data["identity"]
    ref = data["ref_chemicals"]

    if len(ref) == 0:
        st.warning("No chemical reference data available.")
        return

    # Search
    search = st.text_input("Search chemicals", placeholder="CAS number or chemical name...")

    # Build chemical view
    chem_view = ref.copy()
    if len(hazard_ref) > 0:
        # Get unique hazard info per casrn (prefer rows with canonical_name)
        haz_dedup = hazard_ref.sort_values('canonical_name', na_position='last').drop_duplicates(
            subset='casrn', keep='first'
        )
        merge_cols = ['casrn']
        haz_cols = [c for c in ['ghs_hazard_class', 'ghs_signal_word', 'h_codes'] if c in haz_dedup.columns]
        chem_view = chem_view.merge(haz_dedup[merge_cols + haz_cols], on='casrn', how='left')

    if search:
        mask = chem_view.apply(
            lambda r: search.lower() in str(r.get('canonical_name', '')).lower()
                      or search.lower() in str(r.get('casrn', '')).lower(),
            axis=1
        )
        chem_view = chem_view[mask]

    st.caption(f"Showing {len(chem_view)} chemicals")

    display_cols = ['casrn', 'canonical_name', 'source']
    if 'ghs_hazard_class' in chem_view.columns:
        display_cols += ['ghs_hazard_class', 'ghs_signal_word']

    st.dataframe(
        chem_view[[c for c in display_cols if c in chem_view.columns]].rename(columns={
            'casrn': 'CAS #', 'canonical_name': 'Chemical Name', 'source': 'Source',
            'ghs_hazard_class': 'GHS Hazard Classes', 'ghs_signal_word': 'Signal Word'
        }),
        width='stretch',
        hide_index=True,
    )

    # Detail view
    if len(hazard_ref) > 0:
        st.divider()
        st.subheader("Chemical Hazard Profile")
        chem_names = chem_view['canonical_name'].dropna().unique().tolist()
        if chem_names:
            selected_chem = st.selectbox("Select chemical", sorted(chem_names))
            chem_row = chem_view[chem_view['canonical_name'] == selected_chem].iloc[0]
            casrn = chem_row.get('casrn')

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**CAS #:** {casrn or 'N/A'}")
                st.markdown(f"**Signal Word:** {chem_row.get('ghs_signal_word', 'N/A')}")
            with col_b:
                classes = chem_row.get('ghs_hazard_class', '')
                if classes and not pd.isna(classes):
                    for cls in str(classes).split('|'):
                        st.markdown(f"- {cls.strip()}")

            # Find products containing this chemical
            if len(identity) > 0 and casrn:
                products_with = identity[identity['casrn'] == casrn]
                if len(products_with) > 0:
                    prods = data["products"]
                    product_list = prods[prods['product_id'].isin(products_with['product_id'])]
                    st.markdown(f"**Found in {len(product_list)} products:**")
                    st.dataframe(
                        product_list[['product_name', 'brand', 'category_raw']].rename(columns={
                            'product_name': 'Product', 'brand': 'Brand', 'category_raw': 'Category'
                        }),
                        width='stretch', hide_index=True
                    )


def page_brands(data):
    """Brand risk analysis page."""
    st.header("Brand Risk Analysis")

    brands = data["brands"]
    if len(brands) == 0:
        st.warning("No brand data available.")
        return

    # Top metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Brands", len(brands))
    col2.metric("Avg Hazard Score", f"{brands['avg_hazard_score'].mean():.1f}")
    high_brands = (brands['max_hazard_flag'] == 'HIGH').sum()
    col3.metric("Brands w/ HIGH Risk", high_brands)

    # Brand ranking chart
    st.subheader("Brand Hazard Rankings")
    sort_by = st.selectbox("Sort by", ['avg_hazard_score', 'max_hazard_score', 'product_count',
                                        'total_carc_products', 'total_repro_products'])
    top_n = st.slider("Show top N brands", 10, min(len(brands), 67), 20)

    top_brands = brands.nlargest(top_n, sort_by)
    fig = px.bar(top_brands.sort_values(sort_by),
                 x=sort_by, y='brand', orientation='h',
                 color='max_hazard_flag',
                 color_discrete_map={'HIGH': '#e74c3c', 'MEDIUM': '#f39c12',
                                     'LOW': '#2ecc71', 'NO_DATA': '#95a5a6'},
                 labels={'brand': 'Brand', sort_by: sort_by.replace('_', ' ').title(),
                         'max_hazard_flag': 'Max Risk'})
    fig.update_layout(margin=dict(t=20, b=20), height=max(400, top_n * 22))
    st.plotly_chart(fig, width='stretch')

    # Detailed table
    st.subheader("Full Brand Data")
    st.dataframe(
        brands.rename(columns={
            'brand': 'Brand', 'company': 'Company', 'product_count': '# Products',
            'avg_hazard_score': 'Avg Score', 'max_hazard_score': 'Max Score',
            'total_repro_products': 'Repro Hazard', 'total_carc_products': 'Carcinogen',
            'max_hazard_flag': 'Risk Level'
        }).drop(columns=['brand_id'], errors='ignore'),
        width='stretch',
        hide_index=True,
    )


def page_categories(data):
    """Category analysis page."""
    st.header("Category Hazard Analysis")

    cats = data["categories"]
    if len(cats) == 0:
        st.warning("No category data available.")
        return

    # Comparison chart
    st.subheader("Category Comparison")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Avg Hazard Score', x=cats['category_raw'], y=cats['avg_hazard_score'],
        marker_color='#3498db'
    ))
    fig.add_trace(go.Bar(
        name='Max Hazard Score', x=cats['category_raw'], y=cats['max_hazard_score'],
        marker_color='#e74c3c'
    ))
    fig.update_layout(barmode='group', xaxis_tickangle=-45,
                      margin=dict(t=20, b=100), height=400)
    st.plotly_chart(fig, width='stretch')

    # Risk breakdown
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("% High Hazard by Category")
        fig2 = px.bar(cats.sort_values('pct_high_hazard'),
                      x='pct_high_hazard', y='category_raw', orientation='h',
                      color='pct_high_hazard', color_continuous_scale='RdYlGn_r',
                      labels={'pct_high_hazard': '% High Hazard', 'category_raw': ''})
        fig2.update_layout(margin=dict(t=20, b=20), showlegend=False, height=300)
        st.plotly_chart(fig2, width='stretch')

    with col_r:
        st.subheader("% Carcinogen by Category")
        fig3 = px.bar(cats.sort_values('pct_carcinogen'),
                      x='pct_carcinogen', y='category_raw', orientation='h',
                      color='pct_carcinogen', color_continuous_scale='Reds',
                      labels={'pct_carcinogen': '% Carcinogen', 'category_raw': ''})
        fig3.update_layout(margin=dict(t=20, b=20), showlegend=False, height=300)
        st.plotly_chart(fig3, width='stretch')

    # Recommendations table
    st.subheader("Category Recommendations")
    st.dataframe(
        cats[['category_raw', 'product_count', 'avg_hazard_score', 'pct_high_hazard', 'recommendation']].rename(columns={
            'category_raw': 'Category', 'product_count': '# Products',
            'avg_hazard_score': 'Avg Score', 'pct_high_hazard': '% High',
            'recommendation': 'Recommendation'
        }),
        width='stretch', hide_index=True
    )


def page_identity(data):
    """Identity resolution coverage page."""
    st.header("Chemical Identity Resolution")

    identity = data["identity"]
    if len(identity) == 0:
        st.warning("No identity data available.")
        return

    total = len(identity)
    matched = identity['canonical_name'].notna().sum()
    rate = matched / total if total > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Ingredient Rows", total)
    col2.metric("Resolved", matched)
    col3.metric("Match Rate", f"{rate:.1%}")

    # By match source
    st.subheader("Resolution by Method")
    source_counts = identity['match_source'].value_counts().reset_index()
    source_counts.columns = ['Method', 'Count']
    fig = px.pie(source_counts, values='Count', names='Method')
    fig.update_layout(margin=dict(t=20, b=20))
    st.plotly_chart(fig, width='stretch')

    # By category
    st.subheader("Match Rate by Category")
    cat_match = identity.groupby('category_raw').agg(
        total=('product_id', 'count'),
        matched=('canonical_name', lambda x: x.notna().sum())
    ).reset_index()
    cat_match['rate'] = (cat_match['matched'] / cat_match['total'] * 100).round(1)
    fig2 = px.bar(cat_match.sort_values('rate'), x='rate', y='category_raw',
                  orientation='h', color='rate', color_continuous_scale='Greens',
                  labels={'rate': 'Match Rate (%)', 'category_raw': 'Category'})
    fig2.update_layout(margin=dict(t=20, b=20), height=300, showlegend=False)
    st.plotly_chart(fig2, width='stretch')

    # Unresolved ingredients
    unresolved = identity[identity['canonical_name'].isna()]
    if len(unresolved) > 0:
        st.subheader(f"Unresolved Ingredients ({len(unresolved)} rows)")
        st.dataframe(
            unresolved[['ingredient_raw', 'casrn', 'match_source']].drop_duplicates().rename(columns={
                'ingredient_raw': 'Ingredient', 'casrn': 'CAS #', 'match_source': 'Status'
            }),
            width='stretch', hide_index=True
        )
    else:
        st.success("All ingredients resolved!")


# ── Main App ──

st.set_page_config(
    page_title="Hair Glue Safety Dashboard",
    page_icon="🧪",
    layout="wide",
)

st.title("Hair Glue Product Safety Dashboard")
st.caption("Interactive analysis of hair-glue and weaving-adhesive product chemical hazards (CSCP data)")

data = load_data()

pages = {
    "Overview": page_overview,
    "Products": page_products,
    "Chemicals": page_chemicals,
    "Brands": page_brands,
    "Categories": page_categories,
    "Identity Resolution": page_identity,
}

page = st.sidebar.radio("Navigation", list(pages.keys()))
st.sidebar.divider()
st.sidebar.markdown("**Data Sources**")
st.sidebar.markdown("- CSCP Cosmetics Database")
st.sidebar.markdown("- PubChem GHS Classifications")
st.sidebar.markdown("- PubChem Chemical Identity")
st.sidebar.divider()
st.sidebar.caption(f"Products: {len(data['products'])} | Chemicals: {len(data['ref_chemicals'])}")

try:
    pages[page](data)
except Exception as e:
    # Don't swallow Streamlit's internal control-flow exceptions
    # (RerunException, StopException) — they must propagate or the page goes blank.
    if "Rerun" in type(e).__name__ or "Stop" in type(e).__name__:
        raise
    st.error(f"Error loading page: {e}")
    import traceback
    st.code(traceback.format_exc())
