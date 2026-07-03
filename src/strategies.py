"""Estrategias de mitigación de islas de calor urbano para Bogotá."""

from __future__ import annotations

import pandas as pd

STRATEGIES: list[dict] = [
    {
        "id": "urban_trees",
        "name": "Arbolado urbano y silvicultura urbana",
        "category": "Infraestructura Verde",
        "lst_reduction_c": -2.5,
        "ndvi_increase": 0.08,
        "cost_level": "Medio",
        "timeframe": "Mediano (3-5 años)",
        "priority_localidades": ["Ciudad Bolívar", "Kennedy", "Chapinero", "Usaquén"],
        "co_benefits": "Mejora calidad del aire, reduce escorrentía y aporta biodiversidad urbana.",
        "description": (
            "Siembra y mantenimiento de árboles en vías, parques y espacios públicos. "
            "Reduce temperatura por sombra y evapotranspiración."
        ),
    },
    {
        "id": "green_roofs",
        "name": "Techos verdes y jardines verticales",
        "category": "Infraestructura Verde",
        "lst_reduction_c": -1.8,
        "ndvi_increase": 0.05,
        "cost_level": "Alto",
        "timeframe": "Mediano (3-5 años)",
        "priority_localidades": ["Chapinero", "Kennedy", "Ciudad Bolívar"],
        "co_benefits": "Aísla térmicamente edificaciones, retiene agua lluvia y aumenta biodiversidad.",
        "description": (
            "Instalación de cubiertas y paredes vegetadas en edificaciones residenciales y comerciales. "
            "Disminuye la absorción de calor en superficies construidas."
        ),
    },
    {
        "id": "parks_green_corridors",
        "name": "Parques y corredores verdes",
        "category": "Infraestructura Verde",
        "lst_reduction_c": -3.0,
        "ndvi_increase": 0.12,
        "cost_level": "Alto",
        "timeframe": "Largo (>5 años)",
        "priority_localidades": ["Ciudad Bolívar", "Kennedy", "Usaquén"],
        "co_benefits": "Fomenta recreación, conectividad ecológica y bienestar mental de la comunidad.",
        "description": (
            "Creación y rehabilitación de parques locales y corredores verdes interconectados. "
            "Genera el mayor efecto de enfriamiento al combinar vegetación densa con suelo permeable."
        ),
    },
    {
        "id": "cool_pavements",
        "name": "Pavimentos y superficies reflectantes",
        "category": "Infraestructura Gris",
        "lst_reduction_c": -1.2,
        "ndvi_increase": 0.0,
        "cost_level": "Medio",
        "timeframe": "Corto (1-2 años)",
        "priority_localidades": ["Kennedy", "Ciudad Bolívar"],
        "co_benefits": "Reduce consumo energético en iluminación pública y mejora confort peatonal.",
        "description": (
            "Reemplazo o recubrimiento de pavimentos oscuros por materiales de alta reflectancia solar. "
            "Disminuye la absorción de radiación en vías y estacionamientos."
        ),
    },
    {
        "id": "cool_roofs",
        "name": "Techos fríos",
        "category": "Infraestructura Gris",
        "lst_reduction_c": -1.5,
        "ndvi_increase": 0.0,
        "cost_level": "Bajo",
        "timeframe": "Corto (1-2 años)",
        "priority_localidades": ["Ciudad Bolívar", "Kennedy", "Chapinero"],
        "co_benefits": "Reduce consumo de energía para climatización y prolonga vida útil de cubiertas.",
        "description": (
            "Aplicación de pinturas o materiales reflectantes en cubiertas de viviendas y edificios. "
            "Es la intervención de menor costo y más rápida implementación."
        ),
    },
    {
        "id": "urban_water_bodies",
        "name": "Cuerpos de agua urbanos",
        "category": "Infraestructura Verde",
        "lst_reduction_c": -2.0,
        "ndvi_increase": 0.02,
        "cost_level": "Medio",
        "timeframe": "Mediano (3-5 años)",
        "priority_localidades": ["Kennedy", "Ciudad Bolívar", "Usaquén"],
        "co_benefits": "Aumenta humedad relativa, provee hábitat acuático y valor estético al espacio público.",
        "description": (
            "Construcción y rehabilitación de fuentes, canales y estanques en espacios públicos. "
            "El enfriamiento evaporativo reduce la temperatura del aire y superficies adyacentes."
        ),
    },
    {
        "id": "density_ventilation_zoning",
        "name": "Regulación de densidad y zonas de ventilación",
        "category": "Planificación Urbana",
        "lst_reduction_c": -0.8,
        "ndvi_increase": 0.0,
        "cost_level": "Bajo",
        "timeframe": "Largo (>5 años)",
        "priority_localidades": ["Chapinero", "Kennedy", "Ciudad Bolívar"],
        "co_benefits": "Mejora calidad del aire, reduce contaminación acústica y ordena el crecimiento urbano.",
        "description": (
            "Actualización normativa para limitar densidad de construcción y abrir corredores de viento. "
            "Facilita la circulación del aire fresco y disipa el calor acumulado."
        ),
    },
    {
        "id": "wetland_restoration",
        "name": "Restauración de humedales periurbanos",
        "category": "Infraestructura Verde",
        "lst_reduction_c": -2.2,
        "ndvi_increase": 0.10,
        "cost_level": "Medio",
        "timeframe": "Largo (>5 años)",
        "priority_localidades": ["Ciudad Bolívar", "Kennedy", "Usaquén"],
        "co_benefits": "Captura carbono, filtra agua, reduce riesgo de inundación y protege biodiversidad nativa.",
        "description": (
            "Recuperación y protección de humedales en la periferia urbana de Bogotá. "
            "Su gran masa de agua y vegetación higrófita produce enfriamiento evaporativo sostenido."
        ),
    },
]


def get_strategies_df() -> pd.DataFrame:
    """Retorna todas las estrategias como DataFrame ordenado por impact_score."""
    df = pd.DataFrame(STRATEGIES)
    df["impact_score"] = (
        df["lst_reduction_c"].abs() * 0.7 + df["ndvi_increase"] * 10 * 0.3
    )
    return df.sort_values("impact_score", ascending=False).reset_index(drop=True)


def get_strategies_for_localidad(localidad: str) -> pd.DataFrame:
    """Filtra estrategias prioritarias para una localidad y las ordena por impact_score."""
    df = get_strategies_df()
    mask = df["priority_localidades"].apply(lambda locs: localidad in locs)
    return df[mask].reset_index(drop=True)


def simulate_mitigation(
    lst_current: float,
    ndvi_current: float,
    strategy_ids: list[str],
) -> dict:
    """Calcula LST y NDVI proyectados al aplicar las estrategias indicadas."""
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
    """Agrupa estrategias por categoría y calcula estadísticas de impacto."""
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
