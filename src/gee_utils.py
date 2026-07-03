"""Utilities for connecting to and querying Google Earth Engine."""

import ee
from google.oauth2 import service_account

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GEE_PROJECT: str = ""  # set at runtime via initialize_gee()

LOCALIDADES_ASSET: str = "projects/uhi-bogota/assets/localidades_bogota"

# Nombre real de la propiedad del asset que identifica la localidad — viene
# del dataset oficial de datos abiertos de Bogotá (Nataliagarzon/Localidades
# en GitHub, espejo del portal IDECA). El asset se subió como shapefile
# (.zip), que trunca los nombres de campo ESRI a 10 caracteres: el campo
# original "Nombre de la localidad" quedó como "Nombre de".
LOCALIDAD_NAME_PROPERTY: str = "Nombre de"

LOCALIDADES_INTERES: list[str] = [
    "Chapinero",
    "Ciudad Bolívar",
    "Usaquén",
    "Kennedy",
]

# El asset trae los nombres en mayúsculas y sin tildes (formato de datos
# abiertos de Bogotá) — mapeo nombre canónico (usado en todo el dashboard)
# → valor real de la propiedad en el asset, solo para filtrar en GEE.
LOCALIDAD_ASSET_NAMES: dict[str, str] = {
    "Chapinero": "CHAPINERO",
    "Ciudad Bolívar": "CIUDAD BOLIVAR",
    "Usaquén": "USAQUEN",
    "Kennedy": "KENNEDY",
}

YEAR_START: int = 2015
YEAR_END: int = 2025

# Dataset IDs
_MODIS_LST = "MODIS/061/MOD11A2"
_LANDSAT8 = "LANDSAT/LC08/C02/T1_L2"
_LANDSAT9 = "LANDSAT/LC09/C02/T1_L2"
_SENTINEL2 = "COPERNICUS/S2_SR_HARMONIZED"
_ESA_WORLDCOVER = "ESA/WorldCover/v200"
_DYNAMIC_WORLD = "GOOGLE/DYNAMICWORLD/V1"
_CMIP6_GDDP = "NASA/GDDP-CMIP6"

# ---------------------------------------------------------------------------
# Paso 1 — Clima nacional Colombia (CMIP6 vía GEE, en vez del portal WB CCKP)
# ---------------------------------------------------------------------------

COLOMBIA_BOUNDARY_ASSET: str = "FAO/GAUL/2015/level0"

# Subconjunto de 6 modelos CMIP6 (de los 34 disponibles en NASA/GDDP-CMIP6)
# usado para estimar el rango de incertidumbre (min/mediana/max del ensemble).
# Verificado que las 3 bandas necesarias (tas, tasmax, pr) están presentes en
# los 3 escenarios para cada uno — CESM2 se descartó por no traer tasmax/tasmin.
CMIP6_MODELS: list[str] = [
    "ACCESS-CM2",
    "CanESM5",
    "MPI-ESM1-2-HR",
    "MIROC6",
    "NorESM2-MM",
    "GFDL-ESM4",
]

# Escenario CMIP6 → etiqueta de escenario usada en el resto del dashboard
# (SSP2-4.5 y SSP5-8.5 son los sucesores CMIP6 de RCP4.5/RCP8.5).
CMIP6_SCENARIO_MAP: dict[str, str] = {
    "historical": "historical",
    "ssp245": "rcp45",
    "ssp585": "rcp85",
}

_TX35_THRESHOLD_K: float = 308.15  # 35 °C en Kelvin


def get_colombia_geometry() -> ee.Geometry:
    """Return Colombia's national boundary geometry (FAO GAUL)."""
    countries = ee.FeatureCollection(COLOMBIA_BOUNDARY_ASSET)
    return countries.filter(ee.Filter.eq("ADM0_NAME", "Colombia")).geometry()


def get_cmip6_annual_series(
    model: str, scenario: str, geometry: ee.Geometry, start_year: int, end_year: int
) -> list[dict]:
    """Annual tas_mean (°C), tx35_days and pr_mm for `geometry`, for one CMIP6 model+scenario.

    Computes every year server-side and fetches the whole series in a single
    getInfo() call — looping year by year in Python would mean one network
    round-trip per year, which dominates runtime for a ~65-year series.
    """
    collection = (
        ee.ImageCollection(_CMIP6_GDDP)
        .filter(ee.Filter.eq("model", model))
        .filter(ee.Filter.eq("scenario", scenario))
    )

    def _year_stats(y: ee.Number) -> ee.Feature:
        y = ee.Number(y)
        start = ee.Date.fromYMD(y, 1, 1)
        end = start.advance(1, "year")
        year_col = collection.filterDate(start, end)

        tas_c = year_col.select("tas").mean().subtract(273.15).rename("tas_mean")
        tx35 = (
            year_col.select("tasmax")
            .map(lambda img: img.gt(_TX35_THRESHOLD_K))
            .sum()
            .rename("tx35_days")
        )
        pr_mm = (
            year_col.select("pr")
            .map(lambda img: img.multiply(86400))  # kg m-2 s-1 → mm/día
            .sum()
            .rename("pr_mm")
        )

        combined = tas_c.addBands(tx35).addBands(pr_mm)
        stats = combined.reduceRegion(
            reducer=ee.Reducer.mean(), geometry=geometry, scale=27830, maxPixels=1e9
        )
        return ee.Feature(None, stats.set("year", y))

    years = ee.List.sequence(start_year, end_year)
    fc = ee.FeatureCollection(years.map(_year_stats))
    return [f["properties"] for f in fc.getInfo()["features"]]


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def initialize_gee(
    project: str, service_account_info: dict | None = None
) -> None:
    """Initialize the GEE session with either local or service-account credentials."""
    try:
        if service_account_info is None:
            ee.Initialize(project=project)
        else:
            # Service account path is used in production (Streamlit Cloud / Cloud Run)
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=["https://www.googleapis.com/auth/earthengine"],
            )
            ee.Initialize(credentials=credentials, project=project)
    except Exception as exc:
        print(f"[gee_utils] GEE initialization failed: {exc}")


# ---------------------------------------------------------------------------
# Asset helpers
# ---------------------------------------------------------------------------


def get_localidades(asset_path: str) -> ee.FeatureCollection:
    """Load the localidades FeatureCollection and keep only the ones of interest."""
    return ee.FeatureCollection(asset_path).filter(
        ee.Filter.inList(LOCALIDAD_NAME_PROPERTY, list(LOCALIDAD_ASSET_NAMES.values()))
    )


# ---------------------------------------------------------------------------
# Indicator queries
# ---------------------------------------------------------------------------


def get_lst_image_celsius(year: int, geometry: ee.Geometry | None = None) -> ee.Image:
    """Mean JJA daytime LST composite (°C) from MODIS MOD11A2 for the given year."""
    collection = (
        ee.ImageCollection(_MODIS_LST)
        .filterDate(f"{year}-06-01", f"{year}-08-31")
        .select("LST_Day_1km")
    )
    if geometry is not None:
        collection = collection.filterBounds(geometry)

    image = collection.mean().multiply(0.02).subtract(273.15).rename("LST_Celsius")
    return image.clip(geometry) if geometry is not None else image


def get_tile_url(image: ee.Image, vis_params: dict) -> str:
    """Return an XYZ tile URL template for a GEE image (for use with folium/leaflet)."""
    map_id_dict = ee.Image(image).getMapId(vis_params)
    return map_id_dict["tile_fetcher"].url_format


def get_lst_modis(geometry: ee.Geometry, year: int) -> float | None:
    """Return mean daytime LST (°C) from MODIS MOD11A2 for the given year and geometry."""
    try:
        collection = (
            ee.ImageCollection(_MODIS_LST)
            .filterDate(f"{year}-06-01", f"{year}-08-31")  # JJA for seasonal consistency
            .filterBounds(geometry)
            .select("LST_Day_1km")
        )

        if collection.size().getInfo() == 0:
            return None

        # Scale factor 0.02 K → Celsius
        mean_image = collection.mean().multiply(0.02).subtract(273.15)
        value: float = mean_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geometry,
            scale=1000,
            maxPixels=1e9,
        ).get("LST_Day_1km").getInfo()

        return value
    except Exception as exc:
        print(f"[gee_utils] get_lst_modis failed (year={year}): {exc}")
        return None


def get_ndvi_sentinel(geometry: ee.Geometry, year: int) -> float | None:
    """Return mean annual NDVI from Sentinel-2 SR for the given year and geometry."""
    try:
        collection = (
            ee.ImageCollection(_SENTINEL2)
            .filterDate(f"{year}-01-01", f"{year}-12-31")
            .filterBounds(geometry)
            # 40% en vez de 20%: Bogotá es una zona muy nublada — con 20%
            # algunos años quedan con 0 imágenes disponibles.
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
        )

        if collection.size().getInfo() == 0:
            return None

        ndvi_collection = collection.map(
            lambda img: img.normalizedDifference(["B8", "B4"]).rename("NDVI")
        )

        value: float = (
            ndvi_collection.mean()
            .reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=10,
                maxPixels=1e9,
            )
            .get("NDVI")
            .getInfo()
        )

        return value
    except Exception as exc:
        print(f"[gee_utils] get_ndvi_sentinel failed (year={year}): {exc}")
        return None


def get_urban_fraction(geometry: ee.Geometry, year: int) -> float | None:
    """Return the percentage of pixels classified as urban (class 6) in Dynamic World V1."""
    try:
        collection = (
            ee.ImageCollection(_DYNAMIC_WORLD)
            .filterDate(f"{year}-01-01", f"{year}-12-31")
            .filterBounds(geometry)
            .select("label")
        )

        if collection.size().getInfo() == 0:
            return None

        mode_image = collection.mode()

        # Count total pixels and urban pixels separately to get a fraction
        total = mode_image.reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=geometry,
            scale=10,
            maxPixels=1e9,
        ).get("label").getInfo()

        if not total:
            return None

        urban_mask = mode_image.eq(6)  # class 6 = built area
        urban_count = urban_mask.reduceRegion(
            reducer=ee.Reducer.sum(),
            geometry=geometry,
            scale=10,
            maxPixels=1e9,
        ).get("label").getInfo()

        return (urban_count / total) * 100.0
    except Exception as exc:
        print(f"[gee_utils] get_urban_fraction failed (year={year}): {exc}")
        return None
