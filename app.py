import streamlit as st

st.set_page_config(page_title="UHI Bogotá", layout="wide", page_icon="🌡️")

import pandas as pd
import plotly.express as px

from src.data_pipeline import load_processed_data
from src.analysis import (
    compute_correlations,
    rank_localidades,
    fit_lst_model,
    predict_lst,
)
from src.gee_utils import initialize_gee


# ── GEE ──────────────────────────────────────────────────────────────────────

@st.cache_resource
def _init_gee() -> bool:
    try:
        gee_cfg = st.secrets.get("gee", None)
        if not gee_cfg:
            return False
        project = gee_cfg.get("project", "ee-uhi-bogota")
        sa_info = dict(gee_cfg.get("service_account", {})) or None
        initialize_gee(project=project, service_account_info=sa_info)
        import ee
        ee.Number(1).getInfo()
        return True
    except Exception:
        return False


@st.cache_resource
def _build_gee_map():
    try:
        import geemap.foliumap as geemap_folium
        m = geemap_folium.Map(center=[4.65, -74.08], zoom=11)
        return m
    except Exception:
        return None


gee_available = _init_gee()


# ── Carga y caché de datos ────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def _load_data() -> pd.DataFrame:
    return load_processed_data()


@st.cache_data(ttl=3600)
def _cached_correlations(data: pd.DataFrame) -> pd.DataFrame:
    return compute_correlations(data)


@st.cache_data(ttl=3600)
def _cached_rank(data: pd.DataFrame) -> pd.DataFrame:
    return rank_localidades(data)


@st.cache_data(ttl=3600)
def _cached_fit_model(data: pd.DataFrame) -> dict:
    return fit_lst_model(data)


try:
    df_raw = _load_data()
except Exception as exc:
    st.error(
        f"Error al cargar los datos: {exc}. "
        "Verifica que el archivo `data/processed/uhi_bogota.parquet` exista y sea válido."
    )
    st.stop()

if df_raw.empty:
    st.warning("No hay datos procesados. Ejecuta data_pipeline.py primero.")
    st.stop()


# ── Sidebar ───────────────────────────────────────────────────────────────────

st.sidebar.title("Filtros")

all_localidades = sorted(df_raw["localidad"].unique().tolist())
selected_localidades = st.sidebar.multiselect(
    "Localidades",
    options=all_localidades,
    default=all_localidades,
)
if not selected_localidades:
    selected_localidades = all_localidades

year_range = st.sidebar.slider("Rango temporal", 2015, 2025, (2015, 2025))

_VAR_OPTIONS = {"LST (°C)": "lst_celsius", "NDVI": "ndvi", "% Urbano": "urban_pct"}
variable_label = st.sidebar.radio("Variable principal", options=list(_VAR_OPTIONS.keys()))
variable_col = _VAR_OPTIONS[variable_label]


# ── Filtrado ──────────────────────────────────────────────────────────────────

df = df_raw[
    df_raw["localidad"].isin(selected_localidades)
    & df_raw["year"].between(year_range[0], year_range[1])
].copy()

if df.empty:
    st.warning("Sin datos para la selección actual. Amplía el rango de años o localidades.")
    st.stop()

first_year = int(df["year"].min())
last_year = int(df["year"].max())


def _mean_year(col: str, year: int) -> float:
    subset = df[df["year"] == year]
    return float(subset[col].mean()) if not subset.empty else float("nan")


# ── Título ────────────────────────────────────────────────────────────────────

st.title("🌡️ Monitoreo de Islas de Calor Urbano — Bogotá")


# ── Sección 1: KPIs ───────────────────────────────────────────────────────────

k1, k2, k3, k4 = st.columns(4)

lst_now = _mean_year("lst_celsius", last_year)
lst_before = _mean_year("lst_celsius", first_year)
k1.metric(
    "LST promedio actual",
    f"{lst_now:.2f} °C",
    delta=f"{lst_now - lst_before:+.2f} vs {first_year}",
    delta_color="inverse",
)

ndvi_now = _mean_year("ndvi", last_year)
ndvi_before = _mean_year("ndvi", first_year)
k2.metric(
    "NDVI promedio actual",
    f"{ndvi_now:.3f}",
    delta=f"{ndvi_now - ndvi_before:+.3f} vs {first_year}",
)

urban_now = _mean_year("urban_pct", last_year)
urban_before = _mean_year("urban_pct", first_year)
k3.metric(
    "% Urbano promedio",
    f"{urban_now:.1f} %",
    delta=f"{urban_now - urban_before:+.1f} pp vs {first_year}",
    delta_color="inverse",
)

try:
    _ranking_kpi = _cached_rank(df)
    critical_loc = _ranking_kpi.iloc[0]["localidad"]
    critical_change = float(_ranking_kpi.iloc[0]["lst_change"])
    k4.metric(
        "Localidad más crítica",
        critical_loc,
        delta=f"ΔT = {critical_change:+.2f} °C",
        delta_color="inverse",
    )
except Exception:
    k4.metric("Localidad más crítica", "N/D")

st.markdown("---")


# ── Sección 2: Mapa interactivo ───────────────────────────────────────────────

st.subheader("Mapa de temperatura superficial")

if gee_available:
    m = _build_gee_map()
    if m is not None:
        try:
            m.to_streamlit(height=500)
        except Exception as exc:
            st.info(f"No se pudo renderizar el mapa: {exc}")
    else:
        st.info("Mapa no disponible: no se pudo inicializar el objeto de mapa.")
else:
    st.info("Mapa no disponible: configura las credenciales de GEE en secrets.toml")

st.markdown("---")


# ── Sección 3: Series de tiempo ───────────────────────────────────────────────

st.subheader("Evolución temporal por localidad")

df_sorted = df.sort_values(["localidad", "year"])
col_ts1, col_ts2 = st.columns(2)

with col_ts1:
    fig_lst = px.line(
        df_sorted,
        x="year",
        y="lst_celsius",
        color="localidad",
        markers=True,
        title="Temperatura superficial (LST)",
        labels={"year": "Año", "lst_celsius": "LST (°C)", "localidad": "Localidad"},
    )
    fig_lst.update_layout(
        legend_title_text="Localidad",
        xaxis_title="Año",
        yaxis_title="LST (°C)",
    )
    st.plotly_chart(fig_lst, use_container_width=True)

with col_ts2:
    fig_ndvi = px.line(
        df_sorted,
        x="year",
        y="ndvi",
        color="localidad",
        markers=True,
        title="Índice de vegetación (NDVI)",
        labels={"year": "Año", "ndvi": "NDVI", "localidad": "Localidad"},
    )
    fig_ndvi.update_layout(
        legend_title_text="Localidad",
        xaxis_title="Año",
        yaxis_title="NDVI",
    )
    st.plotly_chart(fig_ndvi, use_container_width=True)

st.markdown("---")


# ── Sección 4: Correlaciones ──────────────────────────────────────────────────

st.subheader("Correlaciones entre variables")

try:
    corr_df = _cached_correlations(df)
    ndvi_lst = corr_df[corr_df["pair"] == "ndvi_vs_lst"].copy()
    overall_r = float(ndvi_lst["pearson_r"].mean()) if not ndvi_lst.empty else float("nan")

    scatter_title = (
        f"NDVI vs LST — Pearson r = {overall_r:.3f}"
        if not pd.isna(overall_r)
        else "NDVI vs LST"
    )
    fig_scatter = px.scatter(
        df,
        x="ndvi",
        y="lst_celsius",
        color="localidad",
        title=scatter_title,
        labels={"ndvi": "NDVI", "lst_celsius": "LST (°C)", "localidad": "Localidad"},
    )
    fig_scatter.update_layout(legend_title_text="Localidad")
    st.plotly_chart(fig_scatter, use_container_width=True)

    if not ndvi_lst.empty:
        corr_table = (
            ndvi_lst[["localidad", "pearson_r", "spearman_r"]]
            .rename(columns={
                "localidad": "Localidad",
                "pearson_r": "Pearson r (NDVI↔LST)",
                "spearman_r": "Spearman r (NDVI↔LST)",
            })
            .set_index("Localidad")
        )
        st.dataframe(corr_table.style.format("{:.3f}"), use_container_width=True)
except Exception as exc:
    st.warning(f"No se pudieron calcular las correlaciones: {exc}")

st.markdown("---")


# ── Sección 5: Ranking de localidades ────────────────────────────────────────

st.subheader("Ranking de localidades por criticidad")

try:
    ranking = _cached_rank(df)
    max_change_idx = int(ranking["lst_change"].idxmax())

    def _highlight_critical(row):
        if row.name == max_change_idx:
            return ["background-color: #ff4b4b; color: white"] * len(row)
        return [""] * len(row)

    ranking_display = ranking.rename(columns={
        "localidad": "Localidad",
        "lst_mean": "LST Media (°C)",
        "lst_last": "LST Último año (°C)",
        "lst_change": "Δ LST (°C)",
        "ndvi_mean": "NDVI Medio",
        "ndvi_change": "Δ NDVI",
        "urban_pct_last": "% Urbano",
    })
    fmt = {
        "LST Media (°C)": "{:.2f}",
        "LST Último año (°C)": "{:.2f}",
        "Δ LST (°C)": "{:.2f}",
        "NDVI Medio": "{:.3f}",
        "Δ NDVI": "{:.3f}",
        "% Urbano": "{:.1f}",
    }
    st.dataframe(
        ranking_display.style.apply(_highlight_critical, axis=1).format(fmt),
        use_container_width=True,
    )
except Exception as exc:
    st.warning(f"No se pudo generar el ranking: {exc}")

st.markdown("---")


# ── Sección 6: Simulador de escenarios ───────────────────────────────────────

st.subheader("Simulador de escenarios")

try:
    model = _cached_fit_model(df)
    sim_c1, sim_c2, sim_c3 = st.columns([1, 1, 1])

    with sim_c1:
        sim_ndvi = st.slider(
            "NDVI hipotético",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.01,
            help="Índice de vegetación normalizado (0 = sin vegetación, 1 = vegetación densa)",
        )
    with sim_c2:
        sim_urban = st.slider(
            "% Urbano hipotético",
            min_value=0,
            max_value=100,
            value=50,
            step=1,
            help="Porcentaje de cobertura de suelo urbano en la localidad",
        )
    with sim_c3:
        st.write("")
        st.write("")
        predict_btn = st.button("Predecir LST", type="primary", use_container_width=True)

    if predict_btn:
        predicted = predict_lst(ndvi=sim_ndvi, urban_pct=float(sim_urban), model=model)
        st.success(
            f"LST predicha: **{predicted:.2f} °C** "
            f"&nbsp;|&nbsp; R² del modelo: {model['r_squared']:.3f} "
            f"&nbsp;|&nbsp; n = {model['n_samples']}"
        )
except Exception as exc:
    st.warning(f"El simulador no está disponible: {exc}")


# ── Pie de página ─────────────────────────────────────────────────────────────

st.markdown("---")
st.caption(
    "Datos: MODIS, Landsat 8/9, Sentinel-2 vía Google Earth Engine | Localidades: Bogotá, Colombia"
)
