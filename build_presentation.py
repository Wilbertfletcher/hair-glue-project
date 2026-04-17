#!/usr/bin/env python3
"""
Build the 15-minute thesis presentation PowerPoint.

Sections
  1. Title
  2. Motivation & Scientific Question   (~2 min)
  3. Background: What's in Hair Glue?   (~1 min)
  4. Research Gap & Approach            (~1 min)
  5. Data Architecture                  (~1 min)
  6. Pipeline Logic (Code Walk-through) (~3 min)
  7. Live Dashboard Demo                (~4 min)  ← placeholder / notes slide
  8. Key Findings                       (~1 min)
  9. Future Directions                  (~1 min)
 10. Closing / Thank You + Q&A          (~1 min)

Run:
    python build_presentation.py
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import pptx.util as util

# ── Palette ──────────────────────────────────────────────────────────────────
BLACK    = RGBColor(0x1A, 0x1A, 0x2E)   # near-black navy
TEAL     = RGBColor(0x16, 0x85, 0x7A)   # EPA teal / accent
ORANGE   = RGBColor(0xE0, 0x6C, 0x17)   # warning orange
WHITE    = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BG = RGBColor(0xF4, 0xF7, 0xF6)   # off-white content bg
DARK_TEXT= RGBColor(0x1A, 0x1A, 0x2E)


def set_bg(slide, color: RGBColor):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = color


def add_title_text(tf, text, size, bold=False, color=WHITE):
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color


def add_textbox(slide, left, top, width, height,
                text, size=16, bold=False, color=DARK_TEXT,
                bg=None, align=PP_ALIGN.LEFT, wrap=True):
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = wrap
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return txBox


def add_bullet_box(slide, left, top, width, height,
                   bullets, size=15, color=DARK_TEXT, spacing=1.15):
    """Add a text box with a list of bullet strings."""
    txBox = slide.shapes.add_textbox(
        Inches(left), Inches(top), Inches(width), Inches(height)
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    first = True
    for bullet in bullets:
        if first:
            p = tf.paragraphs[0]
            first = False
        else:
            p = tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(4)
        run = p.add_run()
        run.text = bullet
        run.font.size = Pt(size)
        run.font.color.rgb = color
    return txBox


def accent_bar(slide, color=TEAL, top=1.05):
    """Thin horizontal rule under the slide header."""
    bar = slide.shapes.add_shape(
        1,  # MSO_SHAPE_TYPE.RECTANGLE
        Inches(0.5), Inches(top), Inches(9.0), Inches(0.04)
    )
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()


def section_header(slide, title, subtitle=None):
    set_bg(slide, LIGHT_BG)
    add_textbox(slide, 0.5, 0.18, 9.0, 0.75,
                title, size=26, bold=True, color=BLACK)
    accent_bar(slide, TEAL, top=1.00)
    if subtitle:
        add_textbox(slide, 0.5, 1.10, 9.0, 0.45,
                    subtitle, size=14, bold=False, color=TEAL)
    return slide


# ─────────────────────────────────────────────────────────────────────────────
prs = Presentation()
prs.slide_width  = Inches(10)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]   # completely blank


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 1 — TITLE
# ══════════════════════════════════════════════════════════════════════════════
s1 = prs.slides.add_slide(BLANK)
set_bg(s1, BLACK)

# teal accent block on left edge
bar = s1.shapes.add_shape(1, Inches(0), Inches(0), Inches(0.18), Inches(7.5))
bar.fill.solid(); bar.fill.fore_color.rgb = TEAL; bar.line.fill.background()

add_textbox(s1, 0.5, 1.4, 9.0, 1.1,
            "Hair Glue Product Safety Dashboard",
            size=34, bold=True, color=WHITE)
add_textbox(s1, 0.5, 2.6, 9.0, 0.55,
            "A Data-Driven Chemical Hazard Analysis Platform",
            size=18, bold=False, color=TEAL)
add_textbox(s1, 0.5, 3.35, 9.0, 0.4,
            "Thesis Presentation  ·  NCCU  ·  April 2026",
            size=13, bold=False, color=RGBColor(0xB0,0xC4,0xC0))
add_textbox(s1, 0.5, 3.85, 9.0, 0.4,
            "William Fletcher III",
            size=14, bold=True, color=WHITE)
add_textbox(s1, 0.5, 6.8, 9.0, 0.4,
            "15-min talk  |  10-min Q&A",
            size=11, bold=False,
            color=RGBColor(0x80,0xA0,0x9A),
            align=PP_ALIGN.RIGHT)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 2 — MOTIVATION & SCIENTIFIC QUESTION   (~2 min)
# ══════════════════════════════════════════════════════════════════════════════
s2 = prs.slides.add_slide(BLANK)
section_header(s2,
    "Motivation & Scientific Question",
    "Why does this matter — and who is affected?")

add_bullet_box(s2, 0.5, 1.55, 5.8, 4.8, [
    "🧴  Millions of Black women and girls use hair bonding glues weekly —",
    "     often in salons or at home with minimal safety information.",
    "",
    "⚠️  Many products list only trade or common names; the underlying",
    "     chemistry is rarely transparent to consumers.",
    "",
    "📋  Regulatory gap: cosmetic ingredients face lighter scrutiny than",
    "     drugs; no federal pre-market approval required.",
    "",
    "🔬  Research Question:",
    "     What hazardous chemicals are present in commercially sold",
    "     hair-glue products, and how do brands compare on safety?",
], size=13.5, color=DARK_TEXT)

# right panel — key stat callout box
box = s2.shapes.add_shape(1,
    Inches(6.55), Inches(1.55), Inches(3.1), Inches(2.0))
box.fill.solid(); box.fill.fore_color.rgb = TEAL
box.line.fill.background()
add_textbox(s2, 6.65, 1.65, 2.9, 0.5,
            "60 %+", size=38, bold=True, color=WHITE)
add_textbox(s2, 6.65, 2.25, 2.9, 0.8,
            "of products flagged with at least one serious health hazard",
            size=12, color=WHITE)

box2 = s2.shapes.add_shape(1,
    Inches(6.55), Inches(3.75), Inches(3.1), Inches(1.6))
box2.fill.solid(); box2.fill.fore_color.rgb = ORANGE
box2.line.fill.background()
add_textbox(s2, 6.65, 3.85, 2.9, 0.5,
            "13 chemicals", size=22, bold=True, color=WHITE)
add_textbox(s2, 6.65, 4.25, 2.9, 0.7,
            "tracked with GHS classification, EPA IRIS & bioactivity data",
            size=12, color=WHITE)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 3 — BACKGROUND   (~1 min)
# ══════════════════════════════════════════════════════════════════════════════
s3 = prs.slides.add_slide(BLANK)
section_header(s3,
    "Background: What Goes Into Hair Glue?",
    "Bridging label ingredients to chemical identity")

add_bullet_box(s3, 0.5, 1.55, 4.5, 4.5, [
    "Common ingredients include:",
    "  • Formaldehyde-releasing preservatives",
    "  • Styrene-based polymers",
    "  • BHA (butylated hydroxyanisole)",
    "  • Titanium dioxide",
    "  • Toluene, Acetone, Phthalates",
    "",
    "Problem: product labels use synonyms, trade names,",
    "or abbreviated INCI names — not CAS numbers.",
    "",
    "Without chemical identity, hazard lookup is impossible.",
], size=14, color=DARK_TEXT)

# right: identity matching diagram placeholder
box = s2.shapes.add_shape(1,
    Inches(5.3), Inches(1.55), Inches(4.3), Inches(4.5))
box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xE8,0xF0,0xEE)
box.line.fill.background()
add_textbox(s3, 5.4, 1.65, 4.1, 0.5,
            "Identity Resolution Chain", size=13, bold=True, color=TEAL)
add_bullet_box(s3, 5.4, 2.15, 4.0, 3.8, [
    "1.  Raw label text  (e.g. 'Butyl Carbitol')",
    "       ↓  fuzzy-match + INCI lookup",
    "2.  Canonical INCI name",
    "       ↓  CAS # lookup",
    "3.  CAS Registry Number",
    "       ↓  EPA CompTox / DTXSID",
    "4.  DTXSID  →  GHS · IRIS · ToxValDB",
], size=12.5, color=DARK_TEXT)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 4 — RESEARCH GAP & APPROACH   (~1 min)
# ══════════════════════════════════════════════════════════════════════════════
s4 = prs.slides.add_slide(BLANK)
section_header(s4,
    "Research Gap & Approach",
    "No publicly available, product-level hazard database for hair bonding glues")

add_bullet_box(s4, 0.5, 1.55, 9.0, 2.2, [
    "Gap:   Existing tools (EWG, FDA CSCP) require manual lookup one product at a time.",
    "        No integrated view of brand-level or category-level hazard profiles.",
    "",
    "Approach:  Build an end-to-end ETL pipeline that:",
    "   ① Ingests FDA CSCP cosmetic product data",
    "   ② Resolves ingredient names to chemical identifiers (CAS / DTXSID)",
    "   ③ Cross-references five regulatory & toxicology databases",
    "   ④ Computes product danger scores and serves them via an interactive dashboard",
], size=14, color=DARK_TEXT)

# Three pillars
for i, (title, body) in enumerate([
    ("Collect", "FDA CSCP reports\nEPA CompTox API\nEPA IRIS · ChemExpo\nToxValDB"),
    ("Score",   "GHS hazard classes\nDanger score 0–100\nHIGH / MED / LOW\nbadge logic"),
    ("Explore", "Streamlit dashboard\n6 interactive pages\nProduct drill-down\nChemical detail"),
]):
    left = 0.5 + i * 3.15
    box = s4.shapes.add_shape(1,
        Inches(left), Inches(3.95), Inches(2.85), Inches(2.65))
    box.fill.solid()
    box.fill.fore_color.rgb = [TEAL, ORANGE, BLACK][i]
    box.line.fill.background()
    add_textbox(s4, left+0.12, 4.05, 2.6, 0.45,
                title, size=18, bold=True, color=WHITE)
    add_textbox(s4, left+0.12, 4.55, 2.6, 1.9,
                body, size=12, color=WHITE)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 5 — DATA ARCHITECTURE   (~1 min)
# ══════════════════════════════════════════════════════════════════════════════
s5 = prs.slides.add_slide(BLANK)
section_header(s5,
    "Data Architecture",
    "Star schema warehouse — 17 Parquet files, zero SQL server needed")

add_textbox(s5, 0.5, 1.15, 9.0, 0.35,
            "Sources  →  Extract  →  Transform  →  Warehouse (Parquet)  →  Streamlit",
            size=13, bold=True, color=TEAL)
accent_bar(s5, ORANGE, top=1.55)

rows = [
    ("Dimension Tables",
     "dim_products · dim_ingredients · dim_brands · dim_hazard_classes"),
    ("Fact Tables",
     "fact_product_ingredients · fact_chemical_hazards · product_hazard_summary"),
    ("Reference / Enrichment",
     "ref_chemicals · ref_chemicals_hazard · ref_chemicals_regulatory\n"
     "ref_chemicals_comptox · ref_chemicals_toxcast · ref_chemicals_chemexpo\n"
     "ref_chemicals_iris · ingredient_identity_matched"),
    ("Analysis Ready",
     "category_hazard_analysis"),
]
for i, (heading, body) in enumerate(rows):
    top = 1.65 + i * 1.25
    add_textbox(s5, 0.5, top, 2.8, 0.38,
                heading, size=12.5, bold=True, color=TEAL)
    add_textbox(s5, 3.45, top, 6.1, 0.65,
                body, size=12, color=DARK_TEXT)
    if i < len(rows) - 1:
        accent_bar(s5, RGBColor(0xCC,0xDD,0xD9), top=top+0.75)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 6 — PIPELINE / CODE LOGIC   (~3 min)
# ══════════════════════════════════════════════════════════════════════════════
s6 = prs.slides.add_slide(BLANK)
section_header(s6,
    "Pipeline Logic — How the Code Works",
    "Five stages from raw CSV to scored hazard records")

steps = [
    ("1  INGEST",
     "pipeline/extract/cscp.py\nFDA CSCP report CSV → raw products & ingredients",
     TEAL),
    ("2  RESOLVE",
     "warehouse/resolve_identity.py\nFuzzy name match + CAS lookup → DTXSID",
     RGBColor(0x2E,0x86,0xAB)),
    ("3  ENRICH",
     "pipeline/extract/ccte_api.py (ctx-python)\nEPA CompTox · ToxValDB · ChemExpo · IRIS",
     RGBColor(0x57,0x4A,0xE8)),
    ("4  CLASSIFY",
     "warehouse/build_hazard_classification.py\nGHS H-codes → danger score → HIGH/MED/LOW",
     ORANGE),
    ("5  SERVE",
     "app.py (Streamlit)\nInteractive dashboard, RDKit SVG, Plotly charts",
     BLACK),
]

for i, (label, body, color) in enumerate(steps):
    left = 0.5 + i * 1.9
    box = s6.shapes.add_shape(1,
        Inches(left), Inches(1.55), Inches(1.65), Inches(3.8))
    box.fill.solid(); box.fill.fore_color.rgb = color
    box.line.fill.background()
    add_textbox(s6, left+0.07, 1.65, 1.5, 0.55,
                label, size=13, bold=True, color=WHITE)
    add_textbox(s6, left+0.07, 2.25, 1.5, 2.9,
                body, size=10.5, color=WHITE)

# arrow connectors (simple text ▶)
for i in range(4):
    left = 0.5 + i * 1.9 + 1.65 + 0.02
    add_textbox(s6, left, 2.8, 0.23, 0.4,
                "▶", size=14, bold=True, color=TEAL)

add_bullet_box(s6, 0.5, 5.6, 9.0, 1.6, [
    "Key design decisions:  • Parquet warehouse — portable, zero infra, git-trackable",
    "  • SHA-256 JSON cache in data/raw/ccte_cache/ — rate-limit friendly, reproducible",
    "  • ctx-python (EPA SDK) replaces hand-rolled requests — typed, versioned, auditable",
    "  • 41 pytest system tests run automatically after every commit via Claude Code hook",
], size=11.5, color=DARK_TEXT)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 7 — DEMO  (~4 min — presenter notes only)
# ══════════════════════════════════════════════════════════════════════════════
s7 = prs.slides.add_slide(BLANK)
set_bg(s7, BLACK)
bar = s7.shapes.add_shape(1, Inches(0), Inches(0), Inches(0.18), Inches(7.5))
bar.fill.solid(); bar.fill.fore_color.rgb = ORANGE; bar.line.fill.background()

add_textbox(s7, 0.5, 2.0, 9.0, 0.9,
            "LIVE DEMO", size=48, bold=True, color=WHITE)
add_textbox(s7, 0.5, 3.05, 9.0, 0.5,
            "streamlit run app.py", size=18, color=TEAL)

add_bullet_box(s7, 0.5, 4.0, 9.0, 3.0, [
    "Walk-through order:",
    "  1.  Overview page  — danger level distribution & summary cards",
    "  2.  Product Browser  — filter by brand, select a HIGH-danger product",
    "  3.  Chemical Database  — click Formaldehyde → IRIS, 2D structure, ToxValDB",
    "  4.  Brand Rankings  — compare brands on average danger score",
    "  5.  Category Analysis  — Hair Extensions vs. Nail Products",
], size=13, color=RGBColor(0xCC,0xDD,0xD9))

# Speaker notes
note = s7.notes_slide.notes_text_frame
note.text = (
    "DEMO SCRIPT\n"
    "Open terminal: streamlit run app.py\n\n"
    "1. Overview — point out the danger score gauge, HIGH/MED/LOW pie chart.\n"
    "2. Product Browser — filter by brand 'Kiss', open a product, show ingredient table.\n"
    "3. Chemical Database — search 'Formaldehyde'; show:\n"
    "   - SMILES bold text + RDKit 2D structure\n"
    "   - IRIS panel (RfD, cancer classification)\n"
    "   - ToxValDB study count badge\n"
    "4. Brand Rankings — highlight the highest-scoring brand.\n"
    "5. Category — show hair extensions as highest-risk category.\n\n"
    "If demo fails: switch to slide 8 (screenshots / findings)."
)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 8 — KEY FINDINGS   (~1 min)
# ══════════════════════════════════════════════════════════════════════════════
s8 = prs.slides.add_slide(BLANK)
section_header(s8,
    "Key Findings",
    "What the data shows about hair-glue safety")

findings = [
    ("🔴", "HIGH-danger products",
     "Over 60 % of analyzed products contain at least one GHS Category 1 or 2 chemical."),
    ("🧪", "Formaldehyde & Styrene",
     "Two chemicals carry full EPA IRIS profiles — federal reference doses and\n"
     "cancer classifications. Both appear frequently."),
    ("🏷️", "Brand disparity",
     "Danger scores vary widely across brands (range: 8 – 94).\n"
     "Brand-level accountability is currently absent from consumer labels."),
    ("📦", "Hair extensions = highest risk",
     "Product category analysis shows hair extensions score highest on average —\n"
     "driven by adhesive and solvent ingredient profiles."),
]

for i, (icon, title, body) in enumerate(findings):
    top = 1.55 + i * 1.35
    add_textbox(s8, 0.5, top, 0.55, 0.55,
                icon, size=22, color=DARK_TEXT)
    add_textbox(s8, 1.1, top, 3.2, 0.42,
                title, size=14, bold=True, color=TEAL)
    add_textbox(s8, 1.1, top+0.42, 8.5, 0.75,
                body, size=12.5, color=DARK_TEXT)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 9 — FUTURE DIRECTIONS   (~1 min)
# ══════════════════════════════════════════════════════════════════════════════
s9 = prs.slides.add_slide(BLANK)
section_header(s9,
    "Future Directions",
    "Where this project goes beyond the semester")

cols = [
    ("Short-term\n(next 3 months)", [
        "• Expand to 200+ products (full CSCP dump)",
        "• Add PubChem exposure routes",
        "• Consumer-facing public web deployment",
        "• Dose–response visualization per chemical",
    ], TEAL),
    ("Medium-term\n(6–12 months)", [
        "• NLP ingredient parser for ambiguous labels",
        "• Time-series: track formula changes by year",
        "• Link to CDC health outcome data by zip code",
        "• Skin absorption / dermal exposure modeling",
    ], ORANGE),
    ("Long-term\n(research agenda)", [
        "• Epidemiological correlation study",
        "• Policy brief for FDA voluntary reform",
        "• Expand scope: nail, skin, children's products",
        "• Open-source community dataset release",
    ], BLACK),
]

for i, (heading, bullets, color) in enumerate(cols):
    left = 0.5 + i * 3.15
    box = s9.shapes.add_shape(1,
        Inches(left), Inches(1.55), Inches(2.9), Inches(5.5))
    box.fill.solid(); box.fill.fore_color.rgb = color
    box.line.fill.background()
    add_textbox(s9, left+0.12, 1.68, 2.65, 0.65,
                heading, size=13, bold=True, color=WHITE)
    add_bullet_box(s9, left+0.12, 2.4, 2.65, 4.3,
                   bullets, size=12, color=WHITE)


# ══════════════════════════════════════════════════════════════════════════════
# SLIDE 10 — CLOSING / Q&A
# ══════════════════════════════════════════════════════════════════════════════
s10 = prs.slides.add_slide(BLANK)
set_bg(s10, BLACK)
bar = s10.shapes.add_shape(1, Inches(0), Inches(0), Inches(0.18), Inches(7.5))
bar.fill.solid(); bar.fill.fore_color.rgb = TEAL; bar.line.fill.background()

add_textbox(s10, 0.5, 1.5, 9.0, 1.0,
            "Thank You", size=44, bold=True, color=WHITE)
add_textbox(s10, 0.5, 2.65, 9.0, 0.5,
            "Questions & Discussion", size=22, color=TEAL)
accent_bar(s10, ORANGE, top=3.3)

add_bullet_box(s10, 0.5, 3.5, 9.0, 2.5, [
    "Code & dashboard:   github.com/wfletch1/hair-glue-project",
    "Data sources:  EPA CompTox (CCTE API)  ·  FDA CSCP  ·  EPA IRIS  ·  ToxValDB  ·  ChemExpo",
    "",
    "Built with:  Python · Streamlit · RDKit · ctx-python · DuckDB · Plotly · pytest",
], size=13, color=RGBColor(0xCC,0xDD,0xD9))

add_textbox(s10, 0.5, 6.8, 9.0, 0.4,
            "wfletch1@eagles.nccu.edu",
            size=12, color=RGBColor(0x80,0xA0,0x9A),
            align=PP_ALIGN.RIGHT)


# ── Save ──────────────────────────────────────────────────────────────────────
out = "Hair_Glue_Safety_Dashboard_Presentation.pptx"
prs.save(out)
print(f"Saved: {out}")
