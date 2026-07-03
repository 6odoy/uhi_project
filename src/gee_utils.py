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
