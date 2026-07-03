import re
from pathlib import Path

import pandas as pd
import numpy as np


_VAR_BOUNDS = {
    "tas_mean": ("tas_low", "tas_high"),
    "tx35_days": ("tx35_low", "tx35_high"),
    "pr_mm": ("pr_low", "pr_high"),
}

# variable de archivo → (columna central, columna low, columna high) en el parquet final
_RAW_VAR_COLUMNS = {
    "tas": ("tas_mean", "tas_low", "tas_high"),
    "tx35": ("tx35_days", "tx35_low", "tx35_high"),
    "pr": ("pr_mm", "pr_low", "pr_high"),
}

_SCENARIOS = ("historical", "rcp45", "rcp85")

_CENTRAL_NAME_HINTS = ("median", "mean", "p50", "central")
_LOW_NAME_HINTS = ("p10", "low", "min", "p5")
_HIGH_NAME_HINTS = ("p90", "high", "max", "p95")
_YEAR_NAME_HINTS = ("year", "anio", "año", "date")


def _match_hint(col_name: str, hints: tuple[str, ...]) -> bool:
    return any(h in col_name.lower() for h in hints)


def _read_variable_csv(path: Path) -> pd.DataFrame:
    """Lee un CSV crudo del World Bank CCKP y lo normaliza a columnas [year, central, low, high].

    Soporta dos formatos comunes de exportación del portal:
      - Largo:  una columna de año + 1-3 columnas numéricas (media/mediana, p10, p90).
      - Ancho:  columnas = años, filas = estadístico (media/mediana, p10, p90).
    """
    raw = pd.read_csv(path)
    raw.columns = [str(c).strip() for c in raw.columns]

    year_cols = [c for c in raw.columns if re.fullmatch(r"(19|20)\d{2}", c)]

    if year_cols:
        # Formato ancho: cada fila es un estadístico, cada columna un año.
        id_col = raw.columns[0]
        long = raw.melt(id_vars=[id_col], value_vars=year_cols, var_name="year", value_name="value")
        long["year"] = long["year"].astype(int)

        def _pick(hints: tuple[str, ...]) -> pd.Series:
            mask = long[id_col].astype(str).str.lower().apply(lambda v: any(h in v for h in hints))
            return long[mask].groupby("year")["value"].mean()

        central = _pick(_CENTRAL_NAME_HINTS)
        if central.empty:
            central = long.groupby("year")["value"].mean()
        low = _pick(_LOW_NAME_HINTS)
        high = _pick(_HIGH_NAME_HINTS)

        out = pd.DataFrame({"year": central.index, "central": central.values}).set_index("year")
        out["low"] = low
        out["high"] = high
        out = out.reset_index()

    else:
        # Formato largo: buscar columna de año + columnas de valor por nombre.
        year_col = next((c for c in raw.columns if _match_hint(c, _YEAR_NAME_HINTS)), raw.columns[0])
        value_cols = [c for c in raw.columns if c != year_col and pd.api.types.is_numeric_dtype(raw[c])]

        central_col = next((c for c in value_cols if _match_hint(c, _CENTRAL_NAME_HINTS)), None)
        low_col = next((c for c in value_cols if _match_hint(c, _LOW_NAME_HINTS)), None)
        high_col = next((c for c in value_cols if _match_hint(c, _HIGH_NAME_HINTS)), None)

        if central_col is None:
            remaining = [c for c in value_cols if c not in (low_col, high_col)]
            central_col = remaining[0] if remaining else value_cols[0]

        out = pd.DataFrame({
            "year": raw[year_col].astype(int),
            "central": raw[central_col],
            "low": raw[low_col] if low_col else np.nan,
            "high": raw[high_col] if high_col else np.nan,
        })

    out["low"] = out["low"].fillna(out["central"])
    out["high"] = out["high"].fillna(out["central"])
    return out.sort_values("year").reset_index(drop=True)


def process_wb_csvs(
    raw_dir: str = "data/raw/wb_climate",
    output_path: str = "data/processed/wb_colombia.parquet",
) -> pd.DataFrame:
    """Transforma los CSV crudos descargados del World Bank CCKP en el parquet del dashboard.

    Convención de nombres esperada en `raw_dir`: `<variable>_<escenario>.csv`,
    variable en {tas, tx35, pr}, escenario en {historical, rcp45, rcp85}.
    Ej.: tas_historical.csv, tas_rcp45.csv, tx35_rcp85.csv, pr_historical.csv
    """
    raw_path = Path(raw_dir)
    frames: list[pd.DataFrame] = []

    for scenario in _SCENARIOS:
        scenario_df: pd.DataFrame | None = None

        for variable, (central_col, low_col, high_col) in _RAW_VAR_COLUMNS.items():
            file_path = raw_path / f"{variable}_{scenario}.csv"
            if not file_path.exists():
                raise FileNotFoundError(
                    f"Falta '{file_path}'. Descarga el CSV correspondiente desde "
                    "https://climateknowledgeportal.worldbank.org/download-data "
                    f"(País: Colombia, Variable: {variable}, Escenario: {scenario}) "
                    f"y guárdalo con ese nombre exacto en '{raw_dir}/'."
                )

            parsed = _read_variable_csv(file_path).rename(
                columns={"central": central_col, "low": low_col, "high": high_col}
            )

            scenario_df = parsed if scenario_df is None else scenario_df.merge(parsed, on="year", how="outer")

        scenario_df["scenario"] = scenario
        frames.append(scenario_df)

    df = pd.concat(frames, ignore_index=True)
    df["year"] = df["year"].astype(int)

    float_cols = [c for c in df.columns if c not in ("year", "scenario")]
    df[float_cols] = df[float_cols].round(4)
    df = df[["year", "scenario", *(c for pair in _RAW_VAR_COLUMNS.values() for c in pair)]]

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, index=False)

    return df


def extract_colombia_cmip6(
    output_path: str = "data/processed/wb_colombia.parquet",
    hist_start: int = 1950,
    hist_end: int = 2014,
    proj_start: int = 2015,
    proj_end: int = 2080,
) -> pd.DataFrame:
    """Genera wb_colombia.parquet directamente desde CMIP6 vía Earth Engine.

    Alternativa a `process_wb_csvs()` cuando el portal del World Bank CCKP
    no está disponible: usa el mismo archivo climático (CMIP6) que alimenta
    ese portal, promediado sobre el territorio de Colombia con un ensemble
    de 6 modelos (ver `gee_utils.CMIP6_MODELS`) para estimar min/mediana/max.
    """
    from src.gee_utils import (
        get_colombia_geometry,
        get_cmip6_annual_series,
        CMIP6_MODELS,
        CMIP6_SCENARIO_MAP,
    )

    geometry = get_colombia_geometry()
    periods = {
        "historical": (hist_start, hist_end),
        "ssp245": (proj_start, proj_end),
        "ssp585": (proj_start, proj_end),
    }

    frames: list[pd.DataFrame] = []
    for cmip6_scenario, (start_year, end_year) in periods.items():
        model_frames = []
        for model in CMIP6_MODELS:
            print(f"Procesando {cmip6_scenario} / {model} ({start_year}-{end_year})...")
            records = get_cmip6_annual_series(model, cmip6_scenario, geometry, start_year, end_year)
            model_frames.append(pd.DataFrame(records))

        combined = pd.concat(model_frames, ignore_index=True)
        agg = combined.groupby("year").agg(
            tas_mean=("tas_mean", "median"), tas_low=("tas_mean", "min"), tas_high=("tas_mean", "max"),
            tx35_days=("tx35_days", "median"), tx35_low=("tx35_days", "min"), tx35_high=("tx35_days", "max"),
            pr_mm=("pr_mm", "median"), pr_low=("pr_mm", "min"), pr_high=("pr_mm", "max"),
        ).reset_index()
        agg["scenario"] = CMIP6_SCENARIO_MAP[cmip6_scenario]
        frames.append(agg)

    df = pd.concat(frames, ignore_index=True)
    df["year"] = df["year"].astype(int)

    float_cols = [c for c in df.columns if c not in ("year", "scenario")]
    df[float_cols] = df[float_cols].round(4)
    df = df[["year", "scenario", *(c for pair in _RAW_VAR_COLUMNS.values() for c in pair)]]

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, index=False)

    return df


def load_wb_data(path: str = "data/processed/wb_colombia.parquet") -> pd.DataFrame:
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        print(
            f"File not found: {path}\n"
            "Run:  python scripts/generate_wb_sample_data.py"
        )
        return pd.DataFrame()
    return pd.read_parquet(p)


def _baseline(df: pd.DataFrame, variable: str) -> float:
    mask = (df["scenario"] == "historical") & df["year"].between(1981, 2010)
    return float(df.loc[mask, variable].mean())


def _future_mean(df: pd.DataFrame, scenario: str, variable: str) -> float:
    mask = (df["scenario"] == scenario) & df["year"].between(2071, 2080)
    return float(df.loc[mask, variable].mean())


def get_temperature_kpis(df: pd.DataFrame) -> dict:
    hist = _baseline(df, "tas_mean")
    rcp45 = _future_mean(df, "rcp45", "tas_mean")
    rcp85 = _future_mean(df, "rcp85", "tas_mean")
    return {
        "hist_mean": round(hist, 3),
        "rcp45_2080": round(rcp45, 3),
        "rcp85_2080": round(rcp85, 3),
        "delta_rcp45": round(rcp45 - hist, 3),
        "delta_rcp85": round(rcp85 - hist, 3),
    }


def get_heatdays_kpis(df: pd.DataFrame) -> dict:
    hist = _baseline(df, "tx35_days")
    rcp45 = _future_mean(df, "rcp45", "tx35_days")
    rcp85 = _future_mean(df, "rcp85", "tx35_days")
    return {
        "hist_mean": round(hist, 3),
        "rcp45_2080": round(rcp45, 3),
        "rcp85_2080": round(rcp85, 3),
        "delta_rcp45": round(rcp45 - hist, 3),
        "delta_rcp85": round(rcp85 - hist, 3),
    }


def get_precip_kpis(df: pd.DataFrame) -> dict:
    hist = _baseline(df, "pr_mm")
    rcp45 = _future_mean(df, "rcp45", "pr_mm")
    rcp85 = _future_mean(df, "rcp85", "pr_mm")
    return {
        "hist_mean": round(hist, 3),
        "rcp45_2080": round(rcp45, 3),
        "rcp85_2080": round(rcp85, 3),
        "delta_rcp45": round(rcp45 - hist, 3),
        "delta_rcp85": round(rcp85 - hist, 3),
    }


def get_scenario_series(df: pd.DataFrame, variable: str) -> pd.DataFrame:
    if variable not in _VAR_BOUNDS:
        raise ValueError(f"variable must be one of {list(_VAR_BOUNDS)}, got '{variable}'")

    low_col, high_col = _VAR_BOUNDS[variable]

    hist = (
        df[df["scenario"] == "historical"][["year", variable, low_col, high_col]]
        .rename(columns={variable: "historical"})
        .drop(columns=[low_col, high_col])
    )

    rcp45 = (
        df[df["scenario"] == "rcp45"][["year", variable, low_col, high_col]]
        .rename(columns={variable: "rcp45", low_col: "rcp45_low", high_col: "rcp45_high"})
    )

    rcp85 = (
        df[df["scenario"] == "rcp85"][["year", variable, low_col, high_col]]
        .rename(columns={variable: "rcp85", low_col: "rcp85_low", high_col: "rcp85_high"})
    )

    all_years = pd.DataFrame({"year": range(df["year"].min(), df["year"].max() + 1)})

    out = (
        all_years
        .merge(hist, on="year", how="left")
        .merge(rcp45, on="year", how="left")
        .merge(rcp85, on="year", how="left")
    )

    return out.reset_index(drop=True)


def _init_gee_from_secrets(path: str = ".streamlit/secrets.toml") -> None:
    import tomllib
    from src.gee_utils import initialize_gee

    with open(path, "rb") as f:
        secrets = tomllib.load(f)

    gee_cfg = secrets["gee"]
    initialize_gee(
        project=gee_cfg["project"],
        service_account_info=gee_cfg.get("service_account") or None,
    )


if __name__ == "__main__":
    _init_gee_from_secrets()
    df = extract_colombia_cmip6()
    print(f"Guardado {len(df)} filas → data/processed/wb_colombia.parquet\n")
    print(df.groupby("scenario")[["tas_mean", "tx35_days", "pr_mm"]].agg(["min", "mean", "max"]).round(2))
