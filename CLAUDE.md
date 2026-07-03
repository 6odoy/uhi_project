# CLAUDE.md — Proyecto UHI Bogotá

## Descripción del Proyecto

**Título:** Assessing the Combined Impact of Climate Change and Urban Heat — Colombia / Bogotá

**País seleccionado:** Colombia  
**Ciudad seleccionada:** Bogotá D.C.

**Estructura del proyecto (3 pasos académicos):**

### Paso 1 — Proyecciones climáticas nacionales (Colombia)
Analizar datos históricos y proyecciones futuras de variables/índices climáticos relacionados con el calor para Colombia, usando el **World Bank Climate Change Knowledge Portal** (WBCCKP).
- Fuente: https://climateknowledgeportal.worldbank.org/download-data
- Variables objetivo: temperatura media, días con calor extremo (Tx35), precipitación, índices de estrés térmico
- Escenarios: RCP 4.5 y RCP 8.5 (o SSP2-4.5 / SSP5-8.5 en CMIP6)
- Período histórico: 1950–2020; proyecciones: 2020–2080
- Entregable: resumen de cambios proyectados + implicaciones

### Paso 2 — Análisis urbano de Bogotá con GEE
Investigar cómo la urbanización amplifica los impactos del cambio climático en Bogotá usando GEE + Python.
- Análisis espacial de LST, NDVI, cobertura del suelo y expansión urbana (2015–2025)
- 4 localidades contrastantes: Chapinero, Ciudad Bolívar, Usaquén, Kennedy
- Identificar zonas de alto riesgo térmico y patrones de calor urbano
- Correlacionar pérdida de vegetación con incremento de temperatura superficial
- Datos adicionales opcionales: estaciones meteorológicas IDEAM, datos demográficos DANE

### Paso 3 — Estrategias de mitigación
Proponer estrategias de mitigación de calor urbano basadas en los hallazgos de los Pasos 1 y 2.
- Justificar recomendaciones con evidencia del análisis
- Estrategias candidatas: infraestructura verde, techos frescos, arbolado urbano, pavimentos reflectantes, corredores de viento

---

## Estructura de Carpetas

```
uhi_project/
├── CLAUDE.md
├── app.py                          # Dashboard Streamlit (3 secciones = 3 pasos)
├── requirements.txt
├── .streamlit/
│   └── secrets.toml                # Credenciales GEE (NO subir a git)
├── .gitignore
├── assets/
│   └── unitus_logo.svg
├── data/
│   ├── raw/
│   │   ├── wb_climate/             # CSVs descargados del World Bank portal
│   │   └── shapefiles/             # Límites administrativos Bogotá
│   └── processed/
│       ├── uhi_bogota.parquet      # LST + NDVI + urbano por localidad y año
│       └── wb_colombia.parquet     # Datos climáticos World Bank procesados
├── src/
│   ├── __init__.py
│   ├── gee_utils.py                # Conexión y consultas a GEE
│   ├── data_pipeline.py            # Pipeline GEE → Parquet (Paso 2)
│   ├── wb_pipeline.py              # Procesamiento datos World Bank (Paso 1)
│   └── analysis.py                 # Estadísticas, correlaciones, modelo
├── scripts/
│   └── generate_sample_data.py     # Datos sintéticos para pruebas
└── notebooks/
    └── exploracion.ipynb
```

---

## Datasets

### Paso 1 — World Bank Climate Change Knowledge Portal
| Variable | Descripción | Formato |
|---|---|---|
| Temperatura media (tas) | Histórico + RCP4.5/8.5 | CSV mensual por país |
| Días > 35°C (Tx35) | Proyecciones de calor extremo | CSV anual |
| Precipitación (pr) | Histórico + proyecciones | CSV mensual |
| Índice de estrés térmico | WBGT o HI cuando disponible | CSV |

Descarga manual desde: https://climateknowledgeportal.worldbank.org/download-data  
→ Country: Colombia → Variable → Scenario → Download CSV  
Guardar en: `data/raw/wb_climate/`

### Paso 2 — Google Earth Engine
| Variable | Dataset GEE | Resolución |
|---|---|---|
| LST | `MODIS/061/MOD11A2` | 1 km, 8 días |
| NDVI | `COPERNICUS/S2_SR_HARMONIZED` | 10 m |
| Expansión urbana | `GOOGLE/DYNAMICWORLD/V1` | 10 m |
| Cobertura del suelo | `ESA/WorldCover/v200` | 10 m |
| Límites administrativos | Asset propio (shapefile IDECA/DANE) | — |

---

## Estructura del Dashboard (app.py)

El dashboard tiene **3 tabs** correspondientes a los 3 pasos del proyecto:

### Tab 1 — "Colombia: Proyecciones Climáticas"
- KPIs: cambio proyectado de temperatura (°C), días de calor extremo extra, cambio en precipitación
- Gráfico: temperatura histórica + proyecciones RCP4.5 vs RCP8.5 (con banda de incertidumbre)
- Gráfico: frecuencia de días extremos por década
- Texto: resumen de implicaciones

### Tab 2 — "Bogotá: Análisis Urbano"  ← lo que ya existe
- Mapa interactivo GEE
- Series de tiempo LST y NDVI por localidad
- Correlaciones y scatter plots
- Ranking de localidades por criticidad
- Simulador de escenarios

### Tab 3 — "Estrategias de Mitigación"
- Matriz de estrategias (tipo, impacto esperado, aplicabilidad por localidad)
- Gráfico de impacto simulado (what-if con el modelo de regresión)
- Recomendaciones prioritarias basadas en el ranking de criticidad

---

## Librerías Python
```
earthengine-api>=0.1.370
geemap>=0.30.0
streamlit>=1.35.0
pandas>=2.0.0
geopandas>=0.14.0
plotly>=5.20.0
scipy>=1.12.0
pymannkendall>=1.4.3
dvc>=3.0.0
requests>=2.31.0      # Para API World Bank si disponible
```

---

## Reglas de Código

1. **Nunca subir a git:** `.streamlit/secrets.toml`, claves JSON, `.env`
2. **Datos precalculados** en `data/processed/` — no llamar GEE en tiempo real desde el dashboard
3. **Cache obligatorio** en todas las funciones de carga de datos (`@st.cache_data`)
4. **Tipos anotados** en todas las funciones de `src/`
5. **Sin comentarios obvios** — solo el "por qué" cuando no sea evidente
6. **Idioma del código:** inglés para identificadores y para todos los textos visibles del dashboard (labels, títulos, tooltips, mensajes) — decisión tomada el 2026-07-03. Los nombres propios de las localidades de Bogotá (Chapinero, Ciudad Bolívar, Usaquén, Kennedy) se mantienen tal cual, sin traducir
7. **Estructura de tabs:** cada tab es autónomo y funciona aunque los otros fallen

---

## Notas de Autenticación GEE

```python
# Local
import ee
ee.Authenticate()
ee.Initialize(project="tu-proyecto-gcp")

# Producción (service account en secrets.toml)
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gee_service_account"],
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials=credentials, project="tu-proyecto-gcp")
```

---

## Estado Actual (2026-07-02)

- [x] Entorno virtual `.venv` con todas las dependencias
- [x] `src/gee_utils.py` — conexión GEE, extracción LST/NDVI/urbano
- [x] `src/data_pipeline.py` — pipeline GEE → Parquet
- [x] `src/analysis.py` — correlaciones, tendencias Mann-Kendall, modelo regresión
- [x] `app.py` — dashboard con diseño personalizado (modo claro/oscuro)
- [x] Datos sintéticos de prueba en `data/processed/uhi_bogota.parquet`
- [ ] `src/wb_pipeline.py` — procesamiento datos World Bank (Paso 1)
- [ ] Tab 1 en dashboard — proyecciones climáticas Colombia
- [ ] Tab 3 en dashboard — estrategias de mitigación
- [ ] Datos reales GEE (requiere proyecto GCP + asset de localidades)
- [ ] Datos World Bank descargados manualmente en `data/raw/wb_climate/`
