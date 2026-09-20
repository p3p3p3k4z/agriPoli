# 🌱 AniIta — Enjambre de Agentes para Recolección Ecológica y Agrícola de México

> Sistema multi-agente orquestado con **LangGraph** que automatiza la búsqueda, recolección, extracción y síntesis de datos ecológicos, geográficos y agrícolas de México para el proyecto **Añi Ita**.

---

## 🏗️ Arquitectura del Enjambre

El sistema ha evolucionado de un simple flujo secuencial a un **Enjambre Jerárquico** controlado por un Agente Supervisor:

```
🙋‍♂️ Usuario <---> [🛡️ Supervisor] <───> [💾 Gestor Descargas Masivas]
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
[🕷️ Grupo 1: Investigador]     [💬 Grupo 2: Agro-Experto]
(Scraping Web, PDFs, RAG)      (Catálogos INEGI, BD Locales)
```

### Nodos del Enjambre

| Nodo/Agente | Función | Herramientas Clave |
|-------------|---------|--------------------|
| **Supervisor** | Interactúa contigo, enruta peticiones y pide permiso para descargar. | `delegar_investigador`, `consultar_agroexperto`, `descargas_masivas` |
| **Investigador** | Busca URLs y extrae contexto (Scraping/RAG) para armar JSONs. | `buscar_tavily_mexico`, `lector_web_playwright` |
| **Agro Experto** | Cruza datos de bases locales y la API oficial del BISE. | `consultar_base_agricola_local`, `consultar_indicador_inegi` |

### Fuentes Oficiales
- 🇲🇽 **CONABIO** / EncicloVida — Biodiversidad y Polinizadores
- 🌾 **SADER** / SIAP — Agricultura y Cierres Agrícolas
- 🗺️ **INEGI** — Geografía, Edafología y Socioeconomía
- 🎓 **UNAM** / IBUNAM — Colecciones Botánicas e Insectos

---

## ⚡ Quickstart (Entorno `uv`)

El proyecto utiliza el moderno gestor **uv** y su `pyproject.toml` para ser ultra rápido.

### 1. Inicialización
```bash
# Entrar a la carpeta
cd enjambre_agentes

# Las dependencias se instalarán automáticamente en el entorno virtual
uv run playwright install chromium
```

### 2. Configurar API keys
```bash
cp .env.example .env
# Editar .env con tus API keys (Gemini, Tavily, INEGI, etc.)
```

### 3. Ejecutar el Chat Interactivo (Human-in-the-Loop)
El punto de entrada principal ahora es el Agente Supervisor interactivo:
```bash
uv run python scripts/main_supervisor.py
```
*Escríbele en el chat: "Dime qué polinizadores hay en Oaxaca" o "Cuáles son los rendimientos de la milpa en Sonora".*

---

## 💾 Extracción de Datos Libres y Descargas Masivas

Además de la búsqueda dinámica, el Enjambre cuenta con un potente motor unificado de descargas asíncronas (`DescargadorMasivoAsync`). Este motor te permite bajar las bases de datos gubernamentales completas a tu computadora.

Puedes invocar estas descargas de dos maneras:
1. **Pidiéndoselo al Supervisor** en el chat interactivo (él te preguntará si deseas guardarlas).
2. **Directamente desde la terminal** ejecutando los scripts dedicados:

```bash
# 1. Catálogo Completo de Polinizadores y Flora (EncicloVida / iNaturalist)
uv run python scripts/descargar_catalogo.py --tipo ambos --use-gbif

# 2. Cierres Agrícolas (SADER / SIAP)
uv run python scripts/descarga_agricola.py

# 3. Colecciones Universitarias (IBUNAM)
uv run python scripts/descarga_unam.py
```

> **Gestión de Referencias:** Todas las extracciones masivas registran automáticamente su URL de origen, título y fecha en `data/referencias.json`, garantizando así el rigor científico y trazabilidad de los datos.

## 📦 Estructura del Proyecto

```
AniIta/
├── config/
│   ├── keys.py         # Gestión de API keys
│   └── models.py       # Fábrica LLM multi-proveedor
├── data/
│   └── referencias.json# Bibliografía de descargas
├── tools/
│   ├── search.py       # Herramientas web para México
│   ├── inegi_client.py # API Oficial de BISE INEGI
│   └── descargador_masivo.py # Motor asíncrono para bases gubernamentales
├── agents/
│   ├── supervisor.py   # El orquestador Human-in-the-Loop
│   ├── investigador.py # Especialista en scraping
│   └── agro_experto.py # Especialista agrícola/estadístico
├── scripts/
│   ├── main_supervisor.py # Terminal interactiva
│   └── descargar_catalogo.py # Scripts de descarga masiva (SIAP, UNAM, etc)
├── pyproject.toml      # Configuración de uv
└── .env.example
```

---

## 📋 Schema de Salida (DatosRegion)

El JSON generado sigue el schema `DatosRegion` con los siguientes campos principales:

```json
{
  "region": "La Mixteca, Oaxaca",
  "estado": "Oaxaca",
  "coordenadas_aprox": [17.5, -97.5],
  "altitud_media_msnm": 1800,
  "clima": { "clasificacion_koppen": "BSk", ... },
  "suelo": { "tipo_suelo_dominante": "Leptosol", ... },
  "polinizadores": [
    {
      "nombre_comun": "Abeja melipona",
      "nombre_cientifico": "Melipona beecheii",
      "tipo": "abeja",
      "fuente": "https://enciclovida.mx/..."
    }
  ],
  "cultivos": [...],
  "flora_nativa": [...],
  "problematicas_ecologicas": [...],
  "recomendaciones_preliminares": [...],
  "fuentes_consultadas": [...],
  "fecha_extraccion": "2026-09-11"
}
```

---

## 🔧 Proveedores LLM

El sistema soporta intercambio transparente entre proveedores:

| Proveedor | Modelo Default | Uso Recomendado |
|-----------|---------------|-----------------|
| **Gemini** | `gemini-2.5-flash-lite` | Producción (structured output nativo) |
| **Groq** | `llama-3.3-70b-versatile` | Velocidad (inferencia ultra-rápida) |
| **Cohere** | `command-r7b-12-2024` | Alternativa (RAG optimizado) |

---

## 🌍 Regiones de Prueba Sugeridas

| Región | Características |
|--------|----------------|
| La Mixteca, Oaxaca | Zona semiárida, agricultura tradicional, erosión severa |
| Selva Lacandona, Chiapas | Alta biodiversidad, muchos polinizadores, deforestación |
| Valle del Yaqui, Sonora | Agricultura intensiva, zona árida, riego tecnificado |
| Sierra Norte, Puebla | Bosque mesófilo, café de sombra, meliponicultura |
| Península de Yucatán | Abejas meliponas, selva baja, apicultura |

---

## 📄 Licencia

Proyecto académico para el sistema Añi Ita.
