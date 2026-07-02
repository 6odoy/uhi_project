# CLAUDE.md — Proyecto UHI Bogotá

## Descripción del Proyecto

**Título:** Monitoreo geoespacial de islas de calor urbano (UHI) y su relación con la pérdida de cobertura vegetal en Bogotá (2015-2025)

**Objetivo:** Construir un dashboard interactivo en Streamlit que permita explorar la evolución de la temperatura superficial (LST), el índice de vegetación (NDVI) y la expansión urbana en las localidades de Bogotá, usando datos satelitales extraídos vía Google Earth Engine (GEE) API.

---

## Estructura de Carpetas

```
uhi_project/
├── CLAUDE.md
├── plan_proyecto_UHI_Bogota.md
├── app.py                         # Entrypoint principal del dashboard Streamlit
├── requirements.txt               # Dependencias fijadas con versiones
├── .streamlit/
│   └── secrets.toml               # Credenciales de service account (NO subir a git)
├── .gitignore
├── data/
│   ├── raw/                       # Shapefiles de localidades de Bogotá (IDECA/DANE)
│   └── processed/                 # CSVs/Parquet precalculados (output del pipeline)
├── src/
│   ├── __init__.py
│   ├── gee_utils.py               # Funciones de conexión y consulta a GEE
│   ├── data_pipeline.py           # Extracción y agregación (Fase 2)
│   └── analysis.py                # Funciones estadísticas (Fase 3)
└── notebooks/
    └── exploracion.ipynb          # EDA inicial
```

---

## Datasets de Google Earth Engine

| Variable | Dataset GEE | Resolución | Notas |
|---|---|---|---|
| LST (temperatura superficial) | `MODIS/061/MOD11A2` | 1 km, 8 días | Serie larga y consistente |
| LST alta resolución | `LANDSAT/LC08/C02/T1_L2` + `LANDSAT/LC09/C02/T1_L2` | 30 m | Menos frecuencia, más detalle |
| NDVI | `COPERNICUS/S2_SR_HARMONIZED` | 10 m | Sentinel-2 |
| Cobertura del suelo | `ESA/WorldCover/v200` | 10 m | Snapshot 2021 |
| Expansión urbana anual | `GOOGLE/DYNAMICWORLD/V1` | 10 m | Para medir expansión año a año |
| Límites administrativos | Shapefile IDECA/DANE | — | Asset GEE propio |

---

## Librerías Python Principales

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
```

---

## Fases de Desarrollo

### Fase 1 — Configuración Inicial (Semana 1-2)
- Área de estudio: Bogotá completa con foco en 4 localidades contrastantes: Chapinero, Ciudad Bolívar, Usaquén, Kennedy
- Rango temporal: 2015–2025, agregación anual
- Configurar proyecto GCP, habilitar Earth Engine API
- Subir shapefile de localidades como Asset en GEE
- Configurar entorno conda/venv, repositorio Git

**Entregable:** entorno funcional + acceso GEE confirmado + geometrías de localidades cargadas

### Fase 2 — Pipeline de Extracción de Datos (Semana 2-4)
- Filtrar colecciones de imágenes por fecha y región de interés
- Calcular LST promedio por localidad y período (`reduceRegions` con `ee.Reducer.mean()`)
- Calcular NDVI promedio por localidad y período
- Calcular % cobertura urbana por localidad y año (Dynamic World)
- Exportar a CSV/Parquet (no depender de GEE en tiempo real desde el dashboard)
- Validar nulos, outliers, cobertura de nubes en Landsat/Sentinel
- Versionar datasets intermedios con DVC

**Entregable:** dataset tabular limpio (localidad, año/periodo, LST, NDVI, % urbano)

### Fase 3 — Análisis Exploratorio y Estadístico (Semana 4-5)
- EDA: distribución de LST y NDVI por localidad
- Series de tiempo por localidad (tendencia LST y NDVI)
- Correlación NDVI vs. LST vs. % urbanización (Pearson y/o Spearman)
- Test Mann-Kendall sobre series temporales
- Modelo de regresión para predecir LST desde cobertura vegetal y urbana
- Identificar localidades críticas (mayor temperatura / mayor pérdida vegetal)

**Entregable:** notebook de análisis con hallazgos y visualizaciones preliminares

### Fase 4 — Dashboard Streamlit (Semana 5-7)

Componentes:
- `st.sidebar` para selección de localidad, año/rango y capa (LST, NDVI, urbano)
- Mapa interactivo con `geemap` (foliumap) mostrando capas desde GEE
- Series de tiempo con Plotly (tendencia LST y NDVI por localidad)
- Panel de correlación (scatter plot + coeficiente)
- Tabla comparativa entre localidades (ranking temperatura/vegetación)
- Cache con `@st.cache_data` / `@st.cache_resource`
- Manejo de errores si GEE API falla o se excede la cuota

Autenticación producción:
- Service account de GEE (no autenticación interactiva)
- Clave JSON configurada como secret en Streamlit
- Credenciales en `.streamlit/secrets.toml` (nunca en git)

**Entregable:** dashboard funcional en local

### Fase 5 — Despliegue y Documentación (Semana 7-8)
- Plataforma: Streamlit Community Cloud (primera opción, gratis) o Docker
- `requirements.txt` con versiones fijadas
- Credenciales de service account como secret en la plataforma
- README con: objetivo, metodología, fuentes de datos, instrucciones locales
- (Opcional) GIF de demostración

**Entregable:** dashboard público desplegado + repositorio documentado

---

## Reglas de Código

1. **Nunca subir a git:** `.streamlit/secrets.toml`, claves JSON de service account, archivos `.env`
2. **Siempre usar datos precalculados** en el dashboard (CSV/Parquet en `data/processed/`) — no llamar GEE en tiempo real desde el dashboard salvo para el mapa interactivo
3. **Cache obligatorio** en todas las funciones que llamen a GEE o carguen datos pesados
4. **Tipos anotados** en todas las funciones de `src/`
5. **Sin comentarios obvios** — solo comentar el "por qué" si no es evidente
6. **Manejo de errores** solo en los límites del sistema (respuesta GEE API, carga de archivos)
7. **Idioma del código:** inglés para identificadores y docstrings; español para comunicación con el usuario

---

## Extensiones Opcionales (MLOps)

- Módulo de predicción de LST futura (regresión o red pequeña)
- Trackeo de experimentos con MLflow
- Componente "what-if" para escenarios de cambio de cobertura vegetal usando el modelo

---

## Notas de Autenticación GEE

```python
# Local (desarrollo)
import ee
ee.Authenticate()
ee.Initialize(project="tu-proyecto-gcp")

# Producción (service account)
import ee
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gee_service_account"],
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials=credentials, project="tu-proyecto-gcp")
```
