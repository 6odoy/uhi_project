"""
Genera datos sintéticos realistas para las 4 localidades de Bogotá (2015-2025).
Usa perfiles basados en literatura de UHI para Bogotá (2600 m.s.n.m.).
Reemplazar con datos reales ejecutando src/data_pipeline.py una vez que
el proyecto GCP y el asset de localidades estén configurados en GEE.
"""

import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)

# Perfiles base por localidad (valores medios reales de Bogotá)
# LST en °C, NDVI adimensional, urban_pct en %
PROFILES = {
    "Chapinero": {
        "lst_base": 17.5, "lst_trend": 0.07,
        "ndvi_base": 0.38, "ndvi_trend": -0.008,
        "urban_base": 62.0, "urban_trend": 0.5,
    },
    "Ciudad Bolívar": {
        "lst_base": 19.2, "lst_trend": 0.10,
        "ndvi_base": 0.28, "ndvi_trend": -0.012,
        "urban_base": 71.0, "urban_trend": 0.8,
    },
    "Usaquén": {
        "lst_base": 16.8, "lst_trend": 0.05,
        "ndvi_base": 0.47, "ndvi_trend": -0.005,
        "urban_base": 55.0, "urban_trend": 0.4,
    },
    "Kennedy": {
        "lst_base": 19.8, "lst_trend": 0.09,
        "ndvi_base": 0.22, "ndvi_trend": -0.010,
        "urban_base": 78.0, "urban_trend": 0.6,
    },
}

YEARS = list(range(2015, 2026))

records = []
for localidad, p in PROFILES.items():
    for i, year in enumerate(YEARS):
        lst = p["lst_base"] + p["lst_trend"] * i + rng.normal(0, 0.3)
        ndvi = p["ndvi_base"] + p["ndvi_trend"] * i + rng.normal(0, 0.015)
        urban = p["urban_base"] + p["urban_trend"] * i + rng.normal(0, 0.8)
        records.append({
            "localidad": localidad,
            "year": year,
            "lst_celsius": round(lst, 3),
            "ndvi": round(float(np.clip(ndvi, 0.0, 1.0)), 4),
            "urban_pct": round(float(np.clip(urban, 0.0, 100.0)), 2),
        })

df = pd.DataFrame(records)
out = Path("data/processed/uhi_bogota.parquet")
out.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(out, index=False)
print(f"Datos guardados: {len(df)} filas → {out}")
print(df.groupby("localidad")[["lst_celsius", "ndvi", "urban_pct"]].mean().round(3))
