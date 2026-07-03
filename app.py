import streamlit as st

st.set_page_config(
    page_title="UHI Bogotá",
    layout="wide",
    page_icon="🌡️",
    initial_sidebar_state="expanded",
)

import base64
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.data_pipeline import load_processed_data
from src.analysis import compute_correlations, compute_trends, rank_localidades, fit_lst_model, predict_lst
from src.gee_utils import (
    initialize_gee,
    get_localidades,
    get_lst_image_celsius,
    get_tile_url,
    LOCALIDADES_ASSET,
    LOCALIDAD_NAME_PROPERTY,
    LOCALIDAD_ASSET_NAMES,
)
from src.wb_pipeline import load_wb_data, get_temperature_kpis, get_heatdays_kpis, get_precip_kpis, get_scenario_series
from src.strategies import get_strategies_df, get_strategies_for_localidad, simulate_mitigation, get_category_summary


# ── Design tokens ──────────────────────────────────────────────────────────────

LOCALIDAD_COLORS = {
    "Chapinero":    "#60A5FA",
    "Ciudad Bolívar": "#F97316",
    "Usaquén":      "#34D399",
    "Kennedy":      "#A78BFA",
}

_PLOTLY = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#94a3b8", family="Sora, Inter, sans-serif", size=12),
    xaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        zerolinecolor="rgba(255,255,255,0.05)",
        linecolor="rgba(255,255,255,0.08)",
        tickfont=dict(size=11),
    ),
    yaxis=dict(
        gridcolor="rgba(255,255,255,0.05)",
        zerolinecolor="rgba(255,255,255,0.05)",
        linecolor="rgba(255,255,255,0.08)",
        tickfont=dict(size=11),
    ),
    legend=dict(
        bgcolor="rgba(255,255,255,0.03)",
        bordercolor="rgba(255,255,255,0.07)",
        borderwidth=1,
        font=dict(size=11),
    ),
    margin=dict(l=8, r=8, t=44, b=8),
    hoverlabel=dict(
        bgcolor="#1e293b",
        bordercolor="rgba(255,255,255,0.12)",
        font=dict(color="#f1f5f9", size=12),
    ),
    title_font=dict(size=13, color="#cbd5e1"),
    title_x=0,
)

# ── Theme ──────────────────────────────────────────────────────────────────────
# Dark mode only — the light mode toggle was removed by design decision.

_P = _PLOTLY

# Text palette with verified contrast (WCAG AA, ≥4.5:1) against the dark
# backgrounds — used in the HTML blocks assembled in Python.
_MUTED        = "#94a3b8"
_ACCENT_BAD   = "#fb923c"   # orange: alert / negative delta
_ACCENT_GOOD  = "#34d399"   # green: positive / low cost
_ACCENT_WARM  = "#fbbf24"   # amber: moderate / medium cost
_ACCENT_BLUE  = "#60A5FA"   # blue: category / info


# ── CSS ────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;500;600;700&display=swap');

/* ── Hide Streamlit chrome ────────────────────────────────────────────────── */
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"], [data-testid="stToolbar"] { display: none; }

/* ── Base ────────────────────────────────────────────────────────────────── */
html, body, .stApp {
    font-family: 'Sora', 'Inter', system-ui, sans-serif !important;
    background-color: #060b18 !important;
    color: #e2e8f0 !important;
}
.block-container {
    padding: 2rem 2.5rem 5rem !important;
    max-width: 1440px !important;
}

/* ── Sidebar ──────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #080e1d !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] label {
    font-size: 0.7rem !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
}

/* ── Tabs ─────────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] button[role="tab"] p {
    color: #94a3b8 !important;
    font-weight: 500 !important;
}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {
    color: #f97316 !important;
    font-weight: 600 !important;
}

/* ── Metric (st.metric) ───────────────────────────────────────────────────── */
[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; }

/* ── Charts ───────────────────────────────────────────────────────────────── */
[data-testid="stPlotlyChart"] > div {
    background: #0c1322 !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
    padding: 4px !important;
}

/* ── Dataframe ────────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
    background: #0c1322 !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}

/* ── Sliders ──────────────────────────────────────────────────────────────── */
[data-testid="stSlider"] [data-testid="stSliderThumb"] {
    background: #f97316 !important;
    border: 2px solid #f97316 !important;
}
[data-testid="stSlider"] [class*="sliderTrack"] > div:first-child {
    background: #f97316 !important;
}

/* ── Buttons ──────────────────────────────────────────────────────────────── */
div[data-testid="stButton"] > button {
    background: #f97316 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'Sora', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    letter-spacing: 0.05em !important;
    padding: 0.6rem 1.6rem !important;
    transition: all 0.15s ease !important;
}
div[data-testid="stButton"] > button:hover {
    background: #ea6c0a !important;
    box-shadow: 0 0 22px rgba(249,115,22,0.4) !important;
    transform: translateY(-1px) !important;
}

/* ── Alerts ───────────────────────────────────────────────────────────────── */
[data-testid="stInfo"] {
    background: rgba(96,165,250,0.06) !important;
    border: 1px solid rgba(96,165,250,0.18) !important;
    border-radius: 8px !important;
    color: #93c5fd !important;
}
[data-testid="stSuccess"] {
    background: rgba(52,211,153,0.06) !important;
    border: 1px solid rgba(52,211,153,0.2) !important;
    border-radius: 8px !important;
    color: #6ee7b7 !important;
}

/* ── Custom components ────────────────────────────────────────────────────── */
.hero {
    padding: 2.2rem 0 2rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    margin-bottom: 2rem;
}
.hero-eyebrow {
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #f97316;
    font-weight: 600;
    margin-bottom: 0.55rem;
}
.hero-title {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.18;
    background: linear-gradient(125deg, #f1f5f9 0%, #64748b 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 0.55rem;
}
.hero-sub {
    font-size: 0.85rem;
    color: #475569;
    font-weight: 400;
    margin: 0;
    max-width: 620px;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 0.5rem;
}
.kpi-card {
    background: #0c1322;
    border: 1px solid rgba(255,255,255,0.07);
    border-top: 2px solid var(--accent, #f97316);
    border-radius: 10px;
    padding: 1.3rem 1.4rem 1.2rem;
}
.kpi-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #94a3b8;
    font-weight: 600;
    margin-bottom: 0.65rem;
}
.kpi-value {
    font-size: 1.75rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1;
    margin-bottom: 0.5rem;
    font-variant-numeric: tabular-nums;
}
.kpi-delta {
    font-size: 0.72rem;
    font-weight: 500;
    border-radius: 4px;
    padding: 0.18rem 0.5rem;
    display: inline-block;
}
.kpi-delta.bad    { color: #fb923c; background: rgba(249,115,22,0.1); }
.kpi-delta.good   { color: #34d399; background: rgba(52,211,153,0.1); }
.kpi-delta.plain  { color: #94a3b8; background: rgba(148,163,184,0.1); }

.section-header {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    margin: 2.5rem 0 1.2rem;
}
.section-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #f97316;
    flex-shrink: 0;
}
.section-title {
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #94a3b8;
    margin: 0;
    white-space: nowrap;
}
.section-line {
    flex: 1;
    height: 1px;
    background: rgba(255,255,255,0.05);
}

.rank-wrap {
    background: #0c1322;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    overflow: hidden;
}
.rank-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
}
.rank-table th {
    text-align: left;
    padding: 0.7rem 1.1rem;
    font-size: 0.63rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #94a3b8;
    font-weight: 600;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    background: rgba(0,0,0,0.2);
}
.rank-table td {
    padding: 0.75rem 1.1rem;
    color: #94a3b8;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    font-variant-numeric: tabular-nums;
}
.rank-table tr:last-child td { border-bottom: none; }
.rank-table td.loc-name { color: #e2e8f0; font-weight: 500; }
.rank-table tr.critical td { background: rgba(249,115,22,0.05); }
.rank-table tr.critical td.loc-name { color: #fb923c; }
.rank-table tr.critical td:first-child { border-left: 2px solid #f97316; }
.rank-table tr:hover td { background: rgba(255,255,255,0.02); }
.badge {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.12rem 0.5rem;
    border-radius: 4px;
    font-size: 0.67rem;
    font-weight: 600;
    letter-spacing: 0.04em;
}
.badge-hot  { background: rgba(249,115,22,0.12); color: #fb923c; }
.badge-warm { background: rgba(251,191,36,0.10); color: #fbbf24; }
.badge-cool { background: rgba(52,211,153,0.10); color: #34d399; }

.sim-wrap {
    background: #0c1322;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 1.75rem 2rem 1.5rem;
}
.sim-result-box {
    display: flex;
    align-items: center;
    gap: 2rem;
    background: rgba(249,115,22,0.07);
    border: 1px solid rgba(249,115,22,0.18);
    border-radius: 8px;
    padding: 1.1rem 1.75rem;
    margin-top: 1.2rem;
}
.sim-result-temp {
    font-size: 2.6rem;
    font-weight: 700;
    color: #f97316;
    line-height: 1;
    font-variant-numeric: tabular-nums;
}
.sim-result-meta {
    font-size: 0.77rem;
    color: #94a3b8;
    line-height: 1.8;
}
.sim-result-meta span { color: #f1f5f9; }

.footer-bar {
    margin-top: 4rem;
    padding-top: 1.5rem;
    border-top: 1px solid rgba(255,255,255,0.05);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.72rem;
    color: #94a3b8;
}

/* ── Institutional header ─────────────────────────────────────────────────── */
.inst-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    padding: 1.4rem 2rem;
    margin-bottom: 2rem;
    background: #07111f;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 12px;
}
.inst-logo-wrap {
    display: flex;
    align-items: center;
    flex-shrink: 0;
}
.inst-logo {
    height: 52px;
    width: auto;
    max-width: 210px;
    object-fit: contain;
    opacity: 0.88;
    transition: opacity 0.2s;
}
.inst-logo:hover { opacity: 1; }
.inst-logo-wrap svg {
    height: 52px;
    width: auto;
    max-width: 200px;
    opacity: 0.88;
}
.inst-divider {
    width: 1px;
    height: 44px;
    background: rgba(255,255,255,0.1);
    flex-shrink: 0;
}
.inst-title-block {
    flex: 1;
    text-align: center;
    padding: 0 1rem;
}
.inst-eyebrow {
    font-size: 0.6rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #f97316 !important;
    font-weight: 600;
    margin-bottom: 0.35rem;
}
.inst-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #ffffff !important;
    line-height: 1.25;
    margin: 0 0 0.25rem;
    letter-spacing: -0.01em;
}
.inst-sub {
    font-size: 0.7rem;
    color: #94a3b8 !important;
    font-weight: 400;
    margin: 0;
}

</style>
""", unsafe_allow_html=True)


# ── Logos ─────────────────────────────────────────────────────────────────────

import re as _re
_APP_DIR = Path(__file__).parent

def _extract_png_from_svg(path: str) -> str:
    """Extract the embedded PNG data URI from an SVG with a bitmap pattern."""
    svg_text = (_APP_DIR / path).read_text()
    m = _re.search(r'xlink:href="(data:image/[^"]+)"', svg_text)
    return m.group(1) if m else ""

# ext_logo has an embedded PNG → used as <img src="data:image/png;...">
_EXT_LOGO_SRC = _extract_png_from_svg("ext_logo.svg")

# unitus_logo is pure vector SVG → inlined directly as SVG markup
_UNIT_LOGO_SVG = (_APP_DIR / "assets/unitus_logo.svg").read_text()


# ── GEE ───────────────────────────────────────────────────────────────────────

@st.cache_resource
def _init_gee() -> bool:
    try:
        gee_cfg = st.secrets.get("gee", None)
        if not gee_cfg:
            return False
        initialize_gee(
            project=gee_cfg.get("project", "uhi-bogota"),
            service_account_info=dict(gee_cfg.get("service_account", {})) or None,
        )
        import ee
        ee.Number(1).getInfo()
        return True
    except Exception:
        return False


@st.cache_resource
def _build_gee_map(year: int, _year_stats: pd.DataFrame):
    """Build a folium map with real GEE layers (LST + locality boundaries).

    Uses plain folium instead of geemap.foliumap: the installed geemap
    version has a known import bug (name collision in its `basemaps`
    module) that breaks `geemap.foliumap` unconditionally.

    `year` selects which year's LST composite to show — it's a normal
    (hashable) argument, so Streamlit caches one map per year picked.
    `_year_stats` (leading underscore so Streamlit doesn't try to hash it)
    holds one row per locality for that same year, used to populate the
    boundary popups.
    """
    try:
        import folium
        from branca.colormap import LinearColormap

        m = folium.Map(location=[4.65, -74.08], zoom_start=11, tiles="CartoDB dark_matter")

        localidades_fc = get_localidades(LOCALIDADES_ASSET)

        lst_min, lst_max = 14, 24
        lst_palette = ["2166ac", "67a9cf", "fee090", "fdae61", "d73027"]
        lst_vis = {"min": lst_min, "max": lst_max, "palette": lst_palette}
        lst_image = get_lst_image_celsius(year, geometry=localidades_fc.geometry())
        folium.raster_layers.TileLayer(
            tiles=get_tile_url(lst_image, lst_vis),
            attr="Google Earth Engine",
            name=f"Mean JJA LST {year} (°C)",
            overlay=True,
            control=True,
        ).add_to(m)

        colormap = LinearColormap(
            colors=[f"#{c}" for c in lst_palette],
            vmin=lst_min,
            vmax=lst_max,
            caption=f"Mean JJA LST {year} (°C)",
        )
        colormap.add_to(m)

        # Dark styling for the Leaflet popup chrome (folium's default popup
        # is a white box, which clashes with the rest of the dashboard).
        m.get_root().html.add_child(folium.Element("""
            <style>
            .leaflet-popup-content-wrapper, .leaflet-popup-tip { background: #0c1322 !important; }
            .leaflet-popup-close-button { color: #94a3b8 !important; }
            </style>
        """))

        asset_to_canonical = {v: k for k, v in LOCALIDAD_ASSET_NAMES.items()}
        for feature in localidades_fc.getInfo()["features"]:
            asset_name = feature["properties"].get(LOCALIDAD_NAME_PROPERTY, "")
            canonical_name = asset_to_canonical.get(asset_name, asset_name)
            color = LOCALIDAD_COLORS.get(canonical_name, "#94a3b8")

            stats_row = _year_stats[_year_stats["localidad"] == canonical_name]
            if not stats_row.empty:
                s = stats_row.iloc[0]
                popup_html = f"""
                <div style="font-family:'Sora',sans-serif;background:#0c1322;color:#e2e8f0;padding:10px 12px;border-radius:6px;min-width:150px">
                  <div style="font-weight:700;font-size:0.85rem;margin-bottom:6px;color:{color}">{canonical_name}</div>
                  <div style="font-size:0.75rem;line-height:1.7;color:#94a3b8">
                    LST {year}: <strong style="color:#e2e8f0">{s['lst_celsius']:.1f} °C</strong><br>
                    NDVI: <strong style="color:#e2e8f0">{s['ndvi']:.2f}</strong><br>
                    % Urban: <strong style="color:#e2e8f0">{s['urban_pct']:.1f}%</strong>
                  </div>
                </div>
                """
                popup = folium.Popup(popup_html, max_width=220)
            else:
                popup = None

            folium.GeoJson(
                feature,
                name=canonical_name,
                style_function=lambda _f, c=color: {"color": c, "weight": 3, "fillOpacity": 0},
                popup=popup,
            ).add_to(m)

        folium.LayerControl(collapsed=False).add_to(m)
        return m
    except Exception:
        return None


gee_available = _init_gee()


# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def _load_data() -> pd.DataFrame:
    return load_processed_data()

@st.cache_data(ttl=3600)
def _cached_corr(data: pd.DataFrame) -> pd.DataFrame:
    return compute_correlations(data)

@st.cache_data(ttl=3600)
def _cached_rank(data: pd.DataFrame) -> pd.DataFrame:
    return rank_localidades(data)

@st.cache_data(ttl=3600)
def _cached_model(data: pd.DataFrame) -> dict:
    return fit_lst_model(data)

@st.cache_data(ttl=3600)
def _cached_trends(data: pd.DataFrame) -> pd.DataFrame:
    return compute_trends(data)


try:
    df_raw = _load_data()
except Exception as exc:
    st.error(f"Error loading data: {exc}")
    st.stop()

if df_raw.empty:
    st.warning("No processed data found. Run data_pipeline.py first.")
    st.stop()


# ── Sidebar ────────────────────────────────────────────────────────────────────

st.sidebar.markdown("""
<div style="padding:1rem 0 1.4rem;border-bottom:1px solid rgba(128,128,128,0.12);margin-bottom:1.2rem;">
  <div style="font-size:0.6rem;letter-spacing:.18em;color:#f97316;text-transform:uppercase;font-weight:600">Project</div>
  <div style="font-size:1.05rem;font-weight:700;margin-top:.2rem;font-family:'Sora',sans-serif">UHI Bogotá</div>
  <div style="font-size:0.72rem;margin-top:.15rem;opacity:0.4">Monitoring 2015 – 2025</div>
</div>
""", unsafe_allow_html=True)

all_localidades = sorted(df_raw["localidad"].unique().tolist())
selected_localidades = st.sidebar.multiselect("Localities", options=all_localidades, default=all_localidades)
if not selected_localidades:
    selected_localidades = all_localidades

year_range = st.sidebar.slider("Time range", 2015, 2025, (2015, 2025))

_VAR_MAP = {"LST (°C)": "lst_celsius", "NDVI": "ndvi", "% Urban": "urban_pct"}
variable_label = st.sidebar.radio("Main variable", list(_VAR_MAP.keys()))
variable_col = _VAR_MAP[variable_label]

st.sidebar.markdown("""
<div style="margin-top:2rem;padding-top:1rem;border-top:1px solid rgba(255,255,255,0.05)">
  <div style="font-size:0.65rem;color:#334155;line-height:1.7">
    Sources: MODIS MOD11A2 · Sentinel-2 SR · Dynamic World V1<br>
    Platform: Google Earth Engine
  </div>
</div>
""", unsafe_allow_html=True)


# ── Filtering ──────────────────────────────────────────────────────────────────

df = df_raw[
    df_raw["localidad"].isin(selected_localidades)
    & df_raw["year"].between(year_range[0], year_range[1])
].copy()

if df.empty:
    st.warning("No data for the current selection.")
    st.stop()

first_year = int(df["year"].min())
last_year  = int(df["year"].max())

def _mean_year(col: str, year: int) -> float:
    s = df[df["year"] == year]
    return float(s[col].mean()) if not s.empty else float("nan")


# ── Institutional header ──────────────────────────────────────────────────────
# (outside the tabs — visible across the whole dashboard)

st.markdown(f"""
<div class="inst-header">
  <div class="inst-logo-wrap">
    <img class="inst-logo" src="{_EXT_LOGO_SRC}" alt="Universidad Externado de Colombia" />
  </div>

  <div class="inst-divider"></div>

  <div class="inst-title-block">
    <div class="inst-eyebrow">Research Project · Geospatial · Bogotá D.C.</div>
    <h1 class="inst-title">Urban Heat Monitoring <br> Bogotá 2015 · 2025</h1>
    <p class="inst-sub">Surface temperature · Vegetation cover · Urban expansion · Google Earth Engine</p>
  </div>

  <div class="inst-divider"></div>

  <div class="inst-logo-wrap" style="display:flex;align-items:center;">
    {_UNIT_LOGO_SVG}
  </div>
</div>
""", unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────

tab1, tab2, tab3 = st.tabs([
    "🌍  Step 1 · Climate Projections",
    "🏙️  Step 2 · Bogotá: UHI Analysis",
    "🌿  Step 3 · Mitigation Strategies",
])

# ── TAB 1: Colombia climate projections ────────────────────────────────────────

with tab1:

    @st.cache_data(ttl=3600)
    def _load_wb() -> pd.DataFrame:
        return load_wb_data()

    wb = _load_wb()

    if wb.empty:
        st.warning("No climate data found. Run `python -m src.wb_pipeline` first.")
    else:
        st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Colombia · Projected Climate Change</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

        t_kpi  = get_temperature_kpis(wb)
        hd_kpi = get_heatdays_kpis(wb)
        pr_kpi = get_precip_kpis(wb)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Historical avg. temp. (1981–2010)", f"{t_kpi['hist_mean']:.1f} °C")
        k2.metric("RCP4.5 projection · 2071–2080", f"{t_kpi['rcp45_2080']:.1f} °C", delta=f"{t_kpi['delta_rcp45']:+.1f} °C", delta_color="inverse")
        k3.metric("RCP8.5 projection · 2071–2080", f"{t_kpi['rcp85_2080']:.1f} °C", delta=f"{t_kpi['delta_rcp85']:+.1f} °C", delta_color="inverse")
        k4.metric("Extra extreme heat days (RCP8.5)", f"+{hd_kpi['delta_rcp85']:.0f} days/year", delta_color="inverse")

        st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Annual Mean Temperature · Colombia</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

        ts = get_scenario_series(wb, "tas_mean")
        fig_t = go.Figure()
        fig_t.add_trace(go.Scatter(x=ts["year"], y=ts["historical"], name="Historical", line=dict(color="#60A5FA", width=2)))
        fig_t.add_trace(go.Scatter(x=ts["year"], y=ts["rcp45"], name="RCP 4.5", line=dict(color="#34D399", width=2, dash="dot")))
        fig_t.add_trace(go.Scatter(x=ts["year"], y=ts["rcp85"], name="RCP 8.5", line=dict(color="#F97316", width=2, dash="dot")))
        fig_t.add_trace(go.Scatter(x=pd.concat([ts["year"], ts["year"][::-1]]),
            y=pd.concat([ts["rcp85_high"], ts["rcp85_low"][::-1]]),
            fill="toself", fillcolor="rgba(249,115,22,0.08)", line=dict(width=0),
            name="RCP8.5 Uncertainty", showlegend=True))
        fig_t.add_trace(go.Scatter(x=pd.concat([ts["year"], ts["year"][::-1]]),
            y=pd.concat([ts["rcp45_high"], ts["rcp45_low"][::-1]]),
            fill="toself", fillcolor="rgba(52,211,153,0.08)", line=dict(width=0),
            name="RCP4.5 Uncertainty", showlegend=True))
        fig_t.update_layout(**_P, title="Annual Mean Temperature (°C) · Colombia 1950–2080",
                            xaxis_title="Year", yaxis_title="Temperature (°C)")
        st.plotly_chart(fig_t, use_container_width=True)

        c1t, c2t = st.columns(2)
        with c1t:
            ts_hd = get_scenario_series(wb, "tx35_days")
            fig_hd = go.Figure()
            fig_hd.add_trace(go.Scatter(x=ts_hd["year"], y=ts_hd["historical"], name="Historical", line=dict(color="#60A5FA", width=2)))
            fig_hd.add_trace(go.Scatter(x=ts_hd["year"], y=ts_hd["rcp45"], name="RCP 4.5", line=dict(color="#34D399", width=2, dash="dot")))
            fig_hd.add_trace(go.Scatter(x=ts_hd["year"], y=ts_hd["rcp85"], name="RCP 8.5", line=dict(color="#F97316", width=2, dash="dot")))
            fig_hd.add_trace(go.Scatter(x=pd.concat([ts_hd["year"], ts_hd["year"][::-1]]),
                y=pd.concat([ts_hd["rcp85_high"], ts_hd["rcp85_low"][::-1]]),
                fill="toself", fillcolor="rgba(249,115,22,0.08)", line=dict(width=0), showlegend=False))
            fig_hd.update_layout(**_P, title="Days with max temperature > 35 °C / year",
                                 xaxis_title="Year", yaxis_title="Days / year")
            st.plotly_chart(fig_hd, use_container_width=True)

        with c2t:
            ts_pr = get_scenario_series(wb, "pr_mm")
            fig_pr = go.Figure()
            fig_pr.add_trace(go.Scatter(x=ts_pr["year"], y=ts_pr["historical"], name="Historical", line=dict(color="#60A5FA", width=2)))
            fig_pr.add_trace(go.Scatter(x=ts_pr["year"], y=ts_pr["rcp45"], name="RCP 4.5", line=dict(color="#34D399", width=2, dash="dot")))
            fig_pr.add_trace(go.Scatter(x=ts_pr["year"], y=ts_pr["rcp85"], name="RCP 8.5", line=dict(color="#F97316", width=2, dash="dot")))
            fig_pr.add_trace(go.Scatter(x=pd.concat([ts_pr["year"], ts_pr["year"][::-1]]),
                y=pd.concat([ts_pr["rcp85_high"], ts_pr["rcp85_low"][::-1]]),
                fill="toself", fillcolor="rgba(249,115,22,0.08)", line=dict(width=0), showlegend=False))
            fig_pr.update_layout(**_P, title="Annual Precipitation (mm) · Colombia",
                                 xaxis_title="Year", yaxis_title="Precipitation (mm)")
            st.plotly_chart(fig_pr, use_container_width=True)

        st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Projected Implications</h3><div class="section-line"></div></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="sim-wrap" style="line-height:1.9;font-size:0.85rem;">
          <p>Colombia will experience a <strong>temperature increase of {t_kpi['delta_rcp45']:.1f}–{t_kpi['delta_rcp85']:.1f} °C</strong> by the end of the 21st century
          under the RCP4.5 and RCP8.5 scenarios, respectively. This implies:</p>
          <ul style="margin:0.75rem 0 0.75rem 1.25rem;color:inherit;">
            <li><strong>Public health:</strong> increase in heat-related illnesses, especially in low-altitude urban areas and vulnerable populations.</li>
            <li><strong>Agriculture:</strong> water stress in coffee, sugarcane, and rice crops; shifting of thermal altitude zones in the Andes.</li>
            <li><strong>Biodiversity:</strong> disruption of páramo ecosystems, essential for the water supply of cities like Bogotá.</li>
            <li><strong>Cities:</strong> the urban heat island effect will amplify these increases in densely built-up areas,
            producing thermal risk scenarios greater than those projected at the national scale.</li>
          </ul>
          <p style="margin-top:0.5rem;color:{_MUTED};font-size:0.78rem;">
            Reference source: NASA NEX-GDDP-CMIP6 (via Google Earth Engine) · SSP2-4.5 / SSP5-8.5 scenarios (CMIP6, equivalent to RCP4.5 / RCP8.5)
          </p>
        </div>
        """, unsafe_allow_html=True)


# ── TAB 2: Bogotá UHI analysis ──────────────────────────────────────────────────

with tab2:

    # ── KPIs ──────────────────────────────────────────────────────────────────

    lst_now    = _mean_year("lst_celsius", last_year)
    lst_before = _mean_year("lst_celsius", first_year)
    ndvi_now   = _mean_year("ndvi", last_year)
    ndvi_before= _mean_year("ndvi", first_year)
    urb_now    = _mean_year("urban_pct", last_year)
    urb_before = _mean_year("urban_pct", first_year)

    try:
        _rk = _cached_rank(df)
        critical_loc    = _rk.iloc[0]["localidad"]
        critical_change = float(_rk.iloc[0]["lst_change"])
        kpi4 = f"""
        <div class="kpi-card" style="--accent:#A78BFA">
          <div class="kpi-label">Most Critical Locality</div>
          <div class="kpi-value" style="font-size:1.35rem">{critical_loc}</div>
          <span class="kpi-delta bad">ΔT {critical_change:+.2f} °C</span>
        </div>"""
    except Exception:
        kpi4 = '<div class="kpi-card" style="--accent:#A78BFA"><div class="kpi-label">Critical Locality</div><div class="kpi-value">N/A</div></div>'

    lst_d  = lst_now - lst_before
    ndvi_d = ndvi_now - ndvi_before
    urb_d  = urb_now - urb_before

    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card" style="--accent:#F97316">
        <div class="kpi-label">Average LST · {last_year}</div>
        <div class="kpi-value">{lst_now:.2f} °C</div>
        <span class="kpi-delta {'bad' if lst_d > 0 else 'good'}">{lst_d:+.2f} °C vs {first_year}</span>
      </div>
      <div class="kpi-card" style="--accent:#34D399">
        <div class="kpi-label">Average NDVI · {last_year}</div>
        <div class="kpi-value">{ndvi_now:.3f}</div>
        <span class="kpi-delta {'good' if ndvi_d > 0 else 'bad'}">{ndvi_d:+.3f} vs {first_year}</span>
      </div>
      <div class="kpi-card" style="--accent:#60A5FA">
        <div class="kpi-label">Average % Urban · {last_year}</div>
        <div class="kpi-value">{urb_now:.1f} %</div>
        <span class="kpi-delta {'bad' if urb_d > 0 else 'good'}">{urb_d:+.1f} pp vs {first_year}</span>
      </div>
      {kpi4.strip()}
    </div>
    """, unsafe_allow_html=True)

    # ── Map ───────────────────────────────────────────────────────────────────

    st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Surface Temperature Map</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

    if gee_available:
        map_years = list(range(first_year, last_year + 1))
        map_year = st.selectbox("Map year", options=map_years, index=len(map_years) - 1, key="map_year")
        m = _build_gee_map(map_year, df_raw[df_raw["year"] == map_year])
        if m:
            try:
                st.components.v1.html(m._repr_html_(), height=480)
            except Exception as exc:
                st.info(f"Could not render the map: {exc}")
        else:
            st.info("Map unavailable — error querying Earth Engine.")
    else:
        st.info("Map unavailable — configure GEE credentials in `.streamlit/secrets.toml`")

    # ── Time series ─────────────────────────────────────────────────────────────

    st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Time Evolution by Locality</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

    df_s = df.sort_values(["localidad", "year"])
    c1, c2 = st.columns(2)

    with c1:
        fig_lst = px.line(
            df_s, x="year", y="lst_celsius", color="localidad", markers=True,
            title="Surface Temperature (LST)",
            labels={"year": "Year", "lst_celsius": "LST (°C)", "localidad": "Locality"},
            color_discrete_map=LOCALIDAD_COLORS,
        )
        fig_lst.update_traces(line=dict(width=2), marker=dict(size=6))
        fig_lst.update_layout(**_P)
        st.plotly_chart(fig_lst, use_container_width=True)

    with c2:
        fig_ndvi = px.line(
            df_s, x="year", y="ndvi", color="localidad", markers=True,
            title="Vegetation Index (NDVI)",
            labels={"year": "Year", "ndvi": "NDVI", "localidad": "Locality"},
            color_discrete_map=LOCALIDAD_COLORS,
        )
        fig_ndvi.update_traces(line=dict(width=2), marker=dict(size=6))
        fig_ndvi.update_layout(**_P)
        st.plotly_chart(fig_ndvi, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        fig_urb = px.area(
            df_s, x="year", y="urban_pct", color="localidad",
            title="Urban Expansion (% urban land)",
            labels={"year": "Year", "urban_pct": "% Urban", "localidad": "Locality"},
            color_discrete_map=LOCALIDAD_COLORS,
        )
        fig_urb.update_traces(opacity=0.55, line=dict(width=1.5))
        fig_urb.update_layout(**_P)
        st.plotly_chart(fig_urb, use_container_width=True)

    with c4:
        fig_var = px.line(
            df_s, x="year", y=variable_col, color="localidad", markers=True,
            title=f"Selected variable: {variable_label}",
            labels={"year": "Year", variable_col: variable_label, "localidad": "Locality"},
            color_discrete_map=LOCALIDAD_COLORS,
        )
        fig_var.update_traces(line=dict(width=2), marker=dict(size=6))
        fig_var.update_layout(**_P)
        st.plotly_chart(fig_var, use_container_width=True)

    # ── Correlations ────────────────────────────────────────────────────────────

    st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Correlations Between Variables</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

    try:
        corr_df  = _cached_corr(df)
        pair_row = corr_df[corr_df["pair"] == "ndvi_vs_lst"]
        r_global = float(pair_row["pearson_r"].mean()) if not pair_row.empty else float("nan")

        ca, cb = st.columns([3, 2])

        with ca:
            fig_sc = px.scatter(
                df, x="ndvi", y="lst_celsius", color="localidad",
                size="urban_pct", size_max=18,
                title=f"NDVI vs LST — Pearson r = {r_global:.3f}" if not pd.isna(r_global) else "NDVI vs LST",
                labels={"ndvi": "NDVI", "lst_celsius": "LST (°C)", "localidad": "Locality", "urban_pct": "% Urban"},
                color_discrete_map=LOCALIDAD_COLORS,
            )
            fig_sc.update_layout(**_P)
            st.plotly_chart(fig_sc, use_container_width=True)

        with cb:
            if not pair_row.empty:
                fig_bar = px.bar(
                    pair_row.sort_values("pearson_r"),
                    x="pearson_r", y="localidad", orientation="h",
                    title="Pearson r (NDVI ↔ LST) by locality",
                    labels={"pearson_r": "Pearson r", "localidad": ""},
                    color="pearson_r",
                    color_continuous_scale=["#34D399", "#FBBF24", "#F97316"],
                    range_color=[-1, 0],
                )
                fig_bar.update_layout(**_P, coloraxis_showscale=False)
                fig_bar.update_traces(marker_line_width=0)
                st.plotly_chart(fig_bar, use_container_width=True)

    except Exception as exc:
        st.warning(f"Could not calculate correlations: {exc}")

    # ── Ranking ──────────────────────────────────────────────────────────────────

    st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Locality Ranking by Criticality</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

    try:
        ranking = _cached_rank(df)

        def _badge(lst_val: float) -> str:
            if lst_val >= 19.5:
                return '<span class="badge badge-hot">🔴 Critical</span>'
            if lst_val >= 17.5:
                return '<span class="badge badge-warm">🟡 Moderate</span>'
            return '<span class="badge badge-cool">🟢 Low</span>'

        max_idx = int(ranking["lst_change"].idxmax())
        rows_html = ""
        for i, row in ranking.iterrows():
            critical_cls = "critical" if i == max_idx else ""
            rows_html += f"""
            <tr class="{critical_cls}">
              <td class="loc-name">{row['localidad']}</td>
              <td>{_badge(row['lst_last'])}</td>
              <td>{row['lst_mean']:.2f} °C</td>
              <td>{row['lst_last']:.2f} °C</td>
              <td style="color:{_ACCENT_BAD if row['lst_change']>0 else _ACCENT_GOOD};font-weight:600">{row['lst_change']:+.2f} °C</td>
              <td>{row['ndvi_mean']:.3f}</td>
              <td style="color:{_ACCENT_BAD if row['ndvi_change']<0 else _ACCENT_GOOD};font-weight:600">{row['ndvi_change']:+.3f}</td>
              <td>{row['urban_pct_last']:.1f} %</td>
            </tr>"""

        st.markdown(f"""
        <div class="rank-wrap">
          <table class="rank-table">
            <thead>
              <tr>
                <th>Locality</th><th>Level</th>
                <th>Mean LST</th><th>LST {last_year}</th><th>Δ LST</th>
                <th>Mean NDVI</th><th>Δ NDVI</th><th>% Urban</th>
              </tr>
            </thead>
            <tbody>{rows_html}</tbody>
          </table>
        </div>
        """, unsafe_allow_html=True)

    except Exception as exc:
        st.warning(f"Could not generate the ranking: {exc}")

    # ── Trend analysis ──────────────────────────────────────────────────────────

    st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Statistical Trend Analysis</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

    try:
        trends_df = _cached_trends(df)

        def _trend_badge(row: pd.Series, higher_is_bad: bool) -> str:
            trend, p_value, slope = row["mk_trend"], row["mk_p_value"], row["slope"]
            significant = p_value < 0.05
            if trend == "increasing":
                color, arrow = (_ACCENT_BAD if higher_is_bad else _ACCENT_GOOD), "↑"
            elif trend == "decreasing":
                color, arrow = (_ACCENT_GOOD if higher_is_bad else _ACCENT_BAD), "↓"
            else:
                color, arrow = _MUTED, "→"
            sig_label = "significant" if significant else "not significant"
            return (
                f'<span style="color:{color};font-weight:600">{arrow} {slope:+.3f}/yr</span> '
                f'<span style="font-size:0.68rem;color:{_MUTED}">({sig_label}, p={p_value:.3f})</span>'
            )

        rows_tr = ""
        for localidad in df_s["localidad"].unique():
            lst_row = trends_df[(trends_df["localidad"] == localidad) & (trends_df["variable"] == "lst_celsius")]
            ndvi_row = trends_df[(trends_df["localidad"] == localidad) & (trends_df["variable"] == "ndvi")]
            lst_html = _trend_badge(lst_row.iloc[0], higher_is_bad=True) if not lst_row.empty else "N/A"
            ndvi_html = _trend_badge(ndvi_row.iloc[0], higher_is_bad=False) if not ndvi_row.empty else "N/A"
            rows_tr += f"""
            <tr>
              <td class="loc-name">{localidad}</td>
              <td>{lst_html}</td>
              <td>{ndvi_html}</td>
            </tr>"""

        st.markdown(f"""
        <div class="rank-wrap">
          <table class="rank-table">
            <thead>
              <tr><th>Locality</th><th>LST Trend</th><th>NDVI Trend</th></tr>
            </thead>
            <tbody>{rows_tr}</tbody>
          </table>
        </div>
        <p style="font-size:.72rem;color:{_MUTED};margin-top:.6rem">
          Mann-Kendall non-parametric trend test (α = 0.05); slope from linear regression, in units per year.
        </p>
        """, unsafe_allow_html=True)

    except Exception as exc:
        st.warning(f"Could not compute trend analysis: {exc}")

    # ── UHI scenario simulator ──────────────────────────────────────────────────

    st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">UHI Scenario Simulator</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

    try:
        model = _cached_model(df)

        st.markdown('<div class="sim-wrap">', unsafe_allow_html=True)
        st.markdown(
            f'<p style="font-size:.8rem;color:{_MUTED};margin:0 0 1.2rem">Adjust vegetation and urban cover to estimate the resulting surface temperature.</p>',
            unsafe_allow_html=True,
        )

        sc1, sc2, sc3 = st.columns([2, 2, 1])
        with sc1:
            sim_ndvi = st.slider("Hypothetical NDVI", 0.0, 1.0, 0.30, 0.01)
        with sc2:
            sim_urban = st.slider("Hypothetical % Urban", 0, 100, 60, 1)
        with sc3:
            st.write("")
            st.write("")
            run_sim = st.button("Calculate LST", use_container_width=True)

        if run_sim:
            pred = predict_lst(ndvi=sim_ndvi, urban_pct=float(sim_urban), model=model)
            st.markdown(f"""
            <div class="sim-result-box">
              <div class="sim-result-temp">{pred:.2f} °C</div>
              <div class="sim-result-meta">
                Estimated LST for NDVI = <span>{sim_ndvi:.2f}</span> and urban cover = <span>{sim_urban} %</span><br>
                Model R² = <span>{model['r_squared']:.3f}</span> &nbsp;·&nbsp; n = <span>{model['n_samples']}</span> observations<br>
                Model: LST ~ β₀ + β₁·NDVI + β₂·urban_pct
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    except Exception as exc:
        st.warning(f"Simulator unavailable: {exc}")


# ── TAB 3: Mitigation Strategies ────────────────────────────────────────────────

with tab3:

    st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Urban Heat Mitigation Strategies</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

    strat_df = get_strategies_df()
    cat_sum  = get_category_summary()

    # Strategy KPIs
    sk1, sk2, sk3, sk4 = st.columns(4)
    best = strat_df.iloc[0]
    sk1.metric("Identified strategies", len(strat_df))
    sk2.metric("Largest LST reduction", f"{abs(best['lst_reduction_c']):.1f} °C", delta=best["name"])
    sk3.metric("Intervention categories", len(cat_sum))
    sk4.metric("Priority localities", "Kennedy · Cd. Bolívar")

    # Strategy matrix
    st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Strategy Impact Matrix</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

    cost_color = {"Low": _ACCENT_GOOD, "Medium": _ACCENT_WARM, "High": _ACCENT_BAD}
    rows_s = ""
    for _, row in strat_df.iterrows():
        bar_w = int(abs(row["lst_reduction_c"]) / 3.0 * 100)
        cc = cost_color.get(row["cost_level"], _MUTED)
        rows_s += f"""
        <tr>
          <td style="font-weight:600">{row['name']}</td>
          <td><span style="background:rgba(96,165,250,0.15);color:{_ACCENT_BLUE};padding:2px 8px;border-radius:4px;font-size:.75rem">{row['category']}</span></td>
          <td>
            <div style="display:flex;align-items:center;gap:8px">
              <div style="width:{bar_w}%;height:6px;background:#F97316;border-radius:3px;min-width:4px"></div>
              <span style="color:{_ACCENT_BAD};font-weight:600">{row['lst_reduction_c']:.1f} °C</span>
            </div>
          </td>
          <td style="color:{_ACCENT_GOOD};font-weight:600">+{row['ndvi_increase']:.2f}</td>
          <td><span style="color:{cc};font-weight:600">{row['cost_level']}</span></td>
          <td style="font-size:.78rem;color:{_MUTED}">{row['timeframe']}</td>
          <td style="font-size:.75rem">{row['co_benefits']}</td>
        </tr>"""

    st.markdown(f"""
    <div class="rank-wrap">
      <table class="rank-table">
        <thead>
          <tr>
            <th>Strategy</th><th>Category</th><th>LST Reduction</th>
            <th>Δ NDVI</th><th>Cost</th><th>Timeframe</th><th>Co-benefits</th>
          </tr>
        </thead>
        <tbody>{rows_s}</tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)

    # Analysis by locality
    st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Priority Strategies by Locality</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

    try:
        ranking_loc = _cached_rank(df)
        loc_ordered = ranking_loc["localidad"].tolist()
    except Exception:
        loc_ordered = ["Kennedy", "Ciudad Bolívar", "Chapinero", "Usaquén"]

    lc1, lc2 = st.columns(2)
    cols_loc = [lc1, lc2, lc1, lc2]

    for idx, localidad in enumerate(loc_ordered):
        loc_strat = get_strategies_for_localidad(localidad)
        accent = list(LOCALIDAD_COLORS.values())[idx % len(LOCALIDAD_COLORS)]
        items_html = "".join(
            f'<li style="margin:4px 0;font-size:.82rem"><strong>{r["name"]}</strong>'
            f'<span style="color:{_MUTED};margin-left:8px">{r["lst_reduction_c"]:.1f} °C · {r["cost_level"]}</span></li>'
            for _, r in loc_strat.head(4).iterrows()
        )
        with cols_loc[idx]:
            st.markdown(f"""
            <div class="kpi-card" style="--accent:{accent};padding:1.2rem 1.4rem;margin-bottom:1rem">
              <div class="kpi-label" style="margin-bottom:.6rem">{localidad}</div>
              <ul style="margin:0;padding:0;list-style:none">{items_html}</ul>
            </div>
            """, unsafe_allow_html=True)

    # Mitigation simulator
    st.markdown('<div class="section-header"><div class="section-dot"></div><h3 class="section-title">Mitigation Simulator</h3><div class="section-line"></div></div>', unsafe_allow_html=True)

    st.markdown('<div class="sim-wrap">', unsafe_allow_html=True)
    st.markdown(
        f'<p style="font-size:.8rem;color:{_MUTED};margin:0 0 1.2rem">Select strategies and a locality to estimate the resulting surface temperature reduction.</p>',
        unsafe_allow_html=True,
    )

    ms1, ms2 = st.columns([2, 1])
    with ms1:
        selected_strats = st.multiselect(
            "Strategies to implement",
            options=strat_df["id"].tolist(),
            format_func=lambda x: strat_df.loc[strat_df["id"] == x, "name"].values[0],
            default=["urban_trees", "parks_green_corridors"],
            key="mit_strategies",
        )
    with ms2:
        sim_loc = st.selectbox("Base locality", options=loc_ordered, key="mit_localidad")

    if selected_strats:
        try:
            loc_data = df[df["localidad"] == sim_loc]
            base_lst  = float(loc_data["lst_celsius"].iloc[-1]) if not loc_data.empty else 19.0
            base_ndvi = float(loc_data["ndvi"].iloc[-1]) if not loc_data.empty else 0.28

            result = simulate_mitigation(base_lst, base_ndvi, selected_strats)

            mr1, mr2, mr3 = st.columns(3)
            mr1.metric("Current LST", f"{result['lst_before']:.2f} °C")
            mr2.metric("Projected LST", f"{result['lst_after']:.2f} °C", delta=f"{result['lst_delta']:+.2f} °C", delta_color="inverse")
            mr3.metric("Total reduction", f"{abs(result['lst_delta']):.2f} °C")

            # Before/after chart
            fig_mit = go.Figure()
            fig_mit.add_trace(go.Bar(
                x=["Current situation", "With strategies"],
                y=[result["lst_before"], result["lst_after"]],
                marker_color=["#F97316", "#34D399"],
                text=[f"{result['lst_before']:.2f} °C", f"{result['lst_after']:.2f} °C"],
                textposition="outside",
            ))
            fig_mit.update_layout(**_P, title=f"Mitigation Impact · {sim_loc}",
                                  yaxis_title="LST (°C)", showlegend=False)
            st.plotly_chart(fig_mit, use_container_width=True)

        except Exception as exc:
            st.warning(f"Error in mitigation simulator: {exc}")
    else:
        st.info("Select at least one strategy to simulate the impact.")

    st.markdown('</div>', unsafe_allow_html=True)


# ── Footer ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="footer-bar">
  <span>Sources: MODIS MOD11A2 · Landsat 8/9 · Sentinel-2 SR · Dynamic World V1 · ESA WorldCover — via Google Earth Engine &nbsp;·&nbsp; NASA NEX-GDDP-CMIP6</span>
  <span>Localities of Bogotá D.C., Colombia · 2015 – 2025 &nbsp;·&nbsp; Step 1: Colombia · Step 2: Bogotá · Step 3: Mitigation</span>
</div>
""", unsafe_allow_html=True)
