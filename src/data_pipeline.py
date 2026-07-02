import ee
import pandas as pd
from pathlib import Path

from src.gee_utils import (
    get_localidades,
    get_lst_modis,
    get_ndvi_sentinel,
    get_urban_fraction,
    LOCALIDADES_INTERES,
    YEAR_START,
    YEAR_END,
    LOCALIDADES_ASSET,
)


def extract_annual_stats(
    output_path: str = "data/processed/uhi_bogota.parquet",
) -> pd.DataFrame:
    localidades_fc = get_localidades(LOCALIDADES_ASSET)

    records: list[dict] = []
    for localidad in LOCALIDADES_INTERES:
        feature = localidades_fc.filter(
            ee.Filter.eq("LocNombre", localidad)
        ).first()
        geometry = feature.geometry()

        for year in range(YEAR_START, YEAR_END + 1):
            print(f"Procesando {localidad} {year}...")
            records.append(
                {
                    "localidad": localidad,
                    "year": year,
                    "lst_celsius": get_lst_modis(geometry, year),
                    "ndvi": get_ndvi_sentinel(geometry, year),
                    "urban_pct": get_urban_fraction(geometry, year),
                }
            )

    df = pd.DataFrame(records)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output, index=False)

    return df


def load_processed_data(
    path: str = "data/processed/uhi_bogota.parquet",
) -> pd.DataFrame:
    file = Path(path)
    if not file.exists():
        print(
            f"Archivo '{path}' no encontrado. "
            "Ejecuta extract_annual_stats() primero para generar los datos."
        )
        return pd.DataFrame()

    return pd.read_parquet(file)


def validate_dataframe(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total_rows": 0,
            "null_counts": {},
            "year_range": (),
            "localidades": [],
            "has_gaps": True,
        }

    years = df["year"].unique()
    localidades = df["localidad"].unique()
    expected_rows = len(years) * len(localidades)

    return {
        "total_rows": len(df),
        "null_counts": df.isnull().sum().to_dict(),
        "year_range": (int(years.min()), int(years.max())),
        "localidades": sorted(localidades.tolist()),
        "has_gaps": len(df) < expected_rows,
    }


if __name__ == "__main__":
    df = extract_annual_stats()
    stats = validate_dataframe(df)
    print(stats)
