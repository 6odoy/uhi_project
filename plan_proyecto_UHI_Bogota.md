# Plan de Acción: Monitoreo Geoespacial de Islas de Calor Urbano en Bogotá

## Descripción General

**Título del proyecto:** Monitoreo geoespacial de islas de calor urbano (UHI) y su relación con la pérdida de cobertura vegetal en Bogotá (2015-2025)

**Objetivo general:** Construir un dashboard interactivo en Streamlit que permita explorar la evolución de la temperatura superficial (LST), el índice de vegetación (NDVI) y la expansión urbana en las localidades de Bogotá, usando datos satelitales extraídos vía Google Earth Engine (GEE) API.

**Justificación:** Conecta Data Science, Smart Cities y salud/planeación urbana. Es replicable con datos abiertos, tiene aplicación real en política pública (adaptación climática, salud pública) y permite mostrar competencias en pipelines geoespaciales, análisis estadístico y despliegue de productos de datos.

---

## Datasets en Google Earth Engine

| Variable | Dataset GEE | Resolución | Notas |
|---|---|---|---|
| Temperatura superficial (LST) | `MODIS/061/MOD11A2` | 1 km, 8 días | Serie larga y consistente |
| Temperatura superficial (alta resolución) | `LANDSAT/LC08/C02/T1_L2` + `LANDSAT/LC09/C02/T1_L2` | 30 m | Menor frecuencia temporal, más detalle espacial |
| Vegetación (NDVI) | `COPERNICUS/S2_SR_HARMONIZED` | 10 m | Sentinel-2, buena resolución |
| Cobertura del suelo | `ESA/WorldCover/v200` | 10 m | Snapshot estático (2021) |
| Clasificación urbana anual | `GOOGLE/DYNAMICWORLD/V1` | 10 m | Ideal para medir expansión urbana año a año |
| Límites administrativos | Shapefile IDECA / DANE (localidades de Bogotá) | — | Subir como GEE Asset propio |

---

## Fase 1 — Alcance y configuración inicial (Semana 1-2)

- [ ] Definir el área de estudio: Bogotá completa vs. 3-4 localidades contrastantes (ej. Chapinero, Ciudad Bolívar, Usaquén, Kennedy) para tener contraste socioeconómico
- [ ] Definir el rango temporal (sugerido: 2015-2025, con agregación anual o semestral)
- [ ] Crear proyecto en Google Cloud Platform
- [ ] Habilitar la Earth Engine API en el proyecto
- [ ] Probar autenticación local: `ee.Authenticate()` y `ee.Initialize(project="tu-proyecto")`
- [ ] Descargar/obtener shapefile de localidades de Bogotá (IDECA o DANE)
- [ ] Subir el shapefile como Asset en GEE (`ee.FeatureCollection`)
- [ ] Configurar entorno de trabajo (conda/venv), repositorio Git, estructura de carpetas

**Entregable de la fase:** entorno funcional + acceso confirmado a GEE + geometrías de localidades cargadas.

---

## Fase 2 — Pipeline de extracción de datos (Semana 2-4)

- [ ] Escribir función para filtrar colecciones de imágenes por fecha y región de interés
- [ ] Calcular LST promedio por localidad y periodo (`reduceRegions` con `ee.Reducer.mean()`)
- [ ] Calcular NDVI promedio por localidad y periodo
- [ ] Calcular % de cobertura urbana por localidad y año (a partir de Dynamic World)
- [ ] Exportar resultados agregados a CSV/Parquet (no depender de llamadas a GEE en tiempo real desde el dashboard)
- [ ] Validar consistencia de los datos exportados (revisar nulos, outliers, cobertura de nubes en Landsat/Sentinel)
- [ ] Versionar los datasets intermedios con DVC
- [ ] Documentar el pipeline (script o notebook reproducible)

**Entregable de la fase:** dataset tabular limpio (localidad, año/periodo, LST, NDVI, % urbano) listo para análisis.

---

## Fase 3 — Análisis exploratorio y estadístico (Semana 4-5)

- [ ] Análisis exploratorio: distribución de LST y NDVI por localidad
- [ ] Series de tiempo por localidad (tendencia de LST y NDVI a lo largo de los años)
- [ ] Correlación NDVI vs. LST vs. % urbanización (Pearson y/o Spearman)
- [ ] (Opcional) Test de tendencia Mann-Kendall sobre las series temporales
- [ ] (Opcional) Modelo de regresión simple (o Bayesiano) para predecir LST a partir de cobertura vegetal y urbana
- [ ] Identificar localidades "críticas" (mayor incremento de temperatura / mayor pérdida de vegetación)

**Entregable de la fase:** notebook de análisis con hallazgos clave y visualizaciones preliminares.

---

## Fase 4 — Construcción del Dashboard en Streamlit (Semana 5-7)

### Estructura sugerida del proyecto
```
proyecto_uhi_bogota/
├── app.py
├── requirements.txt
├── .streamlit/
│   └── secrets.toml          # credenciales de service account (no subir a git)
├── data/
│   └── processed/            # CSVs/Parquet precalculados
├── src/
│   ├── gee_utils.py          # funciones de conexión y consulta a GEE
│   ├── data_pipeline.py      # extracción y agregación (Fase 2)
│   └── analysis.py           # funciones estadísticas (Fase 3)
└── notebooks/
    └── exploracion.ipynb
```

### Componentes del dashboard
- [ ] `st.sidebar` para selección de localidad, año/rango y capa a visualizar (LST, NDVI, urbano)
- [ ] Mapa interactivo con `geemap` (integración nativa con Streamlit vía `geemap.foliumap`) mostrando capas directamente desde GEE
- [ ] Gráficas de series de tiempo con Plotly (tendencia de LST y NDVI por localidad seleccionada)
- [ ] Panel de correlación (scatter plot + coeficiente de correlación)
- [ ] Tabla comparativa entre localidades (ranking de temperatura/vegetación)
- [ ] Cachear llamadas a GEE y carga de datos con `@st.cache_data` / `@st.cache_resource`
- [ ] Manejo de errores si la API de GEE falla o se excede la cuota

### Autenticación para producción
- [ ] Crear una **service account** de GEE (no usar autenticación interactiva en el dashboard desplegado)
- [ ] Generar la clave JSON de la service account
- [ ] Configurar las credenciales como `secret` en Streamlit (no en el repositorio)

**Entregable de la fase:** dashboard funcional en local, navegable y sin errores.

---

## Fase 5 — Despliegue y documentación (Semana 7-8)

- [ ] Elegir plataforma de despliegue: Streamlit Community Cloud (gratis) o contenedor Docker propio
- [ ] Configurar `requirements.txt` con versiones fijadas (evitar romper compatibilidad con `earthengine-api`)
- [ ] Subir credenciales de service account como secret en la plataforma elegida
- [ ] Probar el dashboard desplegado end-to-end
- [ ] Escribir README con: objetivo, metodología, fuentes de datos, cómo correr el proyecto localmente
- [ ] (Opcional) Grabar un video corto o GIF de demostración para el README

**Entregable de la fase:** dashboard público desplegado + repositorio documentado.

---

## Extensión Opcional (valor académico/MLOps)

- [ ] Módulo de predicción de LST futura con un modelo de regresión o red pequeña
- [ ] Trackear experimentos con MLflow (consistente con tu flujo de trabajo en la tesis)
- [ ] Agregar un componente de "qué pasaría si" (escenario de más/menos cobertura vegetal) usando el modelo entrenado

---

## Cronograma Resumen

| Semana | Fase | Foco principal |
|---|---|---|
| 1-2 | Fase 1 | Configuración GEE, datos administrativos |
| 2-4 | Fase 2 | Pipeline de extracción de datos |
| 4-5 | Fase 3 | Análisis exploratorio y estadístico |
| 5-7 | Fase 4 | Construcción del dashboard |
| 7-8 | Fase 5 | Despliegue y documentación |

---

## Librerías Python principales

- `earthengine-api` — conexión con GEE
- `geemap` — visualización de capas GEE en mapas interactivos, integrable con Streamlit
- `streamlit` — dashboard
- `pandas`, `geopandas` — manejo de datos tabulares y geoespaciales
- `plotly` — gráficas interactivas
- `scipy` / `pymannkendall` — pruebas estadísticas
- `dvc` — versionado de datos (opcional, consistente con tu flujo actual)
