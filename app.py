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

try:
    from rdkit import Chem
    from rdkit.Chem.Draw import rdMolDraw2D
    RDKIT_OK = True
except ImportError:
    RDKIT_OK = False


def draw_smiles_svg(
    smiles: str, width: int = 400, height: int = 250
) -> str:
    """Return an SVG string for a SMILES structure, or '' on failure."""
    if (
        not RDKIT_OK
        or not smiles
        or str(smiles).strip() in ('', 'nan', 'None')
    ):
        return ''
    try:
        mol = Chem.MolFromSmiles(str(smiles).strip())
        if mol is None:
            return ''
        drawer = rdMolDraw2D.MolDraw2DSVG(width, height)
        drawer.drawOptions().addStereoAnnotation = True
        drawer.DrawMolecule(mol)
        drawer.FinishDrawing()
        return drawer.GetDrawingText()
    except Exception:
        return ''


WAREHOUSE = Path("warehouse")

# ── Plain-language term glossary ──────────────────────────────────────────────
GLOSSARY = {
    "Danger Score": (
        "A number from 0 to 100 that shows how risky a product is based on "
        "its chemicals. Higher = more dangerous."
    ),
    "Danger Level": (
        "A quick label (HIGH, MEDIUM, LOW) that tells you at a glance how "
        "risky a product is."
    ),
    "Cancer-Causing Chemical (Carcinogen)": (
        "A chemical that can increase the risk of cancer with long-term "
        "exposure."
    ),
    "Reproductive Hazard": (
        "A chemical that can harm the ability to have children or can hurt "
        "an unborn baby."
    ),
    "Organ Damage Chemical": (
        "A chemical that can injure organs (like the liver, kidneys, or "
        "lungs) when used repeatedly."
    ),
    "GHS": (
        "Global Harmonized System — an international system for labeling "
        "how dangerous chemicals are."
    ),
    "Warning Strength": (
        "Either 'DANGER' (very serious hazard) or 'WARNING' (moderate "
        "hazard) printed on product labels."
    ),
    "Hazard Statement Code (H-Code)": (
        "A short code (like H350) that stands for a specific health or "
        "safety warning, used worldwide."
    ),
    "Chemical ID Number (CAS #)": (
        "A unique number given to every chemical — like a social security "
        "number for chemicals."
    ),
    "Official Chemical Name": (
        "The standardized, internationally recognized name for a chemical."
    ),
    "Chemical Name Matching": (
        "The process of figuring out the real identity of an ingredient "
        "listed on a product label."
    ),
    "Product Type / Category": (
        "The type of product (e.g., Hair Extensions, Nail Products, "
        "Skin Care)."
    ),
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
        "iris": "ref_chemicals_iris.parquet",
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
        col4.metric(
            "HIGH Danger Products", f"{high_pct:.0%}",
            help=(
                "Percentage of products rated HIGH danger — meaning they "
                "contain chemicals with serious health warnings."
            ),
        )

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
            flag_counts['Danger Level Label'] = (
                flag_counts['Danger Level']
                .map(label_map)
                .fillna(flag_counts['Danger Level'])
            )
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
            selected_flag = st.selectbox(
                "Danger Level", flags,
                help=(
                    "HIGH = serious hazards present, "
                    "MEDIUM = moderate concerns, "
                    "LOW = few or minor hazards"
                ),
            )
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

        # FDA reporting badge
        regulatory = data.get("regulatory", pd.DataFrame())
        if len(regulatory) > 0 and len(identity) > 0:
            prod_casrns = identity[
                identity['product_id'] == pid
            ]['casrn'].dropna().unique()
            if len(prod_casrns) > 0 and 'cscp_reportable' in regulatory.columns:
                reg_match = regulatory[
                    regulatory['casrn'].isin(prod_casrns)
                    & (regulatory['cscp_reportable'] == True)  # noqa: E712
                ]
                if len(reg_match) > 0:
                    st.divider()
                    st.error(
                        f"**FDA Reportable Ingredients: {len(reg_match)}**  \n"
                        "This product contains chemicals that companies are "
                        "required to report to the FDA under the Cosmetics "
                        "Safety & Chemical Policy (CSCP) program. These are "
                        "chemicals with recognized hazard traits.",
                        icon="🏛️",
                    )
                    fda_chems = reg_match[[
                        'casrn', 'canonical_name',
                        'cscp_hazard_traits', 'cscp_authoritative_lists',
                    ]].rename(columns={
                        'casrn': 'CAS #',
                        'canonical_name': 'Chemical Name',
                        'cscp_hazard_traits': 'FDA-Recognized Hazard',
                        'cscp_authoritative_lists': 'On These Official Lists',
                    })
                    st.dataframe(fda_chems, width='stretch', hide_index=True)

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
                ing_display['match_source'] = (
                    ing_display['match_source']
                    .map(source_plain)
                    .fillna(ing_display['match_source'])
                )
                ing_display.columns = [
                    'Ingredient (As Listed on Label)',
                    'Chemical ID (CAS #)',
                    'Official Chemical Name',
                    'How We Identified It',
                ]
                st.dataframe(ing_display, width='stretch', hide_index=True)


def page_chemicals(data):
    """Chemical search and hazard profile viewer."""
    st.header("Chemical Database")

    st.info(
        "**What this page shows:** A searchable database of every chemical "
        "found in hair-glue products, enriched with live EPA data. "
        "Select a chemical to see its full safety profile, EPA toxicology "
        "study count, national product exposure, and structure data."
    )

    hazard_ref = data["hazard_ref"]
    identity = data["identity"]
    ref = data["ref_chemicals"]
    toxcast = data.get("toxcast", pd.DataFrame())
    chemexpo = data.get("chemexpo", pd.DataFrame())
    comptox = data.get("comptox", pd.DataFrame())
    iris = data.get("iris", pd.DataFrame())

    if len(ref) == 0:
        st.warning("No chemical reference data available.")
        return

    # ── Build merged chemical view ─────────────────────────────────────────
    chem_view = ref.copy()

    if len(hazard_ref) > 0:
        haz_dedup = (
            hazard_ref
            .sort_values('canonical_name', na_position='last')
            .drop_duplicates(subset='casrn', keep='first')
        )
        haz_cols = [
            c for c in ['ghs_hazard_class', 'ghs_signal_word', 'h_codes']
            if c in haz_dedup.columns
        ]
        chem_view = chem_view.merge(
            haz_dedup[['casrn'] + haz_cols], on='casrn', how='left'
        )

    if len(toxcast) > 0 and 'casrn' in toxcast.columns:
        tox_cols = [
            c for c in ['casrn', 'assays_tested', 'assays_active']
            if c in toxcast.columns
        ]
        chem_view = chem_view.merge(toxcast[tox_cols], on='casrn', how='left')

    if len(chemexpo) > 0 and 'casrn' in chemexpo.columns:
        expo_cols = [
            c for c in ['casrn', 'national_product_count', 'use_count']
            if c in chemexpo.columns
        ]
        chem_view = chem_view.merge(chemexpo[expo_cols], on='casrn', how='left')

    if len(comptox) > 0 and 'casrn' in comptox.columns:
        ctx_cols = [
            c for c in ['casrn', 'preferred_name', 'molecular_formula',
                        'molecular_mass', 'smiles', 'dtxsid']
            if c in comptox.columns
        ]
        chem_view = chem_view.merge(comptox[ctx_cols], on='casrn', how='left')

    if 'ghs_hazard_class' in chem_view.columns:
        chem_view['ghs_hazard_class_plain'] = (
            chem_view['ghs_hazard_class'].apply(plain_hazard_class)
        )

    # ── Search ─────────────────────────────────────────────────────────────
    search = st.text_input(
        "Search chemicals",
        placeholder="Chemical name or CAS #...",
    )
    if search:
        mask = chem_view.apply(
            lambda r: (
                search.lower() in str(r.get('canonical_name', '')).lower()
                or search.lower() in str(r.get('preferred_name', '')).lower()
                or search.lower() in str(r.get('casrn', '')).lower()
            ),
            axis=1,
        )
        chem_view = chem_view[mask]

    # ── Summary table ──────────────────────────────────────────────────────
    st.caption(f"Showing {len(chem_view)} chemicals")

    table_cols = ['casrn', 'canonical_name']
    if 'ghs_signal_word' in chem_view.columns:
        table_cols.append('ghs_signal_word')
    if 'ghs_hazard_class_plain' in chem_view.columns:
        table_cols.append('ghs_hazard_class_plain')
    if 'assays_tested' in chem_view.columns:
        table_cols.append('assays_tested')
    if 'national_product_count' in chem_view.columns:
        table_cols.append('national_product_count')
    if 'molecular_formula' in chem_view.columns:
        table_cols.append('molecular_formula')

    rename_map = {
        'casrn': 'CAS #',
        'canonical_name': 'Chemical Name',
        'ghs_signal_word': 'GHS Warning',
        'ghs_hazard_class_plain': 'Hazard Type',
        'assays_tested': 'EPA Tox Studies',
        'national_product_count': 'In # Products Nationally',
        'molecular_formula': 'Formula',
    }
    st.dataframe(
        chem_view[[c for c in table_cols if c in chem_view.columns]]
        .rename(columns=rename_map),
        width='stretch',
        hide_index=True,
    )

    # ── Chemical detail panel ──────────────────────────────────────────────
    st.divider()
    st.subheader("Chemical Safety Profile")
    chem_names = chem_view['canonical_name'].dropna().unique().tolist()
    if not chem_names:
        return

    selected_chem = st.selectbox("Select a chemical", sorted(chem_names))
    chem_row = chem_view[chem_view['canonical_name'] == selected_chem].iloc[0]
    casrn = chem_row.get('casrn')

    # Row 1 — identity + GHS signal
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**Chemical Name:** {selected_chem}")
        st.markdown(f"**CAS #:** {casrn or 'N/A'}")
        dtxsid = chem_row.get('dtxsid')
        if dtxsid and str(dtxsid) not in ('nan', 'None', ''):
            st.markdown(f"**EPA ID (DTXSID):** {dtxsid}")
        formula = chem_row.get('molecular_formula')
        if formula and str(formula) not in ('nan', 'None', ''):
            st.markdown(f"**Molecular Formula:** {formula}")
        mass = chem_row.get('molecular_mass')
        if mass and str(mass) not in ('nan', 'None', ''):
            try:
                st.markdown(f"**Molecular Mass:** {float(mass):.3f} g/mol")
            except (ValueError, TypeError):
                pass
        smiles = chem_row.get('smiles')
        if smiles and str(smiles) not in ('nan', 'None', ''):
            st.caption(f"SMILES: `{str(smiles)[:80]}`")

    with col_b:
        signal = chem_row.get('ghs_signal_word', '')
        if str(signal).upper() == 'DANGER':
            st.error("GHS Warning: DANGER — Very Serious Hazard")
        elif str(signal).upper() == 'WARNING':
            st.warning("GHS Warning: WARNING — Moderate Hazard")
        else:
            st.info("GHS Warning: Not classified")
        st.caption(
            "DANGER = can cause severe injury or death. "
            "WARNING = harmful but less immediately severe."
        )
        classes = chem_row.get('ghs_hazard_class', '')
        if classes and not pd.isna(classes):
            st.markdown("**Hazard Types:**")
            for cls in str(classes).split('|'):
                st.markdown(f"- {plain_hazard_class(cls.strip())}")

    # Row 2 — EPA data metrics
    epa_col1, epa_col2, epa_col3 = st.columns(3)

    assays = chem_row.get('assays_tested')
    active = chem_row.get('assays_active')
    nat_count = chem_row.get('national_product_count')
    use_count = chem_row.get('use_count')

    with epa_col1:
        val = int(assays) if assays and str(assays) not in ('nan', 'None') else 0
        st.metric(
            "EPA Toxicology Studies",
            val,
            help=(
                "Number of toxicological study records in EPA ToxValDB "
                "for this chemical. Higher = more studied = more data available."
            ),
        )
    with epa_col2:
        val2 = int(nat_count) if nat_count and str(nat_count) not in ('nan', 'None') else 0
        st.metric(
            "In # Consumer Products (National)",
            f"{val2:,}",
            help=(
                "How many consumer products in the EPA ChemExpo database "
                "contain this chemical. Shows how widespread your exposure "
                "to this ingredient is beyond just hair-glue products."
            ),
        )
    with epa_col3:
        val3 = int(use_count) if use_count and str(use_count) not in ('nan', 'None') else 0
        st.metric(
            "Functional Use Records",
            val3,
            help=(
                "Number of records describing how this chemical is used "
                "across products in the EPA ChemExpo database."
            ),
        )

    # Row 3 — chemical structure
    smiles = chem_row.get('smiles')
    svg = draw_smiles_svg(str(smiles) if smiles else '', width=260, height=180)
    if smiles and str(smiles) not in ('nan', 'None', ''):
        st.divider()
        st.markdown("**2D Chemical Structure**")
        st.markdown(f"**`{str(smiles)[:120]}`**")
        if svg:
            st.markdown(
                f'<div style="background:#fff;padding:6px;border-radius:6px;'
                f'display:inline-block;margin-top:6px">{svg}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("Structure could not be rendered.")

    # Row 4 — EPA IRIS federal risk data
    if len(iris) > 0 and 'casrn' in iris.columns:
        iris_row = iris[iris['casrn'] == casrn]
        if len(iris_row) > 0 and iris_row.iloc[0].get('has_iris'):
            r = iris_row.iloc[0]
            st.divider()
            st.markdown("**EPA IRIS Federal Risk Assessment**")
            st.caption(
                "IRIS (Integrated Risk Information System) is the U.S. "
                "federal standard for chemical safety limits, used by the "
                "EPA and referenced by the FDA and OSHA."
            )
            iris_col1, iris_col2 = st.columns(2)
            with iris_col1:
                rfd = r.get('rfd_chronic')
                if rfd and str(rfd) not in ('None', 'nan', ''):
                    st.metric(
                        "Safe Daily Dose (RfD)",
                        str(rfd),
                        help=(
                            "Reference Dose — the amount the EPA considers "
                            "safe to consume daily over a lifetime "
                            "(mg per kg of body weight per day)."
                        ),
                    )
                rfc = r.get('rfc_chronic')
                if rfc and str(rfc) not in ('None', 'nan', ''):
                    st.metric(
                        "Safe Air Concentration (RfC)",
                        str(rfc),
                        help=(
                            "Reference Concentration — the safe level in "
                            "air for continuous inhalation (mg/m³)."
                        ),
                    )
            with iris_col2:
                effects = r.get('critical_effects')
                if effects and str(effects) not in ('None', 'nan', ''):
                    st.markdown("**Critical Health Effects:**")
                    for effect in str(effects).replace('\n', '|').split('|'):
                        e = effect.strip()
                        if e:
                            st.markdown(f"- {e}")
                tumors = r.get('tumor_sites')
                if tumors and str(tumors) not in ('None', 'nan', ''):
                    st.markdown("**Tumor Sites (Cancer Evidence):**")
                    for site in str(tumors).replace('\n', '|').split('|'):
                        s = site.strip()
                        if s:
                            st.markdown(f"- {s}")
            revised = r.get('last_revised')
            iris_url = r.get('iris_url')
            if revised:
                st.caption(f"IRIS last revised: {revised}")
            if iris_url and str(iris_url) not in ('None', 'nan', ''):
                st.markdown(f"[View full IRIS assessment]({iris_url})")

    # Row 6 — products in our database
    if len(identity) > 0 and casrn:
        products_with = identity[identity['casrn'] == casrn]
        if len(products_with) > 0:
            st.divider()
            prods = data["products"]
            product_list = prods[
                prods['product_id'].isin(products_with['product_id'])
            ]
            st.markdown(
                f"**Found in {len(product_list)} products in this dataset:**"
            )
            st.dataframe(
                product_list[
                    ['product_name', 'brand', 'category_raw']
                ].rename(columns={
                    'product_name': 'Product Name',
                    'brand': 'Brand',
                    'category_raw': 'Product Type',
                }),
                width='stretch',
                hide_index=True,
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
    label_map_flag = {
        'HIGH': 'HIGH Danger', 'MEDIUM': 'MEDIUM Danger',
        'LOW': 'LOW Danger', 'NO_DATA': 'Not Enough Data',
    }
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
            labels={
                'pct_carcinogen': '% Products with Cancer-Causing Chemicals',
                'category_raw': 'Product Type',
            },
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
    display_cats = cats[[
        'category_raw', 'product_count',
        'avg_hazard_score', 'pct_high_hazard', 'recommendation',
    ]]
    st.dataframe(
        display_cats.rename(columns={
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
    source_counts = (
        identity['match_source']
        .map(source_plain_map)
        .fillna(identity['match_source'])
        .value_counts()
        .reset_index()
    )
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


# ── Main App ──────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Hair Glue Safety Dashboard",
    page_icon="🧪",
    layout="wide",
)

st.title("Hair Glue Product Safety Dashboard")
st.caption(
    "Analysis of chemicals in hair-glue and weaving-adhesive products "
    "using U.S. Cosmetics Safety & Product Tracker (CSCP) data. "
    "All danger scores and hazard ratings are based on internationally "
    "recognized chemical safety standards (GHS)."
)

data = load_data()

pages = {
    "Overview": page_overview,
    "Products": page_products,
    "Chemicals": page_chemicals,
    "Brands": page_brands,
    "Categories": page_categories,
    "Chemical Name Matching": page_identity,
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
