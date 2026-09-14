# 🌱 AniIta — Enjambre de Agentes para Recolección Ecológica y Agrícola de México

> Sistema multi-agente orquestado con **LangGraph** que automatiza la búsqueda, recolección, extracción y síntesis de datos ecológicos, geográficos y agrícolas de México para el proyecto **Añi Ita**.

---

## 🏗️ Arquitectura

```
START → [🔍 Investigador] → [🕷️ Scraper & RAG] → [🧠 Sintetizador] → END
              │                     │                      │
              ▼                     ▼                      ▼
         URLs temáticas      Contenido extraído      JSON DatosRegion
         (Tavily)            (Playwright+PyPDF)      (with_structured_output)
```

### Nodos del Enjambre

| Nodo | Función | Herramientas |
|------|---------|--------------|
| **Investigador** | Busca URLs en fuentes mexicanas por 5 categorías temáticas | `buscar_tavily_mexico`, `buscar_conabio`, `buscar_literatura_agricola` |
| **Scraper & RAG** | Extrae contenido de HTML/PDF y aplica RAG para textos extensos | `lector_web_playwright`, `lector_pdf_web`, `vectorizar_temporal` |
| **Sintetizador** | Convierte todo el contexto en JSON estructurado | `with_structured_output(DatosRegion)` |

### Fuentes Prioritarias

- 🇲🇽 **CONABIO** / EncicloVida — Biodiversidad
- 🌾 **SADER** / INIFAP — Agricultura
- 🗺️ **INEGI** — Geografía y suelos
- 🌐 **iNaturalist** México — Observaciones de campo
- 🎓 **UNAM** / SciELO — Literatura científica

---

## ⚡ Quickstart

### 1. Instalar dependencias

```bash
cd enjambre_agentes
pip install -r requirements.txt
playwright install chromium
```

### 2. Configurar API keys

```bash
cp .env.example .env
# Editar .env con tus API keys reales
```

### 3. Ejecutar

```bash
# Búsqueda básica
python main.py "La Mixteca, Oaxaca"

# Con proveedor específico
python main.py "Selva Lacandona, Chiapas" --provider Groq

# Con modelo y salida personalizada
python main.py "Valle del Yaqui, Sonora" --provider Cohere --model command-r-plus --output sonora.json
```

---

## 📦 Estructura del Proyecto

```
AniIta/
├── config/
│   ├── keys.py         # Gestión de API keys
│   └── models.py       # Fábrica LLM multi-proveedor (Gemini/Groq/Cohere)
├── schemas/
│   └── ecology.py      # Modelos Pydantic (DatosRegion, Polinizador, Cultivo, etc.)
├── tools/
│   ├── search.py       # Herramientas Tavily especializadas en México
│   ├── scraper.py      # Playwright + PyPDF para extracción web/PDF
│   └── rag.py          # RAG temporal con FAISS en memoria
├── agents/
│   ├── state.py        # ScrapingState (TypedDict compartido)
│   ├── investigador.py # Nodo 1: Búsqueda multi-temática
│   ├── scraper.py      # Nodo 2: Extracción y RAG
│   ├── sintetizador.py # Nodo 3: Síntesis JSON estructurada
│   └── graph.py        # Ensamblaje del grafo LangGraph
├── output/             # JSONs generados por región
├── main.py             # Entry point CLI
├── requirements.txt
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
