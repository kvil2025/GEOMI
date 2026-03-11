<p align="center">
  <img src="https://img.shields.io/badge/GeologgIA_Map-v2.0-0ea5e9?style=for-the-badge&logo=globe&logoColor=white" alt="GeologgIA Map v2.0"/>
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+"/>
  <img src="https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react&logoColor=black" alt="React 18+"/>
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/MapLibre_GL-JS-FF4500?style=for-the-badge" alt="MapLibre GL JS"/>
</p>

# 🌍 GeologgIA Map

**Plataforma de Inteligencia Geológica** — Aplicación geoespacial de alta performance para análisis de propiedad minera, geología y topografía en Chile.

> Visualiza concesiones mineras, mapas geológicos con litologías, análisis de pendientes y datos topográficos en una interfaz moderna con tema dark premium.

---

## 📋 Tabla de Contenidos

- [Características](#-características)
- [Tecnologías](#-tecnologías)
- [Instalación](#-instalación)
- [Manual de Uso](#-manual-de-uso)
- [Arquitectura](#-arquitectura)
- [API Endpoints](#-api-endpoints)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Licencia](#-licencia)

---

## ✨ Características

### 🗺 Capas de Mapa
- **Concesiones Mineras**: Consulta WFS a SERNAGEOMIN con polígonos de concesiones de exploración y explotación
- **Mapa Geológico de Chile**: 18,935 unidades litológicas con colores por tipo, leyenda interactiva y popup con metadata
- **Mapa de Pendientes (Slope)**: Análisis DEM con algoritmo de Horn + filtro Gaussiano, rangos configurables
- **Datos del Usuario**: Carga de archivos GeoJSON, KML y Shapefile

### 🔬 Análisis Geológico
- Resolución configurable: ⚡ Rápida (geometrías simplificadas) o 🔬 Alta Resolución
- Índice espacial R-tree para consultas en milisegundos
- Leyenda dinámica con colores por litología
- Popup interactivo con información detallada de cada unidad

### 📊 Análisis de Pendientes
- Selección de zona en el mapa con herramienta de dibujo
- Múltiples resoluciones: Baja (10×10), Media (30×30), Alta (60×60), Ultra (100×100)
- Rangos de color configurables (0-3%, 3-7%, 7-12%, etc.)
- Histograma de distribución de pendientes
- Exportación de resultados

### 📂 Importar / Exportar Shapefile
- **Importar**: Carga de archivos `.shp` + `.shx` + `.dbf` (+ opcionales `.prj`, `.cpg`)
- Auto-reproyección a WGS84 desde cualquier sistema de coordenadas
- **Exportar**: Descarga de todas las capas visibles como Shapefile (ZIP)

### 🎨 Interfaz Premium
- Tema dark con glassmorphism y gradientes
- Sidebar colapsable con secciones organizadas
- Tooltips, toasts y feedback visual
- Responsive y optimizado para desktop

---

## 🛠 Tecnologías

### Backend
| Tecnología | Uso |
|-----------|-----|
| **FastAPI** | Framework web async de alta performance |
| **Python 3.9+** | Lenguaje principal |
| **pyshp** | Lectura/escritura de Shapefiles |
| **pyproj** | Transformación de coordenadas |
| **NumPy / SciPy** | Procesamiento de matrices DEM y filtros |
| **Shapely** | Operaciones geométricas |
| **R-tree** | Índice espacial para consultas rápidas |

### Frontend
| Tecnología | Uso |
|-----------|-----|
| **React 18** | UI reactiva con hooks |
| **Vite** | Build tool ultra-rápido |
| **MapLibre GL JS** | Renderizado de mapas vectoriales |
| **CSS Custom Properties** | Design system con variables |

---

## 🚀 Instalación

### Prerequisitos
- Python 3.9+
- Node.js 18+
- npm o yarn

### 1. Clonar el repositorio
```bash
git clone https://github.com/kvil2025/GEOMI.git
cd GEOMI
```

### 2. Backend (FastAPI)
```bash
# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install fastapi uvicorn[standard] requests numpy scipy shapely pyshp pyproj python-dotenv

# Iniciar servidor
cd fastapi_app
uvicorn main:app --reload --port 8000
```

### 3. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

### 4. Acceder
Abrir el navegador en **http://localhost:5173**

---

## 📖 Manual de Uso

### 1. Interfaz Principal

Al abrir la aplicación verás:
- **Sidebar izquierdo**: Panel de control con todas las herramientas
- **Mapa central**: Mapa interactivo centrado en la región de Atacama, Chile
- **Botón ‹**: Colapsar/expandir el sidebar

### 2. Gestión de Capas

En la sección **CAPAS** del sidebar:

| Capa | Toggle | Descripción |
|------|--------|-------------|
| 🔵 Concesiones Mineras | ON/OFF | Polígonos de concesiones de SERNAGEOMIN |
| 🟢 Mapa de Pendientes | ON/OFF | Overlay de análisis de pendientes |
| 🟣 Datos del Usuario | ON/OFF | Archivos cargados por el usuario |
| 🟡 Geología de Chile | ON/OFF | Mapa geológico con litologías |

### 3. Mapa Base

Selecciona entre dos mapas base:
- **🗺 Estándar**: CARTO Dark Matter (tema oscuro)
- **⛰ Topográfico**: OpenTopoMap (relieve y elevación)

### 4. Cargar Mapa Geológico

1. En la sección **MAPA GEOLÓGICO**, selecciona la resolución:
   - **⚡ Rápida**: Geometrías simplificadas, carga instantánea
   - **🔬 Alta Res**: Detalle completo de polígonos (puede tardar más)
2. Haz clic en **"🗺 Cargar Mapa Geológico"**
3. Los polígonos se colorean automáticamente por litología
4. Haz clic en cualquier polígono para ver su información detallada
5. La leyenda aparece en la esquina inferior izquierda del mapa

### 5. Análisis de Pendientes (Slope Map)

1. En la sección **MAPA DE PENDIENTES**, haz clic en **"📐 Seleccionar Zona en el Mapa"**
2. Dibuja un rectángulo en el mapa arrastrando el mouse
3. Selecciona la resolución deseada (Baja, Media, Alta, Ultra)
4. Configura los rangos de pendiente (%) con los colores deseados
5. Haz clic en **"✦ Generar Mapa de Pendientes"**
6. El mapa mostrará las pendientes coloreadas por rango
7. Un histograma muestra la distribución estadística

### 6. Cargar Concesiones

1. Haz clic en **"📍 Cargar Concesiones"** en la sección ACCIONES
2. Se consultarán las concesiones mineras de SERNAGEOMIN para la zona visible
3. Los polígonos aparecerán en el mapa con popups de información

### 7. Importar Shapefile

1. En la sección **IMPORTAR / EXPORTAR**, haz clic en **"📂 Cargar Shapefile (.shp)"**
2. Selecciona los archivos del shapefile:
   - **Obligatorios**: `.shp`, `.shx`, `.dbf`
   - **Opcionales**: `.prj` (proyección), `.cpg` (codificación)
3. La aplicación reproyectará automáticamente a WGS84 si es necesario
4. Los datos se cargarán como capa "Datos del Usuario"

### 8. Exportar Shapefile

1. Asegúrate de tener capas visibles en el mapa
2. Haz clic en **"📥 Exportar a Shapefile"**
3. Se descargará un archivo ZIP con:
   - `.shp` (geometrías)
   - `.shx` (índice espacial)
   - `.dbf` (atributos)
   - `.prj` (proyección WGS84)

### 9. Importar GeoJSON / KML

1. En la sección **IMPORTAR GEOJSON**, arrastra un archivo `.geojson` o `.kml` al área de drop
2. O haz clic en el área para seleccionar un archivo
3. Los datos se cargarán como capa "Datos del Usuario"

### 10. Datos Topográficos (LiDAR)

1. En la sección **DATOS TOPOGRÁFICOS**, haz clic en **"🛰 Cargar GeoTIFF (.tif)"**
2. Selecciona un archivo GeoTIFF
3. Los datos se procesarán y mostrarán en el mapa

---

## 🏗 Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (React)                  │
│  ┌─────────┐  ┌──────────┐  ┌────────────────────┐ │
│  │ Sidebar  │  │ MapView  │  │ SlopeHistogram     │ │
│  │ - Capas  │  │ MapLibre │  │ Toast, FileDropZone│ │
│  │ - Config │  │ GL JS    │  │                    │ │
│  └────┬─────┘  └────┬─────┘  └────────────────────┘ │
│       │              │                               │
│       └──────┬───────┘                               │
│              │ API calls (fetch)                     │
└──────────────┼───────────────────────────────────────┘
               │
┌──────────────┼───────────────────────────────────────┐
│              │     Backend (FastAPI :8000)            │
│  ┌───────────▼──────────┐                            │
│  │      main.py         │  CORS + Router Registry    │
│  └──────────────────────┘                            │
│  ┌──────────────────────────────────────────────┐    │
│  │ Services:                                    │    │
│  │  • wfs_client.py      → SERNAGEOMIN WFS      │    │
│  │  • geology_service.py → Geología + R-tree    │    │
│  │  • dem_service.py     → DEM / Slope Analysis │    │
│  │  • shapefile_service.py → Import/Export .shp │    │
│  │  • lidar_service.py   → GeoTIFF processing  │    │
│  │  • geo_utils.py       → Spatial utilities    │    │
│  └──────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────┐    │
│  │ Data:                                        │    │
│  │  • geodata/GEOL-CHILE.*  → Shapefile Chile   │    │
│  │  • geology_cache_v2.json → Cached GeoJSON    │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

---

## 🔌 API Endpoints

### Geología
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/geology/features` | Features geológicas por bbox |
| `GET` | `/geology/legend` | Leyenda de litologías con colores |

### Concesiones (WFS)
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/wfs/polygons` | Concesiones mineras por bbox |

### DEM / Pendientes
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/dem/slope` | Análisis de pendientes por bbox |

### Shapefile
| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/shapefile/upload` | Subir shapefile → GeoJSON |
| `POST` | `/shapefile/export` | GeoJSON → Descargar shapefile (ZIP) |

### Sistema
| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Estado del servidor |

---

## 📁 Estructura del Proyecto

```
GeologgIA-Map/
├── fastapi_app/
│   ├── main.py                    # App principal FastAPI
│   ├── services/
│   │   ├── wfs_client.py          # Cliente WFS SERNAGEOMIN
│   │   ├── geology_service.py     # Servicio de geología + R-tree
│   │   ├── dem_service.py         # Análisis DEM y pendientes
│   │   ├── shapefile_service.py   # Import/Export de Shapefiles
│   │   ├── lidar_service.py       # Procesamiento LiDAR/GeoTIFF
│   │   ├── geo_utils.py           # Utilidades geoespaciales
│   │   └── elevation_profile.py   # Perfiles de elevación
│   └── data/
│       └── geology_cache_v2.json  # Cache optimizado de geología
├── frontend/
│   ├── index.html                 # HTML principal
│   ├── vite.config.js             # Config de Vite
│   ├── package.json               # Dependencias npm
│   └── src/
│       ├── main.jsx               # Entry point React
│       ├── App.jsx                # Componente principal
│       ├── App.css                # Estilos del App
│       ├── index.css              # Design system global
│       ├── services/
│       │   └── api.js             # Funciones de API
│       └── components/
│           ├── MapView.jsx/css    # Mapa MapLibre GL
│           ├── Sidebar.jsx/css    # Panel lateral
│           ├── FileDropZone.jsx   # Drag & drop de archivos
│           ├── SlopeMapPanel.jsx  # Panel de pendientes
│           ├── SlopeHistogram.jsx # Histograma de pendientes
│           └── Toast.jsx/css      # Notificaciones
├── geodata/
│   ├── GEOL-CHILE.shp            # Shapefile geológico
│   ├── GEOL-CHILE.dbf            # Atributos
│   ├── GEOL-CHILE.shx            # Índice
│   └── GEOL-CHILE.cpg            # Codificación
├── deps/                          # Dependencias locales
└── README.md                      # Este archivo
```

---

## 🔧 Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto (opcional):

```env
# Puerto del backend
PORT=8000

# API keys (si necesarias)
# MAPBOX_TOKEN=pk.xxx
```

---

## 📝 Notas Técnicas

- **Cache de Geología**: Al cargar por primera vez, se genera `geology_cache_v2.json` (~50MB) para acceso rápido posterior
- **R-tree Index**: Se construye en memoria al iniciar para consultas espaciales en <1ms
- **Simplificación**: Las geometrías simplificadas reducen el tamaño ~80% manteniendo la forma general
- **WGS84**: Todas las operaciones internas usan EPSG:4326 como estándar

---

## 📄 Licencia

Este proyecto es de uso interno para análisis geológico y minero en Chile.

**Desarrollado por** [GeologgIA](https://github.com/kvil2025) — Inteligencia Geológica 🌍

---

<p align="center">
  <b>GeologgIA Map v2.0</b> — Inteligencia Geológica<br/>
  <sub>Hecho con ❤️ para la geología de Chile</sub>
</p>
