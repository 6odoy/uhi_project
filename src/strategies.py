"""Urban heat island mitigation strategies for Bogotá."""

from __future__ import annotations

import pandas as pd

STRATEGIES: list[dict] = [
    {
        "id": "urban_trees",
        "name": "Urban trees and urban forestry",
        "category": "Green Infrastructure",
        "lst_reduction_c": -2.5,
        "ndvi_increase": 0.08,
        "cost_level": "Medium",
        "timeframe": "Medium (3-5 years)",
        "priority_localidades": ["Ciudad Bolívar", "Kennedy", "Chapinero", "Usaquén"],
        "co_benefits": "Improves air quality, reduces runoff, and boosts urban biodiversity.",
        "description": (
            "Planting and maintaining trees along streets, parks, and public spaces. "
            "Reduces temperature through shade and evapotranspiration."
        ),
    },
    {
        "id": "green_roofs",
        "name": "Green roofs and vertical gardens",
        "category": "Green Infrastructure",
        "lst_reduction_c": -1.8,
        "ndvi_increase": 0.05,
        "cost_level": "High",
        "timeframe": "Medium (3-5 years)",
        "priority_localidades": ["Chapinero", "Kennedy", "Ciudad Bolívar"],
        "co_benefits": "Thermally insulates buildings, retains rainwater, and increases biodiversity.",
        "description": (
            "Installation of vegetated roofs and walls on residential and commercial buildings. "
            "Reduces heat absorption on built surfaces."
        ),
    },
    {
        "id": "parks_green_corridors",
        "name": "Parks and green corridors",
        "category": "Green Infrastructure",
        "lst_reduction_c": -3.0,
        "ndvi_increase": 0.12,
        "cost_level": "High",
        "timeframe": "Long (>5 years)",
        "priority_localidades": ["Ciudad Bolívar", "Kennedy", "Usaquén"],
        "co_benefits": "Promotes recreation, ecological connectivity, and community mental well-being.",
        "description": (
            "Creation and rehabilitation of local parks and interconnected green corridors. "
            "Produces the strongest cooling effect by combining dense vegetation with permeable ground."
        ),
    },
    {
        "id": "cool_pavements",
        "name": "Reflective pavements and surfaces",
        "category": "Gray Infrastructure",
        "lst_reduction_c": -1.2,
        "ndvi_increase": 0.0,
        "cost_level": "Medium",
        "timeframe": "Short (1-2 years)",
        "priority_localidades": ["Kennedy", "Ciudad Bolívar"],
        "co_benefits": "Reduces energy consumption for public lighting and improves pedestrian comfort.",
        "description": (
            "Replacing or coating dark pavements with high solar-reflectance materials. "
            "Reduces radiation absorption on roads and parking areas."
        ),
    },
    {
        "id": "cool_roofs",
        "name": "Cool roofs",
        "category": "Gray Infrastructure",
        "lst_reduction_c": -1.5,
        "ndvi_increase": 0.0,
        "cost_level": "Low",
        "timeframe": "Short (1-2 years)",
        "priority_localidades": ["Ciudad Bolívar", "Kennedy", "Chapinero"],
        "co_benefits": "Reduces energy consumption for cooling and extends roof lifespan.",
        "description": (
            "Application of reflective paints or materials on residential and building roofs. "
            "The lowest-cost and fastest-to-implement intervention."
        ),
    },
    {
        "id": "urban_water_bodies",
        "name": "Urban water bodies",
        "category": "Green Infrastructure",
        "lst_reduction_c": -2.0,
        "ndvi_increase": 0.02,
        "cost_level": "Medium",
        "timeframe": "Medium (3-5 years)",
        "priority_localidades": ["Kennedy", "Ciudad Bolívar", "Usaquén"],
        "co_benefits": "Increases relative humidity, provides aquatic habitat, and adds aesthetic value to public space.",
        "description": (
            "Construction and rehabilitation of fountains, canals, and ponds in public spaces. "
            "Evaporative cooling lowers air temperature and that of adjacent surfaces."
        ),
    },
    {
        "id": "density_ventilation_zoning",
        "name": "Density regulation and ventilation corridors",
        "category": "Urban Planning",
        "lst_reduction_c": -0.8,
        "ndvi_increase": 0.0,
        "cost_level": "Low",
        "timeframe": "Long (>5 years)",
        "priority_localidades": ["Chapinero", "Kennedy", "Ciudad Bolívar"],
        "co_benefits": "Improves air quality, reduces noise pollution, and organizes urban growth.",
        "description": (
            "Regulatory update to limit building density and open wind corridors. "
            "Facilitates fresh air circulation and dissipates accumulated heat."
        ),
    },
    {
        "id": "wetland_restoration",
        "name": "Peri-urban wetland restoration",
        "category": "Green Infrastructure",
        "lst_reduction_c": -2.2,
        "ndvi_increase": 0.10,
        "cost_level": "Medium",
        "timeframe": "Long (>5 years)",
        "priority_localidades": ["Ciudad Bolívar", "Kennedy", "Usaquén"],
        "co_benefits": "Captures carbon, filters water, reduces flood risk, and protects native biodiversity.",
        "description": (
            "Recovery and protection of wetlands on Bogotá's urban periphery. "
            "Their large water mass and hygrophilous vegetation produce sustained evaporative cooling."
        ),
    },
]


def get_strategies_df() -> pd.DataFrame:
    """Return all strategies as a DataFrame sorted by impact_score."""
    df = pd.DataFrame(STRATEGIES)
    df["impact_score"] = (
        df["lst_reduction_c"].abs() * 0.7 + df["ndvi_increase"] * 10 * 0.3
    )
    return df.sort_values("impact_score", ascending=False).reset_index(drop=True)


def get_strategies_for_localidad(localidad: str) -> pd.DataFrame:
    """Filter priority strategies for a locality and sort them by impact_score."""
    df = get_strategies_df()
    mask = df["priority_localidades"].apply(lambda locs: localidad in locs)
    return df[mask].reset_index(drop=True)


def simulate_mitigation(
    lst_current: float,
    ndvi_current: float,
    strategy_ids: list[str],
) -> dict:
    """Compute projected LST and NDVI when applying the given strategies."""
    id_to_strategy = {s["id"]: s for s in STRATEGIES}
    lst_delta = 0.0
    ndvi_delta = 0.0
    for sid in strategy_ids:
        strategy = id_to_strategy[sid]
        lst_delta += strategy["lst_reduction_c"]
        ndvi_delta += strategy["ndvi_increase"]
    return {
        "lst_before": lst_current,
        "lst_after": lst_current + lst_delta,
        "ndvi_before": ndvi_current,
        "ndvi_after": ndvi_current + ndvi_delta,
        "lst_delta": lst_delta,
        "ndvi_delta": ndvi_delta,
    }


def get_category_summary() -> pd.DataFrame:
    """Group strategies by category and compute impact statistics."""
    df = pd.DataFrame(STRATEGIES)
    summary = (
        df.groupby("category", as_index=False)
        .agg(
            n_strategies=("id", "count"),
            avg_lst_reduction=("lst_reduction_c", "mean"),
            avg_ndvi_increase=("ndvi_increase", "mean"),
        )
    )
    return summary
