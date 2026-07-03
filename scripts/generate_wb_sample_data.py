"""
Genera datos sintéticos realistas de clima nacional para Colombia (1950–2080)
basados en rangos del IPCC AR6 y el World Bank Climate Change Knowledge Portal.

Escenarios:
  historical : 1950–2014
  rcp45      : 2015–2080
  rcp85      : 2015–2080

Ejecutar con:  python scripts/generate_wb_sample_data.py
Salida:        data/processed/wb_colombia.parquet
"""

import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)

HIST_START = 1950
HIST_END = 2014
PROJ_START = 2015
PROJ_END = 2080

TAS_BASE_1950 = 23.6          # °C promedio nacional Colombia ~1950
TAS_HIST_TREND = 0.02         # °C/año ≈ +0.2°C/década

TAS_2015_ANCHOR = TAS_BASE_1950 + TAS_HIST_TREND * (2014 - HIST_START)
TAS_RCP45_DELTA_2080 = 1.7    # adicionales vs 2015
TAS_RCP85_DELTA_2080 = 3.5

TAS_NOISE = 0.4
TAS_UNCERT = 0.4

TX35_BASE_1950 = 43.0         # días/año
TX35_HIST_TREND = 0.12        # días/año por año de calentamiento
TX35_2015_ANCHOR = TX35_BASE_1950 + TX35_HIST_TREND * (2014 - HIST_START)
TX35_RCP45_DELTA_2080 = 20.0
TX35_RCP85_DELTA_2080 = 55.0
TX35_NOISE = 3.0
TX35_UNCERT = 8.0

PR_BASE_1950 = 2780.0         # mm/año
PR_HIST_TREND = 0.3           # mm/año por año
PR_2015_ANCHOR = PR_BASE_1950 + PR_HIST_TREND * (2014 - HIST_START)
PR_RCP45_DELTA_2080 = PR_2015_ANCHOR * 0.03
PR_RCP85_DELTA_2080 = PR_2015_ANCHOR * 0.06
PR_NOISE_HIST = 80.0
PR_NOISE_PROJ45 = 100.0
PR_NOISE_PROJ85 = 130.0
PR_UNCERT = 150.0


def _linear(start_val: float, end_val: float, n_steps: int) -> np.ndarray:
    return np.linspace(start_val, end_val, n_steps)


def build_historical() -> pd.DataFrame:
    years = np.arange(HIST_START, HIST_END + 1)
    n = len(years)

    tas = _linear(TAS_BASE_1950, TAS_2015_ANCHOR, n) + rng.normal(0, TAS_NOISE * 0.5, n)
    tx35 = _linear(TX35_BASE_1950, TX35_2015_ANCHOR, n) + rng.normal(0, TX35_NOISE * 0.5, n)
    pr = _linear(PR_BASE_1950, PR_2015_ANCHOR, n) + rng.normal(0, PR_NOISE_HIST, n)

    return pd.DataFrame({
        "year": years,
        "scenario": "historical",
        "tas_mean": tas,
        "tas_low": tas - TAS_UNCERT,
        "tas_high": tas + TAS_UNCERT,
        "tx35_days": np.clip(tx35, 0, None),
        "tx35_low": np.clip(tx35 - TX35_UNCERT, 0, None),
        "tx35_high": tx35 + TX35_UNCERT,
        "pr_mm": np.clip(pr, 0, None),
        "pr_low": np.clip(pr - PR_UNCERT, 0, None),
        "pr_high": pr + PR_UNCERT,
    })


def build_projection(scenario: str) -> pd.DataFrame:
    years = np.arange(PROJ_START, PROJ_END + 1)
    n = len(years)

    if scenario == "rcp45":
        tas_end = TAS_2015_ANCHOR + TAS_RCP45_DELTA_2080
        tx35_end = TX35_2015_ANCHOR + TX35_RCP45_DELTA_2080
        pr_end = PR_2015_ANCHOR + PR_RCP45_DELTA_2080
        pr_noise = PR_NOISE_PROJ45
    else:
        tas_end = TAS_2015_ANCHOR + TAS_RCP85_DELTA_2080
        tx35_end = TX35_2015_ANCHOR + TX35_RCP85_DELTA_2080
        pr_end = PR_2015_ANCHOR + PR_RCP85_DELTA_2080
        pr_noise = PR_NOISE_PROJ85

    tas = _linear(TAS_2015_ANCHOR, tas_end, n) + rng.normal(0, TAS_NOISE * 0.3, n)
    tx35 = _linear(TX35_2015_ANCHOR, tx35_end, n) + rng.normal(0, TX35_NOISE * 0.3, n)
    pr = _linear(PR_2015_ANCHOR, pr_end, n) + rng.normal(0, pr_noise, n)

    return pd.DataFrame({
        "year": years,
        "scenario": scenario,
        "tas_mean": tas,
        "tas_low": tas - TAS_UNCERT,
        "tas_high": tas + TAS_UNCERT,
        "tx35_days": np.clip(tx35, 0, None),
        "tx35_low": np.clip(tx35 - TX35_UNCERT, 0, None),
        "tx35_high": tx35 + TX35_UNCERT,
        "pr_mm": np.clip(pr, 0, None),
        "pr_low": np.clip(pr - PR_UNCERT, 0, None),
        "pr_high": pr + PR_UNCERT,
    })


def generate() -> pd.DataFrame:
    frames = [
        build_historical(),
        build_projection("rcp45"),
        build_projection("rcp85"),
    ]
    df = pd.concat(frames, ignore_index=True)
    df["year"] = df["year"].astype(int)
    float_cols = [c for c in df.columns if c not in ("year", "scenario")]
    df[float_cols] = df[float_cols].round(4)
    return df


if __name__ == "__main__":
    df = generate()

    out = Path("data/processed/wb_colombia.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"Saved {len(df)} rows → {out}\n")

    summary = (
        df.groupby("scenario")[["tas_mean", "tx35_days", "pr_mm"]]
        .agg(["min", "mean", "max"])
        .round(2)
    )
    print(summary)
