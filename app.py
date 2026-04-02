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
import requests
from pathlib import Path

WAREHOUSE = Path("warehouse")

# ── Plain-language term glossary ──────────────────────────────────────────────
GLOSSARY = {
    "Danger Score": "A number from 0 to 100 that shows how risky a product is based on its chemicals. Higher = more dangerous.",
    "Danger Level": "A quick label (HIGH, MEDIUM, LOW) that tells you at a glance how risky a product is.",
    "Cancer-Causing Chemical (Carcinogen)": "A chemical that can increase the risk of cancer with long-term exposure.",
    "Reproductive Hazard": "A chemical that can harm the ability to have children or can hurt an unborn baby.",
    "Organ Damage Chemical": "A chemical that can injure organs (like the liver, kidneys, or lungs) when used repeatedly.",
    "GHS": "Global Harmonized System — an international system for labeling how dangerous chemicals are.",
    "Warning Strength": "Either 'DANGER' (very serious hazard) or 'WARNING' (moderate hazard) printed on product labels.",
    "Hazard Statement Code (H-Code)": "A short code (like H350) that stands for a specific health or safety warning, used worldwide.",
    "Chemical ID Number (CAS #)": "A unique number given to every chemical — like a social security number for chemicals.",
    "Official Chemical Name": "The standardized, internationally recognized name for a chemical.",
    "Chemical Name Matching": "The process of figuring out the real identity of an ingredient listed on a product label.",
    "Product Type / Category": "The type of product (e.g., Hair Extensions, Nail Products, Skin Care).",
}


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
        "regulatory": "ref_chemicals_regulatory.parquet",
        "comptox": "ref_chemicals_comptox.parquet",
        "toxcast": "ref_chemicals_toxcast.parquet",
        "chemexpo": "ref_chemicals_chemexpo.parquet",
    }
    for key, fname in files.items():
        path = WAREHOUSE / fname
        if path.exists():
            data[key] = pd.read_parquet(path)
        else:
            data[key] = pd.DataFrame()
    return data


# ── Helper: plain language for GHS hazard class codes ────────────────────────
def plain_hazard_class(raw: str) -> str:
    """Convert technical GHS class codes to 8th-grade-readable descriptions."""
    if not raw or pd.isna(raw):
        return raw
    replacements = {
        "Carc": "Cancer-Causing (Carcinogen)",
        "Repr": "Reproductive Hazard",
        "Repr/Dev": "Reproductive/Developmental Hazard",
        "STOT-RE": "Organ Damage from Repeated Exposure",
        "STOT-SE": "Organ Damage from Single Exposure",
        "Acute Tox": "Acute Poisoning",
        "Skin Corr": "Skin Burns/Corrosion",
        "Skin Irrit": "Skin Irritation",
        "Eye Dam": "Serious Eye Damage",
        "Eye Irrit": "Eye Irritation",
        "Resp Sens": "Respiratory Sensitizer (Causes Allergies in Lungs)",
        "Skin Sens": "Skin Sensitizer (Causes Skin Allergies)",
        "Muta": "DNA-Damaging (Mutagenic)",
        "Flam": "Flammable",
        "Ox": "Oxidizing",
        "Asp Tox": "Aspiration Hazard (Dangerous if Swallowed into Lungs)",
        "Aquat": "Harmful to Aquatic Life",
    }
    result = raw
    for code, plain in replacements.items():
        result = result.replace(code, plain)
    return result


def page_overview(data):
    """Project overview / executive summary page."""
    st.header("Overview")

    st.info(
        "**What this page shows:** A high-level snapshot of all hair-glue and weaving-adhesive products "
        "in our database. You can see how many products exist, what fraction contain dangerous chemicals, "
        "and which product types (categories) are riskiest overall. Use this page to get a quick "
        "sense of the big picture before diving into details."
    )

    products = data["products"]
    ingredients = data["ingredients"]
    identity = data["identity"]
    ph = data["product_hazards"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Products", len(products),
                help="Total number of unique hair-glue/weave products found in the CSCP database.")
    col2.metric("Unique Chemicals", len(ingredients),
                help="Total number of distinct chemical ingredients across all products.")
    if len(identity) > 0 and 'canonical_name' in identity.columns:
        match_rate = identity['canonical_name'].notna().mean()
        col3.metric("Chemical ID Match Rate", f"{match_rate:.0%}",
                    help="Percentage of ingredient listings we were able to match to an official chemical name.")
    else:
        col3.metric("Chemical ID Match Rate", "N/A")

    if len(ph) > 0 and 'hazard_flag' in ph.columns:
        high_pct = (ph['hazard_flag'] == 'HIGH').mean()
        col4.metric("HIGH Danger Products", f"{high_pct:.0%}",
                    help="Percentage of products rated HIGH danger — meaning they contain chemicals with serious health warnings.")

    st.divider()

    # Hazard distribution
    if len(ph) > 0 and 'hazard_flag' in ph.columns:
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Danger Level Breakdown")
            st.caption(
                "How many products fall into each danger category. "
                "RED = HIGH danger, ORANGE = MEDIUM danger, GREEN = LOW danger, GRAY = not enough data."
            )
            flag_counts = ph['hazard_flag'].value_counts().reset_index()
            flag_counts.columns = ['Danger Level', 'Number of Products']
            # Map to plain language labels for display
            label_map = {'HIGH': 'HIGH Danger', 'MEDIUM': 'MEDIUM Danger',
                         'LOW': 'LOW Danger', 'NO_DATA': 'Not Enough Data'}
            flag_counts['Danger Level Label'] = flag_counts['Danger Level'].map(label_map).fillna(flag_counts['Danger Level'])
            color_map = {'HIGH': '#e74c3c', 'MEDIUM': '#f39c12', 'LOW': '#2ecc71', 'NO_DATA': '#95a5a6'}
            fig = px.pie(
                flag_counts,
                values='Number of Products',
                names='Danger Level Label',
                color='Danger Level',
                color_discrete_map=color_map,
                hole=0.35,
            )
            fig.update_traces(textinfo='percent+label')
            fig.update_layout(
                margin=dict(t=30, b=30),
                legend=dict(
                    title="Danger Level",
                    orientation="v",
                    x=1.0,
                    y=0.5,
                ),
                showlegend=True,
            )
            st.plotly_chart(fig, width='stretch')

        with col_right:
            st.subheader("Danger Score Distribution")
            st.caption(
                "Each bar shows how many products have a danger score in that range. "
                "Scores go from 0 (safe) to 100 (very dangerous). "
                "Taller bars on the right mean more highly dangerous products."
            )
            fig = px.histogram(
                ph, x='hazard_score', nbins=20,
                color_discrete_sequence=['#3498db'],
                labels={'hazard_score': 'Danger Score (0–100)', 'count': 'Number of Products'},
            )
            fig.update_layout(
                xaxis_title="Danger Score (0 = safe, 100 = very dangerous)",
                yaxis_title="Number of Products",
                margin=dict(t=30, b=30),
                showlegend=False,
            )
            st.plotly_chart(fig, width='stretch')

    # Category analysis
    cats = data["categories"]
    if len(cats) > 0:
        st.subheader("Danger Score by Product Type")
        st.caption(
            "Each bar shows the average danger score for that product type. "
            "Darker red bars mean a higher percentage of products in that type are rated HIGH danger. "
            "Longer bars = higher average danger score."
        )
        fig = px.bar(
            cats.sort_values('avg_hazard_score', ascending=True),
            x='avg_hazard_score', y='category_raw', orientation='h',
            color='pct_high_hazard',
            color_continuous_scale='RdYlGn_r',
            labels={
                'avg_hazard_score': 'Average Danger Score (0–100)',
                'category_raw': 'Product Type',
                'pct_high_hazard': '% Products Rated HIGH Danger',
            },
        )
        fig.update_layout(
            margin=dict(t=20, b=20),
            height=350,
            coloraxis_colorbar=dict(
                title="% HIGH Danger<br>Products",
                ticksuffix="%",
            ),
        )
        st.plotly_chart(fig, width='stretch')

    # Quick glossary
    with st.expander("Glossary — What do these terms mean?"):
        for term, definition in GLOSSARY.items():
            st.markdown(f"**{term}:** {definition}")


def page_products(data):
    """Product browser with search and hazard details."""
    st.header("Product Browser")

    st.info(
        "**What this page shows:** A searchable list of all hair-glue and weaving-adhesive products. "
        "You can filter by product type or danger level, then click on any product to see exactly "
        "which chemicals it contains and how dangerous each one is. "
        "Use this page to research a specific product you own or are thinking of buying."
    )

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
        selected_cat = st.selectbox("Product Type", categories)
    with col3:
        if 'hazard_flag' in merged.columns:
            flags = ['All'] + sorted(merged['hazard_flag'].dropna().unique().tolist())
            selected_flag = st.selectbox("Danger Level", flags,
                                         help="HIGH = serious hazards present, MEDIUM = moderate concerns, LOW = few or minor hazards")
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
            'product_name': 'Product Name',
            'brand': 'Brand',
            'company': 'Company',
            'category_raw': 'Product Type',
            'hazard_score': 'Danger Score (0–100)',
            'hazard_flag': 'Danger Level',
            'num_ingredients': '# Chemicals Listed',
        }),
        width='stretch',
        height=400,
    )

    # Product detail
    st.divider()
    st.subheader("Product Detail View")
    st.caption("Select a product below to see its full chemical ingredient list and hazard details.")
    product_names = sorted(filtered['product_name'].tolist())
    if product_names:
        selected_product = st.selectbox("Select a product", product_names)
        prod_row = merged[merged['product_name'] == selected_product].iloc[0]
        pid = prod_row['product_id']

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Brand:** {prod_row.get('brand', 'N/A')}")
            st.markdown(f"**Company:** {prod_row.get('company', 'N/A')}")
            st.markdown(f"**Product Type:** {prod_row.get('category_raw', 'N/A')}")
        with col_b:
            if 'hazard_score' in prod_row:
                score = prod_row.get('hazard_score', 'N/A')
                flag = prod_row.get('hazard_flag', 'N/A')
                flag_color = {'HIGH': '🔴', 'MEDIUM': '🟠', 'LOW': '🟢', 'NO_DATA': '⚫'}.get(str(flag), '')
                st.markdown(f"**Danger Score (0–100):** {score}")
                st.markdown(f"**Danger Level:** {flag_color} {flag}")
                if 'carcinogen_count' in prod_row:
                    carc_count = int(prod_row.get('carcinogen_count', 0))
                    st.markdown(
                        f"**Cancer-Causing Chemicals (Carcinogens):** {carc_count}",
                        help="Number of ingredients in this product linked to cancer risk."
                    )
                if 'reproductive_hazard_ingredient_count' in prod_row:
                    repro_count = int(prod_row.get('reproductive_hazard_ingredient_count', 0))
                    st.markdown(f"**Reproductive Hazard Chemicals:** {repro_count}",
                                help="Number of ingredients that may affect fertility or harm an unborn baby.")

        # Show ingredients for this product
        if len(identity) > 0:
            prod_ingredients = identity[identity['product_id'] == pid]
            if len(prod_ingredients) > 0:
                st.markdown("**Chemicals in this Product:**")
                ing_display = prod_ingredients[['ingredient_raw', 'casrn', 'canonical_name', 'match_source']].copy()
                source_plain = {
                    'exact_match': 'Exact Name Match',
                    'fuzzy_match': 'Close Name Match',
                    'pubchem_cid_name': 'Found via PubChem Database',
                    'fallback_no_match': 'Could Not Identify',
                }
                ing_display['match_source'] = ing_display['match_source'].map(source_plain).fillna(ing_display['match_source'])
                ing_display.columns = ['Ingredient (As Listed on Label)', 'Chemical ID (CAS #)', 'Official Chemical Name', 'How We Identified It']
                st.dataframe(ing_display, width='stretch', hide_index=True)


def page_chemicals(data):
    """Chemical search and hazard profile viewer."""
    st.header("Chemical Database")

    st.info(
        "**What this page shows:** A searchable database of every chemical found in hair-glue products. "
        "You can look up any chemical by its name or ID number (CAS #) to see what kind of health "
        "hazards it carries. Select a chemical to see which products contain it and get its full "
        "safety profile. This page is useful for parents, consumers, or researchers checking whether "
        "a specific ingredient is dangerous."
    )

    hazard_ref = data["hazard_ref"]
    identity = data["identity"]
    ref = data["ref_chemicals"]

    if len(ref) == 0:
        st.warning("No chemical reference data available.")
        return

    # Search
    search = st.text_input("Search chemicals", placeholder="Chemical ID (CAS #) or chemical name...")

    # Build chemical view
    chem_view = ref.copy()
    if len(hazard_ref) > 0:
        haz_dedup = hazard_ref.sort_values('canonical_name', na_position='last').drop_duplicates(
            subset='casrn', keep='first'
        )
        merge_cols = ['casrn']
        haz_cols = [c for c in ['ghs_hazard_class', 'ghs_signal_word', 'h_codes'] if c in haz_dedup.columns]
        chem_view = chem_view.merge(haz_dedup[merge_cols + haz_cols], on='casrn', how='left')

    # Apply plain-language hazard classes
    if 'ghs_hazard_class' in chem_view.columns:
        chem_view['ghs_hazard_class_plain'] = chem_view['ghs_hazard_class'].apply(plain_hazard_class)

    if search:
        mask = chem_view.apply(
            lambda r: search.lower() in str(r.get('canonical_name', '')).lower()
                      or search.lower() in str(r.get('casrn', '')).lower(),
            axis=1
        )
        chem_view = chem_view[mask]

    st.caption(f"Showing {len(chem_view)} chemicals")

    display_cols = ['casrn', 'canonical_name', 'source']
    plain_col = 'ghs_hazard_class_plain' if 'ghs_hazard_class_plain' in chem_view.columns else None
    if plain_col:
        display_cols.append(plain_col)
    if 'ghs_signal_word' in chem_view.columns:
        display_cols.append('ghs_signal_word')

    rename_map = {
        'casrn': 'Chemical ID (CAS #)',
        'canonical_name': 'Official Chemical Name',
        'source': 'Data Source',
        'ghs_signal_word': 'Warning Strength (DANGER / WARNING)',
    }
    if plain_col:
        rename_map[plain_col] = 'Type of Hazard'

    st.dataframe(
        chem_view[[c for c in display_cols if c in chem_view.columns]].rename(columns=rename_map),
        width='stretch',
        hide_index=True,
    )

    # ToxCast + ChemExpo summary table
    toxcast = data.get("toxcast", pd.DataFrame())
    chemexpo = data.get("chemexpo", pd.DataFrame())
    regulatory = data.get("regulatory", pd.DataFrame())

    has_epa = (
        len(toxcast) > 0
        or len(chemexpo) > 0
    )
    if has_epa:
        st.divider()
        st.subheader("EPA ToxCast & ChemExpo Data")
        st.caption(
            "ToxCast = how many EPA lab tests found this chemical biologically active. "
            "ChemExpo = how many consumer products nationally contain this chemical."
        )
        epa_view = pd.DataFrame()
        if len(regulatory) > 0 and "casrn" in regulatory.columns:
            epa_view = regulatory[["casrn"]].copy()
            if "canonical_name" in regulatory.columns:
                epa_view["canonical_name"] = regulatory["canonical_name"]
        if len(toxcast) > 0 and "casrn" in toxcast.columns:
            tox_cols = [c for c in ["casrn", "assays_tested", "assays_active", "activity_score"] if c in toxcast.columns]
            epa_view = epa_view.merge(toxcast[tox_cols], on="casrn", how="left") if len(epa_view) > 0 else toxcast[tox_cols].copy()
        if len(chemexpo) > 0 and "casrn" in chemexpo.columns:
            expo_cols = [c for c in ["casrn", "national_product_count", "functional_uses"] if c in chemexpo.columns]
            epa_view = epa_view.merge(chemexpo[expo_cols], on="casrn", how="left") if len(epa_view) > 0 else chemexpo[expo_cols].copy()

        if len(epa_view) > 0:
            rename = {
                "casrn": "Chemical ID (CAS #)",
                "canonical_name": "Chemical Name",
                "assays_tested": "ToxCast: Assays Tested",
                "assays_active": "ToxCast: Active Hits",
                "activity_score": "ToxCast Activity Score (0–1)",
                "national_product_count": "ChemExpo: Products Nationally",
                "functional_uses": "ChemExpo: Functional Uses",
            }
            st.dataframe(
                epa_view.rename(columns=rename),
                width="stretch",
                hide_index=True,
            )

    # Detail view
    if len(hazard_ref) > 0:
        st.divider()
        st.subheader("Chemical Safety Profile")
        st.caption(
            "Select a chemical below to see its full safety profile — what hazards it poses, "
            "how severe the warning is, and which products in our database contain it."
        )
        chem_names = chem_view['canonical_name'].dropna().unique().tolist()
        if chem_names:
            selected_chem = st.selectbox("Select chemical", sorted(chem_names))
            chem_row = chem_view[chem_view['canonical_name'] == selected_chem].iloc[0]
            casrn = chem_row.get('casrn')

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown(f"**Chemical ID (CAS #):** {casrn or 'N/A'}")
                signal = chem_row.get('ghs_signal_word', 'N/A')
                signal_icon = '⚠️ DANGER' if str(signal).upper() == 'DANGER' else ('⚡ WARNING' if str(signal).upper() == 'WARNING' else str(signal))
                st.markdown(f"**Warning Strength:** {signal_icon}")
                st.caption(
                    "DANGER = most serious hazard level (can cause severe injury or death). "
                    "WARNING = moderate hazard (harmful but less immediately severe)."
                )
            with col_b:
                classes = chem_row.get('ghs_hazard_class', '')
                if classes and not pd.isna(classes):
                    st.markdown("**Types of Hazard this Chemical Poses:**")
                    for cls in str(classes).split('|'):
                        plain = plain_hazard_class(cls.strip())
                        st.markdown(f"- {plain}")

            # Find products containing this chemical
            if len(identity) > 0 and casrn:
                products_with = identity[identity['casrn'] == casrn]
                if len(products_with) > 0:
                    prods = data["products"]
                    product_list = prods[prods['product_id'].isin(products_with['product_id'])]
                    st.markdown(f"**Found in {len(product_list)} products:**")
                    st.dataframe(
                        product_list[['product_name', 'brand', 'category_raw']].rename(columns={
                            'product_name': 'Product Name', 'brand': 'Brand', 'category_raw': 'Product Type'
                        }),
                        width='stretch', hide_index=True
                    )


def page_brands(data):
    """Brand risk analysis page."""
    st.header("Brand Danger Rankings")

    st.info(
        "**What this page shows:** A ranking of all hair-glue brands by how dangerous their products are. "
        "You can sort brands by their average danger score, highest danger score, how many products "
        "they make, or how many of their products contain cancer-causing or reproductive-harm chemicals. "
        "Use this page to compare brands and identify which companies sell the riskiest products."
    )

    brands = data["brands"]
    if len(brands) == 0:
        st.warning("No brand data available.")
        return

    # Top metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Brands", len(brands))
    col2.metric("Average Danger Score", f"{brands['avg_hazard_score'].mean():.1f}",
                help="The average danger score (0–100) across all brands.")
    high_brands = (brands['max_hazard_flag'] == 'HIGH').sum()
    col3.metric("Brands with HIGH Danger Products", high_brands,
                help="Number of brands that have at least one product rated HIGH danger.")

    # Sort options in plain language
    sort_options = {
        'avg_hazard_score': 'Average Danger Score',
        'max_hazard_score': 'Highest Danger Score (any product)',
        'product_count': 'Number of Products',
        'total_carc_products': 'Products with Cancer-Causing Chemicals',
        'total_repro_products': 'Products with Reproductive Hazard Chemicals',
    }

    # Brand ranking chart
    st.subheader("Brand Ranking Chart")
    st.caption(
        "Each bar represents one brand. Bar length = the selected metric. "
        "Color shows the brand's worst danger level: RED = HIGH, ORANGE = MEDIUM, GREEN = LOW."
    )
    sort_label = st.selectbox("Rank brands by", list(sort_options.values()))
    sort_by = [k for k, v in sort_options.items() if v == sort_label][0]
    top_n = st.slider("Show top N brands", 10, min(len(brands), 67), 20)

    top_brands = brands.nlargest(top_n, sort_by)
    label_map_flag = {'HIGH': 'HIGH Danger', 'MEDIUM': 'MEDIUM Danger', 'LOW': 'LOW Danger', 'NO_DATA': 'Not Enough Data'}
    top_brands = top_brands.copy()
    top_brands['Danger Level'] = top_brands['max_hazard_flag'].map(label_map_flag).fillna(top_brands['max_hazard_flag'])

    fig = px.bar(
        top_brands.sort_values(sort_by),
        x=sort_by, y='brand', orientation='h',
        color='Danger Level',
        color_discrete_map={
            'HIGH Danger': '#e74c3c',
            'MEDIUM Danger': '#f39c12',
            'LOW Danger': '#2ecc71',
            'Not Enough Data': '#95a5a6',
        },
        labels={'brand': 'Brand', sort_by: sort_label, 'Danger Level': 'Worst Danger Level'},
    )
    fig.update_layout(
        margin=dict(t=20, b=20),
        height=max(400, top_n * 22),
        legend=dict(
            title="Worst Danger Level<br>(any product by this brand)",
            orientation="v",
            x=1.0,
            y=0.5,
        ),
    )
    st.plotly_chart(fig, width='stretch')

    # Detailed table
    st.subheader("Full Brand Data Table")
    st.dataframe(
        brands.rename(columns={
            'brand': 'Brand',
            'company': 'Company',
            'product_count': '# Products',
            'avg_hazard_score': 'Avg Danger Score',
            'max_hazard_score': 'Highest Danger Score',
            'total_repro_products': 'Products w/ Reproductive Hazard Chemicals',
            'total_carc_products': 'Products w/ Cancer-Causing Chemicals',
            'max_hazard_flag': 'Worst Danger Level',
        }).drop(columns=['brand_id'], errors='ignore'),
        width='stretch',
        hide_index=True,
    )


def page_categories(data):
    """Category analysis page."""
    st.header("Product Type Danger Analysis")

    st.info(
        "**What this page shows:** A comparison of danger levels across different types of hair products "
        "(called 'categories'). For example, you can compare how dangerous hair bonding glues are versus "
        "wig adhesives versus weave products. Charts show average and peak danger scores, how many products "
        "are rated HIGH danger, and what percentage contain cancer-causing chemicals. "
        "Use this page to understand which product types are most concerning overall."
    )

    cats = data["categories"]
    if len(cats) == 0:
        st.warning("No category data available.")
        return

    # Comparison chart
    st.subheader("Average vs. Highest Danger Score by Product Type")
    st.caption(
        "Blue bars show the average danger score for each product type. "
        "Red bars show the single highest danger score found in that product type. "
        "A big gap between blue and red means most products are okay, but at least one is very dangerous."
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name='Average Danger Score',
        x=cats['category_raw'], y=cats['avg_hazard_score'],
        marker_color='#3498db',
    ))
    fig.add_trace(go.Bar(
        name='Highest Danger Score (worst product)',
        x=cats['category_raw'], y=cats['max_hazard_score'],
        marker_color='#e74c3c',
    ))
    fig.update_layout(
        barmode='group',
        xaxis_tickangle=-45,
        xaxis_title='Product Type',
        yaxis_title='Danger Score (0–100)',
        margin=dict(t=20, b=120),
        height=420,
        legend=dict(
            title="Score Type",
            orientation="h",
            x=0.01,
            y=1.05,
        ),
    )
    st.plotly_chart(fig, width='stretch')

    # Risk breakdown
    col_l, col_r = st.columns(2)
    with col_l:
        st.subheader("% of Products Rated HIGH Danger")
        st.caption(
            "Longer bar = higher percentage of products in that type rated HIGH danger. "
            "Darker red color = more dangerous product type."
        )
        fig2 = px.bar(
            cats.sort_values('pct_high_hazard'),
            x='pct_high_hazard', y='category_raw', orientation='h',
            color='pct_high_hazard', color_continuous_scale='RdYlGn_r',
            labels={'pct_high_hazard': '% Products Rated HIGH Danger', 'category_raw': 'Product Type'},
        )
        fig2.update_layout(
            margin=dict(t=20, b=20),
            showlegend=False,
            height=320,
            coloraxis_colorbar=dict(title="% HIGH Danger", ticksuffix="%"),
        )
        st.plotly_chart(fig2, width='stretch')

    with col_r:
        st.subheader("% of Products with Cancer-Causing Chemicals")
        st.caption(
            "Longer bar = higher percentage of products in that type containing at least one "
            "cancer-causing chemical (carcinogen). Darker red = more concern."
        )
        fig3 = px.bar(
            cats.sort_values('pct_carcinogen'),
            x='pct_carcinogen', y='category_raw', orientation='h',
            color='pct_carcinogen', color_continuous_scale='Reds',
            labels={'pct_carcinogen': '% Products with Cancer-Causing Chemicals', 'category_raw': 'Product Type'},
        )
        fig3.update_layout(
            margin=dict(t=20, b=20),
            showlegend=False,
            height=320,
            coloraxis_colorbar=dict(title="% w/ Carcinogen", ticksuffix="%"),
        )
        st.plotly_chart(fig3, width='stretch')

    # Recommendations table
    st.subheader("Safety Recommendations by Product Type")
    st.caption("A summary table with safety advice for each product type based on our analysis.")
    st.dataframe(
        cats[['category_raw', 'product_count', 'avg_hazard_score', 'pct_high_hazard', 'recommendation']].rename(columns={
            'category_raw': 'Product Type',
            'product_count': '# Products',
            'avg_hazard_score': 'Avg Danger Score',
            'pct_high_hazard': '% HIGH Danger',
            'recommendation': 'Safety Recommendation',
        }),
        width='stretch', hide_index=True
    )


def page_identity(data):
    """Chemical Name Matching coverage page."""
    st.header("Chemical Name Matching")

    st.info(
        "**What this page shows:** How well we were able to identify the actual chemicals in each product. "
        "Product labels often list ingredients by nicknames, abbreviations, or vague names (like 'fragrance'). "
        "This page shows what percentage of those ingredient names we successfully matched to an official "
        "chemical name in a scientific database — and which ones we couldn't identify. "
        "Higher match rates mean our hazard analysis is more complete and reliable."
    )

    identity = data["identity"]
    if len(identity) == 0:
        st.warning("No identity data available.")
        return

    total = len(identity)
    matched = identity['canonical_name'].notna().sum()
    rate = matched / total if total > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Ingredient Listings", total,
                help="Total number of ingredient entries across all products.")
    col2.metric("Successfully Identified", matched,
                help="Number of ingredient listings matched to an official chemical name.")
    col3.metric("Match Rate", f"{rate:.1%}",
                help="Percentage of ingredient listings we were able to identify.")

    # By match source
    st.subheader("How Were Chemicals Identified?")
    st.caption(
        "This chart shows which method was used to identify each chemical. "
        "Larger slices = more chemicals identified using that method."
    )
    source_plain_map = {
        'exact_match': 'Exact Name Match',
        'fuzzy_match': 'Close Name Match (Fuzzy)',
        'pubchem_cid_name': 'Found via PubChem Database',
        'fallback_no_match': 'Could Not Be Identified',
        None: 'Unknown',
    }
    source_counts = identity['match_source'].map(source_plain_map).fillna(identity['match_source']).value_counts().reset_index()
    source_counts.columns = ['Identification Method', 'Count']
    fig = px.pie(
        source_counts,
        values='Count',
        names='Identification Method',
        hole=0.3,
    )
    fig.update_traces(textinfo='percent+label')
    fig.update_layout(
        margin=dict(t=30, b=30),
        legend=dict(title="Method", orientation="v", x=1.0, y=0.5),
        showlegend=True,
    )
    st.plotly_chart(fig, width='stretch')

    # By category
    st.subheader("Match Rate by Product Type")
    st.caption(
        "This chart shows what percentage of chemicals in each product type were successfully identified. "
        "Longer bar / darker green = better identification rate for that product type."
    )
    cat_match = identity.groupby('category_raw').agg(
        total=('product_id', 'count'),
        matched=('canonical_name', lambda x: x.notna().sum())
    ).reset_index()
    cat_match['Match Rate (%)'] = (cat_match['matched'] / cat_match['total'] * 100).round(1)
    fig2 = px.bar(
        cat_match.sort_values('Match Rate (%)'),
        x='Match Rate (%)', y='category_raw',
        orientation='h', color='Match Rate (%)', color_continuous_scale='Greens',
        labels={'Match Rate (%)': 'Chemical Identification Rate (%)', 'category_raw': 'Product Type'},
    )
    fig2.update_layout(
        margin=dict(t=20, b=20), height=320,
        showlegend=False,
        coloraxis_colorbar=dict(title="Match Rate", ticksuffix="%"),
    )
    st.plotly_chart(fig2, width='stretch')

    # Unresolved ingredients
    unresolved = identity[identity['canonical_name'].isna()]
    if len(unresolved) > 0:
        st.subheader(f"Chemicals We Could NOT Identify ({len(unresolved)} entries)")
        st.caption(
            "These ingredient listings could not be matched to an official chemical name. "
            "This means we could not assess their safety — which is itself a concern."
        )
        st.dataframe(
            unresolved[['ingredient_raw', 'casrn', 'match_source']].drop_duplicates().rename(columns={
                'ingredient_raw': 'Ingredient (As Listed on Label)',
                'casrn': 'Chemical ID (CAS #) if available',
                'match_source': 'Status',
            }),
            width='stretch', hide_index=True
        )
    else:
        st.success("All chemicals were successfully identified!")


def page_epa_tools(data):
    """EPA Research Tools integration guide and live demo."""
    st.header("EPA Chemical Research Tools")

    st.info(
        "**What this page shows:** The U.S. Environmental Protection Agency (EPA) has built a suite of "
        "powerful free tools for researching chemical safety. This page explains each tool, shows how it "
        "relates to this dashboard, and demonstrates live data lookups for chemicals in our database. "
        "These tools together form one of the most complete public chemical safety systems in the world."
    )

    st.divider()

    # ── Tool Overview Cards ──────────────────────────────────────────────────
    st.subheader("The 5 EPA Tools — What Each One Does")

    with st.expander("1. ToxCast — Lab Test Results for Thousands of Chemicals", expanded=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
**What it is:** ToxCast (short for Toxicity Forecasting) is an EPA program that tested over
**10,000 chemicals** in hundreds of computer-based lab tests to predict how they might affect
the human body — things like hormone disruption, cell damage, and organ toxicity.

**Why it matters for this dashboard:** Many chemicals in hair-glue products haven't been
tested in animals or people, but ToxCast has run quick computer tests on them. We can pull
those test results to fill in safety gaps.

**What data we can pull:**
- How many ToxCast biological tests a chemical "hit" (triggered a response in)
- Which body systems or hormones might be disrupted
- A "ToxCast Score" that summarizes overall biological activity

**Plain language:** Think of ToxCast as a massive science fair where thousands of chemicals
were tested against hundreds of different body sensors to see which ones caused a reaction.
            """)
        with col2:
            st.markdown("**Key Facts:**")
            st.metric("Chemicals Tested", "10,000+")
            st.metric("Lab Tests (Assays)", "1,500+")
            st.metric("Data Points", "~700 million")

    with st.expander("2. GenRA Tool — Predicting Toxicity by Comparison"):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
**What it is:** GenRA (Generalized Read-Across) is a tool that estimates how toxic an
**untested chemical** is by comparing it to *similar chemicals that have been tested*.
This is like saying "this new chemical looks a lot like formaldehyde, so it might have
similar risks."

**Why it matters for this dashboard:** Many hair-glue chemicals have almost no safety data.
GenRA lets us make educated predictions by finding their "chemical cousins" that ARE tested.

**What data we can pull:**
- A predicted toxicity level for chemicals with little existing data
- A list of "neighbor chemicals" that are structurally similar
- Confidence scores for the predictions

**Plain language:** Imagine you've never tasted a new fruit, but you know it looks and smells
almost exactly like a mango. You'd predict it tastes like mango. GenRA does the same thing,
but for chemical safety.
            """)
        with col2:
            st.markdown("**Key Facts:**")
            st.metric("Approach", "Read-Across")
            st.metric("Useful For", "Data gaps")

    with st.expander("3. CompTox Chemicals Dashboard — Chemical Info One-Stop Shop"):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
**What it is:** The CompTox Chemicals Dashboard is the EPA's central database for chemical
information. Every chemical gets a unique EPA ID called a **DTXSID** (similar to a CAS # but
from the EPA). The dashboard brings together structure, physical properties, toxicity data,
exposure data, and regulatory status all in one place.

**Why it matters for this dashboard:** We already fetch DTXSID numbers for chemicals in our
pipeline. With DTXSID we can pull structure images, predicted properties, bioactivity data,
and regulatory flags directly from the CompTox API.

**What data we can pull via API:**
- Chemical structure (2D image, SMILES, InChI)
- Predicted physical properties (melting point, solubility)
- TSCA listing (is it on the EPA's Toxic Substances list?)
- Predicted toxicity values (acute, chronic)
- Link to ToxCast and other EPA data

**Plain language:** Think of CompTox as the Wikipedia of chemicals — it pulls together
everything known about a chemical into one clean page, and it's built and maintained by the EPA.
            """)
        with col2:
            st.markdown("**Key Facts:**")
            st.metric("Chemicals in Database", "875,000+")
            st.metric("Our Integration", "Via DTXSID")

    with st.expander("4. ChemExpo Knowledgebase — Where Chemicals Appear in Products"):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
**What it is:** ChemExpo is the EPA's database of **which chemicals appear in which consumer
products** — exactly like what this dashboard tracks, but at a national scale. It covers
cosmetics, cleaning products, food packaging, and more, pulling data from ingredient lists,
safety data sheets, and product databases.

**Why it matters for this dashboard:** ChemExpo is essentially a national-scale version of
what we're doing — tracking chemical exposures in cosmetic products. We can look up our
chemicals in ChemExpo to see:
- How common is this chemical in hair products nationally?
- What is the estimated exposure level for consumers?
- Are other product categories also using this chemical?

**What data we can pull via API:**
- Product categories where a chemical appears
- Estimated consumer exposure levels
- Functional use (e.g., preservative, fragrance, solvent)

**Plain language:** ChemExpo is like a national ingredient tracker — it tells you "this
preservative shows up in 3,000 different products" or "your typical exposure to formaldehyde
from hair products is X micrograms per day."
            """)
        with col2:
            st.markdown("**Key Facts:**")
            st.metric("Products Tracked", "75,000+")
            st.metric("Relevant to Us", "Cosmetics data")

    with st.expander("5. Cheminformatics Modules — Computer Analysis of Chemical Structure"):
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
**What it is:** The EPA's Cheminformatics Modules are a set of computer tools that analyze
the molecular structure of chemicals to predict their properties and hazards. They use
**QSAR models** (Quantitative Structure–Activity Relationship), which are machine learning
models trained on known chemical data.

**Why it matters for this dashboard:** For chemicals in hair-glue products that have no
safety testing at all, cheminformatics can make predictions just from the chemical's
structure. We can predict skin absorption, bioaccumulation, and chronic toxicity.

**What data we can pull:**
- Predicted skin penetration (does it absorb through skin?)
- Predicted endocrine disruption (does it mess with hormones?)
- Predicted carcinogenicity (from structure alone)
- OPERA models: 20+ property predictions

**Plain language:** Like a doctor who can diagnose a disease from an X-ray without running
blood tests, cheminformatics reads a chemical's "molecular shape" and predicts how it will
behave in your body.
            """)
        with col2:
            st.markdown("**Key Facts:**")
            st.metric("OPERA Models", "20+")
            st.metric("Input needed", "SMILES/DTXSID")

    st.divider()

    # ── Warehouse Data Summary ────────────────────────────────────────────────
    comptox = data.get("comptox", pd.DataFrame())
    toxcast = data.get("toxcast", pd.DataFrame())
    chemexpo = data.get("chemexpo", pd.DataFrame())

    has_m31_data = len(comptox) > 0 or len(toxcast) > 0 or len(chemexpo) > 0

    if has_m31_data:
        st.subheader("M3.1 EPA Data Already in Warehouse")
        col1, col2, col3 = st.columns(3)
        col1.metric(
            "CompTox Chemicals",
            len(comptox[comptox["preferred_name"].notna()]) if len(comptox) > 0 else 0,
            help="Chemicals with structure data from CompTox."
        )
        col2.metric(
            "ToxCast Active Chemicals",
            int((toxcast["assays_active"] > 0).sum()) if len(toxcast) > 0 else 0,
            help="Chemicals that triggered at least one ToxCast bioassay."
        )
        col3.metric(
            "ChemExpo: Found Nationally",
            int((chemexpo["national_product_count"] > 0).sum()) if len(chemexpo) > 0 else 0,
            help="Chemicals found in consumer products in the ChemExpo database."
        )

        if len(toxcast) > 0 and "activity_score" in toxcast.columns:
            st.subheader("ToxCast Activity Scores for Our Chemicals")
            st.caption(
                "Activity Score = fraction of lab tests where this chemical triggered a biological response. "
                "Higher = more biologically active = more concern."
            )
            tox_display = toxcast[toxcast["assays_tested"] > 0].sort_values(
                "activity_score", ascending=False
            )
            if len(tox_display) > 0:
                fig = px.bar(
                    tox_display,
                    x="casrn",
                    y="activity_score",
                    labels={
                        "casrn": "Chemical ID (CAS #)",
                        "activity_score": "ToxCast Activity Score (0 = no hits, 1 = all hits)",
                    },
                    color="activity_score",
                    color_continuous_scale="Reds",
                )
                fig.update_layout(
                    margin=dict(t=20, b=40),
                    showlegend=False,
                    coloraxis_colorbar=dict(title="Activity Score"),
                )
                st.plotly_chart(fig, width="stretch")

        if len(chemexpo) > 0 and "national_product_count" in chemexpo.columns:
            st.subheader("ChemExpo: How Many Consumer Products Contain Each Chemical?")
            expo_display = chemexpo[chemexpo["national_product_count"] > 0].sort_values(
                "national_product_count", ascending=False
            )
            if len(expo_display) > 0:
                fig2 = px.bar(
                    expo_display,
                    x="casrn",
                    y="national_product_count",
                    labels={
                        "casrn": "Chemical ID (CAS #)",
                        "national_product_count": "Number of Consumer Products Nationally",
                    },
                    color="national_product_count",
                    color_continuous_scale="Blues",
                )
                fig2.update_layout(
                    margin=dict(t=20, b=40),
                    showlegend=False,
                    coloraxis_colorbar=dict(title="# Products"),
                )
                st.plotly_chart(fig2, width="stretch")

        st.divider()

    # ── Live Data Demo ───────────────────────────────────────────────────────
    st.subheader("Live Chemical Lookup — CompTox & ToxCast API Demo")
    st.caption(
        "Select a chemical from our database that has an EPA ID (DTXSID) to fetch live data "
        "from the EPA CompTox API. This demonstrates what integration would look like."
    )

    regulatory = data.get("regulatory", pd.DataFrame())
    ref_chem = data.get("ref_chemicals", pd.DataFrame())

    if len(regulatory) == 0 or 'dtxsid' not in regulatory.columns:
        st.warning(
            "No regulatory data with EPA IDs (DTXSID) available yet. "
            "Run `python -m pipeline.cli enrich-regulatory` to populate this data."
        )
    else:
        # Filter to chemicals with a DTXSID
        has_dtxsid = regulatory[regulatory['dtxsid'].notna() & (regulatory['dtxsid'] != '')].copy()

        if len(ref_chem) > 0 and 'canonical_name' in ref_chem.columns:
            has_dtxsid = has_dtxsid.merge(
                ref_chem[['casrn', 'canonical_name']], on='casrn', how='left'
            )
        else:
            has_dtxsid['canonical_name'] = has_dtxsid['casrn']

        has_dtxsid['display_name'] = has_dtxsid.apply(
            lambda r: f"{r.get('canonical_name') or r['casrn']} (DTXSID: {r['dtxsid']})", axis=1
        )

        st.success(f"{len(has_dtxsid)} chemicals in our database have an EPA DTXSID — ready for live lookup.")

        selected_display = st.selectbox(
            "Pick a chemical to look up in CompTox:",
            sorted(has_dtxsid['display_name'].tolist()),
        )
        sel_row = has_dtxsid[has_dtxsid['display_name'] == selected_display].iloc[0]
        dtxsid = sel_row['dtxsid']
        casrn = sel_row['casrn']

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Chemical ID (CAS #):** {casrn}")
            st.markdown(f"**EPA ID (DTXSID):** {dtxsid}")
        with col_b:
            # Regulatory flags from our own warehouse
            tsca = sel_row.get('tsca_listed', 'N/A')
            prop65 = sel_row.get('prop65_listed', 'N/A')
            iarc = sel_row.get('iarc_classification', 'N/A')
            st.markdown(f"**On EPA TSCA List?** {tsca} *(TSCA = Toxic Substances Control Act)*")
            st.markdown(f"**On California Prop 65 List?** {prop65} *(Prop 65 = California's list of chemicals known to cause cancer or birth defects)*")
            st.markdown(f"**IARC Cancer Classification:** {iarc} *(1 = causes cancer, 2A = probably causes cancer, 2B = possibly causes cancer)*")

        if st.button("Fetch Live Data from EPA CompTox API"):
            with st.spinner("Contacting EPA CompTox API..."):
                try:
                    # CCTE API for chemical details
                    url = f"https://api-ccte.epa.gov/chemical/detail/search/by-dtxsid/{dtxsid}"
                    headers = {"accept": "application/json"}
                    resp = requests.get(url, headers=headers, timeout=10)
                    if resp.status_code == 200:
                        result = resp.json()
                        if result:
                            st.success("Live data from EPA CompTox API:")
                            display_fields = {
                                'preferredName': 'Official Name',
                                'iupacName': 'Scientific Name (IUPAC)',
                                'smiles': 'Molecular Structure Code (SMILES)',
                                'inchiString': 'InChI Identifier',
                                'inchiKey': 'InChI Key',
                                'monoisotopicMass': 'Molecular Mass',
                                'molecularFormula': 'Molecular Formula',
                                'qsarReadySmiles': 'QSAR-Ready SMILES (for prediction models)',
                            }
                            for field, label in display_fields.items():
                                val = result.get(field)
                                if val:
                                    st.markdown(f"**{label}:** {val}")
                        else:
                            st.info("No additional data returned from the API for this chemical.")
                    else:
                        st.warning(f"API returned status {resp.status_code}. The CCTE API may require a free API key for some endpoints.")
                        st.markdown(
                            "To get a free EPA CCTE API key, visit: "
                            "**https://api-ccte.epa.gov/** and click 'Sign Up'."
                        )
                except requests.exceptions.ConnectionError:
                    st.error("Could not reach the EPA API. Check your internet connection.")
                except Exception as ex:
                    st.error(f"API error: {ex}")

    st.divider()

    # ── Integration Roadmap ──────────────────────────────────────────────────
    st.subheader("How to Add These Tools to This Dashboard — Next Steps")

    st.markdown("""
Below is a practical roadmap for integrating each EPA tool more deeply into this dashboard.
All of these tools have **free public APIs** or **bulk downloads**.

| Tool | What to Add | How |
|------|------------|-----|
| **ToxCast** | A "ToxCast Hits" column per chemical showing how many assays it triggered | Fetch from `api-ccte.epa.gov/bioactivity/data/search/by-dtxsid/{dtxsid}` |
| **GenRA** | Predicted toxicity for chemicals with no data | Use GenRA web tool or OPERA model outputs from CompTox bulk download |
| **CompTox** | Chemical structure images + predicted properties | `api-ccte.epa.gov/chemical/detail/search/by-dtxsid/{dtxsid}` |
| **ChemExpo** | "Found in X other products" exposure context | `api-ccte.epa.gov/exposure/product/search/by-dtxsid/{dtxsid}` |
| **Cheminformatics** | Skin penetration + endocrine disruption predictions | Download OPERA bulk model predictions from CompTox DSSTox |

### Recommended Priority Order:
1. **CompTox** — Add DTXSID lookups to the Chemical detail view (structure, formula, basic properties)
2. **ToxCast** — Add a "Bioactivity Score" metric per chemical (how many tests it triggered)
3. **ChemExpo** — Add "National Exposure Context" — how common is this chemical in consumer products?
4. **GenRA** — Use for chemicals missing GHS data to fill safety gaps
5. **Cheminformatics (OPERA)** — Bulk-download OPERA predictions and join to our warehouse

### Free Resources:
- EPA CCTE API documentation: **api-ccte.epa.gov**
- CompTox bulk downloads: **comptox.epa.gov/dashboard/downloads**
- ToxCast data download: **epa.gov/chemical-research/toxcast-data**
- ChemExpo source data: **chemexpo.epa.gov**
- GenRA tool: **comptox.epa.gov/genra**
    """)


# ── Main App ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Hair Glue Safety Dashboard",
    page_icon="🧪",
    layout="wide",
)

st.title("Hair Glue Product Safety Dashboard")
st.caption(
    "Analysis of chemicals in hair-glue and weaving-adhesive products using U.S. Cosmetics Safety & Product Tracker (CSCP) data. "
    "All danger scores and hazard ratings are based on internationally recognized chemical safety standards (GHS)."
)

data = load_data()

pages = {
    "Overview": page_overview,
    "Products": page_products,
    "Chemicals": page_chemicals,
    "Brands": page_brands,
    "Categories": page_categories,
    "Chemical Name Matching": page_identity,
    "EPA Research Tools": page_epa_tools,
}

page = st.sidebar.radio("Navigation", list(pages.keys()))
st.sidebar.divider()

st.sidebar.markdown("**Danger Level Guide**")
st.sidebar.markdown("🔴 **HIGH** — Contains chemicals with serious health warnings")
st.sidebar.markdown("🟠 **MEDIUM** — Contains chemicals with moderate health concerns")
st.sidebar.markdown("🟢 **LOW** — Minimal hazard chemicals")
st.sidebar.markdown("⚫ **No Data** — Not enough info to rate")

st.sidebar.divider()
st.sidebar.markdown("**Data Sources**")
st.sidebar.markdown("- CSCP Cosmetics Database (FDA)")
st.sidebar.markdown("- PubChem — Chemical Safety Data")
st.sidebar.markdown("- EPA CompTox Dashboard")
st.sidebar.markdown("- ECHA REACH (European chemical registry)")
st.sidebar.divider()
st.sidebar.caption(f"Products tracked: {len(data['products'])} | Chemicals identified: {len(data['ref_chemicals'])}")

try:
    pages[page](data)
except Exception as e:
    if "Rerun" in type(e).__name__ or "Stop" in type(e).__name__:
        raise
    st.error(f"Error loading page: {e}")
    import traceback
    st.code(traceback.format_exc())
