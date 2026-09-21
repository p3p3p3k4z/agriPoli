# (^-^) [AGRIPOLI] Sistema de Apoyo Multiagente para el Manejo Agricola y Preservacion de Polinizadores

> Sistema multiagente jerarquico orquestado con **LangGraph** que automatiza la investigacion edafologica, el balance agronomico, el diseno de islas polinizadoras y la generacion de mapas tridimensionales interactivos para el **Sistema Interactivo Inteligente para el Manejo Agricola y Preservacion de Polinizadores (AgriPoli)**.

---

## [O_O] [ARQUITECTURA] Arquitectura Jerarquica del Enjambre V3

El sistema se organiza en un **Grafo Maestro Jerarquico** orquestado por un **Supervisor Maestro V2** que delega a cuatro grupos independientes, un nodo de sintesis ejecutiva con persistencia local y validaciones ciclicas:

![Arquitectura del Enjambre Jerarquico V3](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/docs/arquitectura_v3.png)

```
(^-^) Usuario <---> [O_O] [Supervisor Maestro V2]
                              │
     ┌────────────────────────┴────────────────────────┐
     ▼                                                 ▼
[Grafo Maestro V3]                            [Herramientas Directas]
     │                                         * Catalogo Biodiversidad (3,922+)
     ▼                                         * RAG Local (4 colecciones)
[>_<] [Grupo 1: Extractor]                    * Delegaciones tematicas directas
(Tavily, Papers Cohere/ArXiv, Scraper Groq, Descargador)
     │
     ▼
(^-^) [Grupo 2: Agronomo] <───┐ (Loop retroalimentacion interno: max 3 ciclos)
(Suelo, Cultivos, SIAP, INEGI, SymPy)
     │                        │
     ▼                        │
(*_*) [Grupo 3: Ecologico] <──┘ (Loop retroalimentacion interno: max 3 ciclos)
(Flora nativa, Polinizadores, Catalogo SNIB, GBIF, Simbiosis)
     │
     ▼
[x_x] [Supervisor Validador] (Auditoria global inter-grupo)
     │
     ▼
[O_O] [Agente Sintetizador] ───> [Persistencia Local Human-in-the-Loop]
(Dossier 8 Secciones Tecnicas)   * data/reportes/diagnostico_<region>.md
     │                           * data/referencias.json
     │                           * data/knowledge/descargas/<region>/
     ▼ (Opcional bajo confirmacion)
(^o^) [Grupo 4: Generador 3D] (Three.js Pydantic Mapa3D, max 2 reintentos)
     │
     ▼
 (^_^) Fin / Resumen Ejecutivo en Consola + JSON Three.js
```

> **Documentacion y Diagramas Detallados:** Consulta el inventario completo de agentes y flujos en [`docs/ESTADO_PROYECTO.md`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/docs/ESTADO_PROYECTO.md) y el artefacto interactivo [`diagrama_enjambre.md`](file:///home/m4r10/.gemini/antigravity-ide/brain/faff0268-1b38-41cd-8f49-ac8c065bfc97/diagrama_enjambre.md).

---

## (^_^)/ [QUICKSTART] Inicio Rapido (Entorno `uv`)

### 1. Instalacion de dependencias
```bash
cd enjambre_agentes
uv sync
uv run playwright install chromium
```

### 2. Variables de Entorno (.env)
```bash
cp .env.example .env
# Configura tus API keys (GEMINI_API_KEY, GROQ_API_KEY, COHERE_API_KEY, TAVILY_API_KEY, INEGI_API_TOKEN, etc.)
```

### 3. Ejecutar el Chat Interactivo V3
```bash
uv run python scripts/main_supervisor_v2.py
```

---

## [CONFIG] [AGENTES: YAML] Configuracion Granular de Modelos (Hot-Reload)

Cada uno de los 22 agentes y mini-agentes puede configurarse independientemente en `config/agentes.yaml` sin modificar una sola linea de codigo, con soporte para **Google Gemini**, **Groq**, **Cohere** y **Ollama (Local)**:

```yaml
modelos:
  mini_tavily:          { proveedor: Gemini, modelo: gemini-2.0-flash,       temperatura: 0.1 }
  mini_academico:       { proveedor: Cohere, modelo: command-r7b-12-2024,   temperatura: 0.1 }
  mini_referencias_extractor: { proveedor: Cohere, modelo: command-r7b-12-2024, temperatura: 0.0 }
  mini_scraper:         { proveedor: Groq,   modelo: llama-3.1-8b-instant,   temperatura: 0.0 }
  fusionador_extractor: { proveedor: Groq,   modelo: llama3-70b-8192,        temperatura: 0.0 }
  fusionador_agronomo:  { proveedor: Gemini, modelo: gemini-3.5-flash-lite,  temperatura: 0.0 }
  agente_sintetizador:  { proveedor: Gemini, modelo: gemini-2.0-flash,       temperatura: 0.1 }
  supervisor:           { proveedor: Gemini, modelo: gemini-2.0-flash,       temperatura: 0.1 }

configuracion:
  max_ciclos_retroalimentacion: 3
  confirmacion_descarga: manual
  flow_type: Hibrido
  activar_3d_automatico: false
  max_iteraciones_supervisor: 3
  guardar_dossier_local: true
```

### Tolerancia a Fallos y Fallback Cruzado
El sistema cuenta con resiliencia multicapa:
* **Introspeccion dinamica**: Valida modelos en vivo con las APIs (`models_gemini.py`, `models_groq.py`, `models_cohere.py`) y mitiga errores 404 por modelos discontinuados.
* **Fallback cruzado automatico**: Conmuta transparentemente: `Gemini -> Groq -> Cohere -> Ollama (Local)` ante errores de cuota (HTTP 429) o fallos de red.
* **Operatividad 100% Offline**: Soporte nativo para Ollama (`llama3.1:latest`) en caso de no disponer de conexion a internet o API keys.

Desde la CLI interactiva puedes inspeccionar y cambiar modelos en caliente:
* `/config-agentes` : Muestra la tabla de configuracion de los 22 agentes.
* `/agente mini_academico command-r7b-12-2024` : Cambia el modelo en tiempo de ejecucion.
* `/agente-provider mini_academico Cohere` : Cambia el proveedor en tiempo de ejecucion.

---

## [._.] [DATOS] Catalogos Locales, RAG y Almacenamiento de Dossiers

1. **Catalogo de Biodiversidad Mexicana** (`data/descargas_masivas/`):
   * 1,188 especies de flora nativa y melifera.
   * 2,734 especies de polinizadores nativos (abejas, meliponas, abejorros, colibries, mariposas).
   * Consulta rapida con `/biodiversidad <termino>` o mediante la herramienta `buscar_biodiversidad_local`.

2. **Base de Conocimientos RAG Vectorial** (`data/knowledge/`):
   * `suelo/`: Estudios edafologicos, retencion de humedad, texturas, NPK.
   * `agricultura/`: Guias tecnicas SADER/INIFAP y manuales de rotacion de cultivos.
   * `polinizadores/`: Guias CONABIO, calendarios florales y preservacion.
   * `general/`: Normativas SEMARNAT y manuales agroecologicos integrales.
   * Administracion con `/rag status` y `/rag rebuild`.

3. **Repositorio Jerarquico Regional y Descargas (`regiones/<estado>/<municipio>/`)**:
   * `regiones/<estado>/<municipio>/referencias.json`: Indice estructurado de metadatos, fuentes y estado de descarga especifico de la region.
   * `regiones/<estado>/<municipio>/diagnostico.md`: Dossier agroecologico completo en 8 secciones tecnicas con frontmatter YAML.
   * `regiones/<estado>/<municipio>/datos_relevantes.json`: Parametros estructurados (clima, suelo, rotacion regenerativa en 4 grupos, flora, polinizadores y control biologico) para alimentar la precision del sistema.
   * `regiones/<estado>/<municipio>/fuentes/`: Documentos organizados en subcarpetas `pdf/` (articulos y monografias), `html/` (webs y archivos `.md` limpios para RAG), y `csv/` (datos estadisticos).
   * *Compatibilidad*: Se preserva en paralelo la ruta base `data/reportes/` y el indice maestro `data/referencias.json`.

---

## [V3] [DIAGRAMAS] Diagramas Estaticos del Sistema

Generados automaticamente en la carpeta `docs/` con `uv run python scripts/generar_diagrama_v3.py` (o comando `/diagrama` en CLI):
* `docs/arquitectura_v3.png` — Grafo Maestro Inter-Grupo V3 con Sintetizador
* `docs/arquitectura_agentes.png` — Arquitectura Global de Agentes
* `docs/grupo_extractor.png` — Sub-grafo Grupo Extractor
* `docs/grupo_agronomo.png` — Sub-grafo Grupo Agronomo con Loop
* `docs/grupo_ecologico.png` — Sub-grafo Grupo Ecologico con Loop
* `docs/grupo_3d.png` — Sub-grafo Generador 3D con Validacion Pydantic
* `docs/grupo_supervisor.png` — Arquitectura del Supervisor Maestro

---

## (^-^)/ [COMANDOS: CLI] Comandos Principales de la Terminal

| Comando | Descripcion |
|---------|-------------|
| `/help` | Manual de ayuda completo y explicacion de carpetas RAG |
| `/config` | Estado de API keys y modelo global |
| `/config-agentes` | Tabla de configuracion de los 22 agentes |
| `/agente <nombre> <modelo>` | Cambia el modelo de un agente en caliente |
| `/agente-provider <nombre> <prov>` | Cambia el proveedor de un agente (Gemini, Groq, Cohere, Ollama) |
| `/run [region]` | Ejecuta el flujo V3 completo; muestra el **Resumen Ejecutivo de 8 secciones** en consola y solicita confirmacion `[S/n]` para guardar el dossier y descargar las fuentes |
| `/run3d [region]` | Ejecuta el flujo V3, muestra el resumen ejecutivo y compila el modelo espacial 3D |
| `/biodiversidad <especie>` | Consulta el catalogo de 3,922+ especies nativas |
| `/rag [status\|rebuild]` | Consulta o reconstruye la base RAG |
| `/diagrama` | Regenera los 7 diagramas estaticos PNG en `docs/` |
| `/clear` | Limpia la sesion actual |
| `/exit` | Cierra la terminal |

---

## (^-^)/ [LICENCIA] Licencia

Proyecto academico — Sistema Interactivo Inteligente para el Manejo Agricola y Preservacion de Polinizadores (AgriPoli).

