# (^-^) [ESTADO DEL PROYECTO] AgriPoli V3 — Enjambre Jerarquico Multiagente

> **Sistema Interactivo Inteligente para el Manejo Agricola y Preservacion de Polinizadores Nativos (AgriPoli)**
> Fecha de corte: Septiembre 2026 | Arquitectura: LangGraph Multiagente Jerarquico V3

---

## 1. (O_O) [RESUMEN: EJECUTIVO] Resumen Ejecutivo

El proyecto **AgriPoli** es un sistema multiagente de alta precision disenado para la planificacion agroecologica y la conservacion de polinizadores nativos en Mexico. El sistema recopila datos climaticos, edafologicos, agronomicos y de biodiversidad desde fuentes oficiales (SADER, SIAP, INEGI, CONABIO, EncicloVida, GBIF, UNAM) y genera tanto planes de rotacion de cultivos con balance hidrico y nutricional, como disenos de islas polinizadoras y mapas tridimensionales interactivos en formato Three.js.

### Principios de Diseno Aplicados
* **SOLID**: Separacion estricta de responsabilidades en 4 grupos autonomos con estados fuertemente tipados (`TypedDict`), interfaces desacopladas e inversion de dependencias mediante la fabrica LLM.
* **Hot-Reload de Modelos**: Configuracion centralizada en `config/agentes.yaml` que permite alternar proveedores y modelos por cada agente en tiempo real sin reiniciar el sistema ni tocar codigo.
* **Tolerancia a Fallos Multimodelo y Resiliencia**: Mecanismo de fallback automatico entre proveedores (`Gemini -> Groq -> Cohere -> Ollama`) y recuperacion ante errores HTTP 429 (cuota agotada), 404 (modelos discontinuados) o caidas de red.
* **Sintesis Ejecutiva y Trazabilidad**: Nodo sintetizador especializado (`agente_sintetizador`) que compila diagnosticos claros y estructurados en 8 secciones tecnicas con fuentes indexadas, inmediatamente visibles en terminal.
* **Persistencia Local Human-in-the-Loop**: Confirmacion interactiva (`[S/n]`) para almacenar dossiers tecnicos (`data/reportes/`), indexar fuentes (`data/referencias.json`) y descargar documentos de soporte offline (`data/knowledge/descargas/`).
* **Loops de Retroalimentacion**: Validadores internos con capacidad de rechazo y autocorreccion ciclica (hasta 3 iteraciones) ante inconsistencias agroecologicas (ej. recomendacion de cultivo incompatible con el clima Koppen de la region).
* **Salida Limpia y Expresiva**: Cumplimiento riguroso de convencion de terminal en texto plano con kaomojis ASCII expresivos (`(^-^)/`, `[O_O]`, `(*_*)!`, `(ง •̀_•́)ง`, `[x_x]`) y etiquetas formales en mayusculas, sin emojis graficos unicode.

---

## 2. [O_O] [ARQUITECTURA] Arquitectura Jerarquica del Enjambre V3

El enjambre se estructura en un grafo maestro orquestado por un **Supervisor Maestro V2** que delega tareas a cuatro grupos especializados, un nodo de sintesis ejecutiva con persistencia local y sub-grafos con loops de retroalimentacion:

![Arquitectura del Enjambre Jerarquico V3](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/docs/arquitectura_v3.png)

```mermaid
flowchart TD
    %% 1. USUARIO Y CONTROL
    subgraph Control ["1. CONTROL Y USUARIO (Human-in-the-Loop)"]
        direction TB
        Usuario["(^-^) Usuario [Human-in-the-Loop]<br/>Peticiones | Confirmaciones | Guardado Local | Decision 3D"]
        Supervisor{{"[O_O] Supervisor Maestro V2 [Orquestador ReAct]<br/>Enrutador de Consultas y Despachador de Tareas"}}
        Usuario <-->|Dialogo y Confirmaciones| Supervisor
    end

    %% 2. ALMACENES LOCALES Y RAG
    subgraph Datos ["2. ALMACENES LOCALES Y RAG"]
        direction LR
        CatalogoBio[("Catalogo Biodiversidad Mexicana<br/>(1,188 Flora + 2,734 Polinizadores)")]
        RAGDB[("Base Vectorial RAG FAISS/Chroma<br/>(Suelo, Agricultura, Polinizadores, General)")]
        RefDB[("referencias.json<br/>(Trazabilidad y fuentes)")]
        ReportesDB[("data/reportes/<br/>(Dossiers Markdown)")]
    end

    Supervisor <-->|Consultas directas| CatalogoBio
    Supervisor <-->|Consultas semanticas| RAGDB

    %% 3. GRUPO EXTRACTOR
    subgraph Grupo1 ["3. GRUPO 1: EXTRACTOR (Alimentacion Externa del Sistema)"]
        direction TB
        subgraph MiniExtractores ["Mini-Agentes de Investigacion Web y Documental"]
            direction LR
            Tavily["(O_O) mini_tavily<br/>Tavily / CONABIO / EncicloVida<br/><i>Gemini 2.0 Flash</i>"]
            Acad["(^_~) mini_academico<br/>arXiv / Semantic Scholar / UNAM<br/><i>Cohere Command R7B</i>"]
            RefExtr["[o_o] mini_referencias_extractor<br/>Citas y Trazabilidad Bibliografica<br/><i>Cohere Command R7B</i>"]
            Scraper["[~_~] mini_scraper<br/>Playwright / PDFs / Selenium<br/><i>Groq Llama 3.1 8B</i>"]
        end
        FusExtr["(^-^)/ fusionador_extractor<br/>Join, Deduplicacion y Sintesis"]
        Descargador{{"(o.O)? descargador [Human-in-the-Loop]<br/>Pregunta autorizacion al usuario si faltan datos locales"}}

        Tavily --> FusExtr
        Acad --> FusExtr
        RefExtr --> FusExtr
        Scraper --> FusExtr
        FusExtr --> Descargador

        subgraph StubsExtr ["Futuros Mini-Agentes Extractor"]
            direction LR
            StubNASA["mini_nasa_power"]
            StubSoil["mini_soilgrids"]
            StubINat["mini_inaturalist"]
            StubSent["mini_sentinel"]
        end
    end

    %% 4. GRUPO AGRONOMO
    subgraph Grupo2 ["4. GRUPO 2: AGRONOMO (Suelo, Cultivos y Rotaciones)"]
        direction TB
        subgraph MiniAgros ["Mini-Agentes Agronomicos"]
            direction LR
            Suelo["[O_O] mini_suelo<br/>Edafologia, pH, texturas, NPK"]
            Cultivo["(-w-)/ mini_cultivo<br/>Especies, viabilidad y siembra"]
            SIAP["[._.] mini_siap<br/>Estadisticas SADER/SIAP"]
            INEGI["(O_O) mini_inegi_agro<br/>Indicadores agropecuarios"]
            Calc["(˘ワ˘) mini_calculadora<br/>Balance hidrico y formulas"]
            Rotacion["(u_u) mini_rotacion_regenerativa<br/>Secuencias funcionales N/D/P/H"]
        end
        FusAgro{{"[x_x] fusionador_agronomo<br/>Arbitro y Auditor Edafoclimatico"}}

        Suelo --> FusAgro
        Cultivo --> FusAgro
        SIAP --> FusAgro
        INEGI --> FusAgro
        Calc --> FusAgro
        Rotacion --> FusAgro

        %% Loop retroalimentacion interno
        FusAgro -.->|"[LOOP: RECHAZADO]<br/>Inconsistencia climatica/suelo (Max 3 ciclos)"| Cultivo
        FusAgro -.->|"[LOOP: RECHAZADO]<br/>Ajuste rotacion regenerativa"| Rotacion

        subgraph StubsAgro ["Futuros Mini-Agentes Agronomo"]
            direction LR
            StubRF["mini_random_forest"]
            StubMercado["mini_mercado_agricola"]
            StubAgua["mini_agua"]
            StubFito["mini_fitosanidad"]
        end
    end

    %% 5. GRUPO ECOLOGICO
    subgraph Grupo3 ["5. GRUPO 3: ECOLOGICO (Islas Polinizadoras y Simbiosis)"]
        direction TB
        subgraph MiniEcos ["Mini-Agentes Ecologicos"]
            direction LR
            Flora["(*-*) mini_flora_nativa<br/>Flora nativa segun clima Koppen"]
            Poli["(^w^) mini_polinizadores<br/>Catalogo abejas y fauna"]
            CatLocal["(._.)/ mini_catalogo_local<br/>Registros CONABIO y NOM-059"]
            GBIF["[~_~] mini_gbif<br/>Taxonomia global API GBIF"]
            ControlBio["(>o<) mini_control_biologico<br/>Depredadores, catarinas y pulgones"]
            Atractores["(^-^)~ mini_atractores_polinizadores<br/>Calendario floral y polinizacion"]
        end
        FusEco{{"[x_x] fusionador_ecologico<br/>Arbitro y Auditor Ecologico"}}

        Flora --> FusEco
        Poli --> FusEco
        CatLocal --> FusEco
        GBIF --> FusEco
        ControlBio --> FusEco
        Atractores --> FusEco

        %% Loop retroalimentacion interno
        FusEco -.->|"[LOOP: RECHAZADO]<br/>Incompatibilidad agro/eco (Max 3 ciclos)"| Flora
        FusEco -.->|"[LOOP: RECHAZADO]<br/>Ajuste atrayentes/depredadores"| ControlBio

        subgraph StubsEco ["Futuros Mini-Agentes Ecologico"]
            direction LR
            StubNOM["mini_nom059"]
            StubKoppen["mini_koppen"]
            StubCorredor["mini_corredor_biologico"]
        end
    end

    %% 6. SUPERVISOR VALIDADOR
    SupervisorValidador{{"[x_x] Supervisor Validador<br/>Auditor de Coherencia Global Inter-Grupo"}}

    %% 7. AGENTE SINTETIZADOR Y PERSISTENCIA
    subgraph SintesisNodo ["7. SINTESIS EJECUTIVA Y PERSISTENCIA"]
        direction TB
        Sintetizador["[O_O] Agente Sintetizador<br/>Dossier 8 Secciones Tecnicas<br/>+ Trazabilidad de Fuentes"]
        Persistencia[("Persistencia Local [Human-in-the-Loop]<br/>data/reportes/ | data/referencias.json | descargas/")]
        Sintetizador -.->|Guardado interactivo [S/n]| Persistencia
    end

    %% 8. GRUPO 3D
    subgraph Grupo4 ["8. GRUPO 4: GENERADOR 3D (Procedural Three.js)"]
        direction TB
        Fus3D["(^o^) fusionador_3d<br/>Consolida coordenadas (x,y,z) y paleta hex"]
        Estr["(^o^) estructurador<br/>Pydantic Mapa3D (Structured Output)"]
        Val3D{{"[x_x] validador_3d<br/>Auditor de Esquema Pydantic"}}

        Fus3D --> Estr --> Val3D
        Val3D -.->|"[LOOP: INVALIDO]<br/>Reintento estructuracion (Max 2 ciclos)"| Estr
    end

    SalidaFinal([\"(^_^) [SALIDA FINAL]<br/>Resumen Ejecutivo 8 Secciones + Dossier Local + JSON Mapa3D Three.js\"])

    %% Conexiones principales de flujo
    Supervisor -->|1. Inicia recoleccion externa| Grupo1
    Descargador -->|Contexto web y oficial consolidado| Grupo2
    FusAgro -->|Propuestas agricolas aprobadas| Grupo3
    FusEco -->|Plan ecologico aprobado| SupervisorValidador

    %% Loops inter-grupo
    SupervisorValidador -.->|"[LOOP INTER-GRUPO: Falta contexto]"| Grupo1
    SupervisorValidador -.->|"[LOOP INTER-GRUPO: Colision agro/eco]"| Grupo2

    %% Validacion, Sintesis y ramificaciones 3D
    SupervisorValidador -->|APROBADO: Sintetizar diagnostico| Sintetizador
    Sintetizador -->|Activar 3D bajo confirmacion| Grupo4
    Sintetizador -->|Finalizar sin 3D| SalidaFinal
    Val3D -->|VALIDO: Exporta mapa3d.json| SalidaFinal
```

---

## 3. [LISTA] [INVENTARIO: AGENTES] Inventario Completo de Agentes y Mini-Agentes

Actualmente el sistema integra **22 agentes y mini-agentes activos**, clasificados en el Supervisor Maestro, 4 Grupos Jerarquicos, el Agente Sintetizador y los Agentes Legacy/Fallback:

### A. Supervisor Maestro
* **Archivo**: [`agents/supervisor_v2.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/agents/supervisor_v2.py)
* **Rol**: Orquestador principal, interfaz conversacional con el usuario, auditor de coherencia y despachador de herramientas.
* **Configuracion YAML**: Proveedor `Gemini`, Modelo `gemini-2.0-flash`, Temp `0.1`.
* **Herramientas**:
  1. `ejecutar_enjambre_v3`: Ejecuta el flujo maestro completo (Extractor -> Agronomo -> Ecologico -> Supervisor -> Sintetizador -> 3D).
  2. `delegar_solo_extractor`: Consulta rapida de clima, geografia y biodiversidad.
  3. `delegar_solo_agronomo`: Recomendaciones exclusivas de cultivos y suelo.
  4. `delegar_solo_ecologico`: Diseno exclusivo de islas polinizadoras y conservacion.
  5. `consultar_conocimiento_rag`: Consulta semantica en las 4 colecciones vectoriales locales.
  6. `buscar_biodiversidad_local`: Busqueda difusa en el catalogo de 3,922+ especies nativas.

---

### B. Grupo 1: Extractor (`agents/groups/group_extractor.py`)
* **Responsabilidad**: Recopilar y consolidar informacion fresca de la region desde la web, articulos cientificos y bases gubernamentales.
* **Sub-grafo**: Secuencia de investigacion con consolidacion (Join) y nodo de descarga con confirmacion.

| Mini-Agente / Nodo | Rol | Herramientas Integradas | Config YAML Default |
|--------------------|-----|-------------------------|---------------------|
| `mini_tavily` | Busqueda web y biodiversidad | `buscar_tavily_mexico`, `buscar_conabio`, `explorador_enciclovida` | Gemini `gemini-2.0-flash` (0.1) |
| `mini_academico` | Literatura cientifica y papers | `buscar_arxiv_agricola`, `buscar_semantic_scholar_agricola`, `formateador_citas_agricola`, `buscar_wikipedia_mx` | Cohere `command-r7b-12-2024` (0.1) |
| `mini_referencias_extractor` | Citas y trazabilidad bibliografica | Extraccion de metadatos, formateo de citas APA/BibTeX y trazabilidad oficial | Cohere `command-r7b-12-2024` (0.0) |
| `mini_scraper` | Scraping profundo gubernamental y PDFs | `buscar_tavily_mexico`, `lector_web_playwright`, `lector_pdf_web`, `lector_web_selenium` | Groq `llama-3.1-8b-instant` (0.0) |
| `fusionador_extractor` | Join, sintesis y deduplicacion | LLM Directo con extraccion XML de URLs de fuentes | Groq `llama3-70b-8192` (0.0) |
| `descargador` | Gestor de descargas masivas | Prompt Human-in-the-Loop para autorizar descargas a disco si falta contexto local | Gemini `gemini-2.0-flash` (0.1) |

---

### C. Grupo 2: Agronomo (`agents/groups/group_agronomo.py`)
* **Responsabilidad**: Determinar aptitud de suelo, calcular balances nutricionales/hidricos y proponer rotacion de cultivos.
* **Sub-grafo**: 6 mini-agentes especializados + Fusionador Arbitro con **Loop de Retroalimentacion (hasta 3 ciclos)**.

| Mini-Agente / Nodo | Rol | Herramientas Integradas | Config YAML Default |
|--------------------|-----|-------------------------|---------------------|
| `mini_suelo` | Analisis edafologico y quimica | `buscar_estudios_suelo`, `calcular_agronomia` (SymPy), RAG `suelo` | Gemini `gemini-flash-lite-latest` (0.2) |
| `mini_cultivo` | Propuesta de cultivos y viabilidad | Agente ReAct `crear_agro_experto`, literatura SADER/SIAP | Gemini `gemini-3.5-flash-lite` (0.2) |
| `mini_siap` | Estadisticas oficiales de produccion | `buscar_literatura_agricola`, bases SIAP locales | Gemini `gemini-flash-lite-latest` (0.0) |
| `mini_inegi_agro` | Indicadores socioeconomicos y agro | `consultar_indicador_inegi`, `usar_inegipy_catalogo` | Gemini `gemini-flash-lite-latest` (0.1) |
| `mini_calculadora` | Matematica agronomica formal | `calcular_agronomia` con motor simbolico SymPy | Gemini `gemini-flash-lite-latest` (0.0) |
| `mini_rotacion_regenerativa` | Secuencias de rotacion N/D/P/H | Formato estructurado 4 grupos funcionales (Nitrogeno, Descompactacion, Plagas, Hidrico) | Gemini `gemini-3.5-flash-lite` (0.2) |
| `mini_prompt_cultivo` | Prompts de recuadro de parcela agrícola | Asociación de cultivos, textura de suelo, surcos y manejo hídrico para render 3D | Gemini `gemini-flash-lite-latest` (0.2) |
| `fusionador_agronomo` | Join, arbitro y auditor de viabilidad | LLM Arbitro: si detecta incongruencia edafoclimatica, emite `RECHAZADO` y retroalimenta al `mini_cultivo` o `mini_rotacion` | Gemini `gemini-3.5-flash-lite` (0.0) |

---

### D. Grupo 3: Ecologico (`agents/groups/group_ecologico.py`)
* **Responsabilidad**: Disenar matrices de conservacion, islas florales y sinergias biologicas beneficiosas.
* **Sub-grafo**: 6 mini-agentes especializados + Fusionador Arbitro con **Loop de Retroalimentacion (hasta 3 ciclos)**.

| Mini-Agente / Nodo | Rol | Herramientas Integradas | Config YAML Default |
|--------------------|-----|-------------------------|---------------------|
| `mini_flora_nativa` | Seleccion botanica segun clima Koppen | Agente ReAct `crear_agente_ecologico`, CONABIO | Gemini `gemini-flash-lite-latest` (0.2) |
| `mini_polinizadores` | Identificacion de abejas nativas/fauna | `consultar_catalogo_biodiversidad_local` (3,922+ especies) | Gemini `gemini-flash-lite-latest` (0.2) |
| `mini_catalogo_local` | Busqueda taxonomica oficial | `buscar_conabio`, `buscar_datos_unam`, SNIB/EncicloVida | Gemini `gemini-flash-lite-latest` (0.1) |
| `mini_gbif` | Taxonomia global e indices de confianza | Cliente asincrono `fetch_gbif_species` (API REST GBIF) | Gemini `gemini-flash-lite-latest` (0.0) |
| `mini_control_biologico` | Depredadores beneficos y control natural | Fauna auxiliar: catarinas contra pulgones, crisopas, parasitoides | Gemini `gemini-flash-lite-latest` (0.2) |
| `mini_atractores_polinizadores` | Calendario floral y atrayentes | Sinergias para Bombus, Xylocopa, Apis, abejas meliponas | Gemini `gemini-flash-lite-latest` (0.2) |
| `fusionador_ecologico` | Join y auditor de compatibilidad ecologica | LLM Arbitro: evalua si la flora complementa los cultivos del agronomo; si hay colision, emite `RECHAZADO` y retroalimenta a `mini_flora_nativa` | Gemini `gemini-3.5-flash-lite` (0.0) |

---

### E. Agente Sintetizador (`agents/graph_v3.py`)
* **Responsabilidad**: Compilar y estructurar el diagnostico integral en un Resumen Ejecutivo riguroso con 8 secciones tecnicas y preparar la persistencia local de fuentes.
* **Nodo en Grafo V3**: `nodo_sintetizador` (orquestado inmediatamente tras `supervisor_validador`).
* **Configuracion YAML**: Proveedor `Gemini` (o fallbacks Groq/Cohere/Ollama), modelo `gemini-2.0-flash` (0.1).
* **Las 8 Secciones del Resumen Ejecutivo**:
  1. **Perfil Regional y Coordenadas**: Municipio, estado, coordenadas aproximadas, elevacion (msnm) y clasificacion orografica.
  2. **Clima y Clasificacion Koppen**: Regimen termopluviometrico, clasificacion bioclimatica formal (ej. Aw, Cwb, Bs), temperaturas estacionales, precipitacion anual y periodos de canicula o heladas.
  3. **Propiedades Edafologicas del Suelo**: Textura predominante, pH estimado, materia organica, limitaciones edaficas y plan de enmiendas conforme a la norma **NOM-021-SEMARNAT-2000**.
  4. **Cultivos Recomendados y Rotacion Regenerativa**: Especies principales y viables para la region, organizadas en una secuencia funcional de rotacion regenerativa en **4 grupos** (Fijadores de Nitrogeno, Descompactadores Radiculares, Supresores de Plagas, Eficiencia Hidrica).
  5. **Flora Nativa de Soporte**: Arboles, arbustos y herbaceas autoctonas con su estatus de conservacion conforme a la norma **NOM-059-SEMARNAT-2010** (P, A, Pr, Amenazada, Sujeta a proteccion especial).
  6. **Polinizadores Nativos Asociados**: Especies de abejas nativas solitarias y meliponinos, colibries, murcielagos nectarivoros y lepidopteros, acompanados de su calendario floral y sinergias.
  7. **Diseno Ecosistemico Integral**: Disposicion de islas polinizadoras, corredores biologicos, esquemas de control biologico mediante fauna auxiliar (catarinas, crisopas, parasitoides) y seleccion botanica para barreras rompeviento.
  8. **Fuentes Oficiales y Trazabilidad**: Lista numerada con nombre formal de la institucion (SADER, INEGI, CONABIO, UNAM, GBIF, etc.), titulo del documento o base consultada, y URL activa o referencia bibliografica estandarizada.

---

### F. Grupo 4: Generador 3D (`agents/groups/group_3d.py`)
* **Responsabilidad**: Traducir las propuestas narrativas aprobadas a un esquema estructurado compatible con Three.js.
* **Sub-grafo**: Pipeline de compilacion con **Loop de Validacion Pydantic (hasta 2 reintentos)**.

| Sub-Agente / Nodo | Rol | Herramientas / Funciones | Config YAML Default |
|-------------------|-----|--------------------------|---------------------|
| `fusionador_3d` | Reconciliador espacial de propuestas | LLM Directo: consolida coordenadas relativas (x,y,z), radios y paletas hex | Gemini `gemini-flash-lite-latest` (0.0) |
| `mini_referencias_3d` | Estandares espaciales y fuentes | `buscar_tavily_mexico` con directivas FAO, SADER e INIFAP | Gemini `gemini-flash-lite-latest` (0.1) |
| `mini_prompt_isla` | Generador de prompts para modelado 3D | Extraccion ecorregional botanica (dosel, sotobosque, cobertura, polinizadores, biocontrol, cultivos circundantes y horizonte) | Gemini `gemini-flash-lite-latest` (0.2) |
| `estructurador` | Compilador de esquema Pydantic | `invocar_estructurador` con structured output sobre `Mapa3D` | Gemini `gemini-flash-lite-latest` (0.0) |
| `validador_3d` | Auditor sintactico y dimensional | Validador Pydantic contra `schemas/threejs_schema.py`. Si falla, reintenta | Gemini `gemini-flash-lite-latest` (0.0) |

---

### G. Agentes Preservados (V1 / Fallbacks)
De acuerdo con las politicas de estabilidad y conservacion del proyecto, ningun agente previo ha sido eliminado:
* [`agents/supervisor.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/agents/supervisor.py): Supervisor ReAct original (V1), conservado como fallback de recuperacion.
* [`agents/agro_experto.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/agents/agro_experto.py): Agente ReAct agricola V1, reutilizado internamente por `mini_cultivo`.
* [`agents/ecologico.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/agents/ecologico.py): Agente ReAct ecologico V1, reutilizado internamente por `mini_flora_nativa`.
* [`agents/investigador.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/agents/investigador.py) y [`agents/extractor.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/agents/extractor.py): Motores originales de navegacion y extraccion.
* [`agents/graph_v2.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/agents/graph_v2.py): Enjambre plano V2 ejecutable para pruebas de rendimiento.

---

### H. Mini-Agentes Sugeridos y Disenados para Futuras Fases (Roadmap)
En el codigo fuente ya se encuentran identificados y modelados los stubs para extensiones futuras:
* **En Grupo Extractor**:
  * `mini_nasa_power`: Conector a la API de agroclimatologia y radiacion solar de NASA POWER.
  * `mini_soilgrids`: Conector al servicio REST global de perfiles de suelo ISRIC SoilGrids.
  * `mini_inaturalist`: Lector de avistamientos comunitarios en tiempo real via API iNaturalist.
  * `mini_sentinel`: Procesador de indices espectrales NDVI de parcelas satelitales.
* **En Grupo Agronomo**:
  * `mini_random_forest`: Evaluador predictivo local con modelo Random Forest preentrenado sobre degradacion de suelo.
  * `mini_mercado_agricola`: Analizador de precios corrientes en centrales de abasto (SNIIM / SE).
  * `mini_agua`: Evaluador de concesiones hidroagricolas y estres hidrico CONAGUA.
  * `mini_fitosanidad`: Diagnostico fitosanitario preventivo SENASICA.
* **En Grupo Ecologico**:
  * `mini_nom059`: Validador automatico de estatus de proteccion oficial (P, A, Pr, E) en la NOM-059-SEMARNAT.
  * `mini_koppen`: Clasificador bioclimatico automatizado por termopluviometria.
  * `mini_corredor_biologico`: Disenador de conectividad ecologica y amortiguamiento de paisajes.

---

## 4. [CONFIG] [SISTEMA: CONFIGURACION] Sistema de Configuracion y Modelos

### Archivo Central: `config/agentes.yaml`
Permite configurar de forma granular el proveedor y modelo para cada agente de forma independiente, soportando **Gemini**, **Groq**, **Cohere** y **Ollama (Local)**:

```yaml
modelos:
  mini_tavily:          { proveedor: Gemini, modelo: gemini-2.0-flash,       temperatura: 0.1 }
  mini_academico:       { proveedor: Cohere, modelo: command-r7b-12-2024,   temperatura: 0.1 }
  mini_referencias_extractor: { proveedor: Cohere, modelo: command-r7b-12-2024, temperatura: 0.0 }
  mini_scraper:         { proveedor: Groq,   modelo: llama-3.1-8b-instant,   temperatura: 0.0 }
  fusionador_extractor: { proveedor: Groq,   modelo: llama3-70b-8192,        temperatura: 0.0 }
  mini_suelo:           { proveedor: Gemini, modelo: gemini-flash-lite-latest, temperatura: 0.2 }
  agente_sintetizador:  { proveedor: Gemini, modelo: gemini-2.0-flash,       temperatura: 0.1 }
  supervisor:           { proveedor: Gemini, modelo: gemini-2.0-flash,       temperatura: 0.1 }
  # ... (22 agentes configurables individualmente)

configuracion:
  max_ciclos_retroalimentacion: 3
  confirmacion_descarga: manual
  flow_type: Hibrido
  activar_3d_automatico: false
  max_iteraciones_supervisor: 3
  guardar_dossier_local: true
```

### Proveedores Soportados y Modelos Verificados
1. **Google Gemini**: Modelos `gemini-2.0-flash`, `gemini-2.5-flash`, `gemini-flash-lite-latest`. Excelente para vision, ReAct multivariable y generacion general.
2. **Groq (Inferencia Ultrarrapida)**: Modelos `llama-3.1-8b-instant`, `llama3-70b-8192`. Optimo para scraping rapido, estructuracion XML y deduplicacion.
3. **Cohere Command**: Modelos `command-r7b-12-2024`, `command-r-plus-08-2024`, `command-light`. Especializado en generacion con citas verificadas (Grounding), literatura cientifica y sintesis documental.
4. **Ollama (Respaldo 100% Offline / Local)**: Modelos `llama3.1:latest`, `gemma4:latest`, `qwen3.6:latest` corriendo sobre `http://localhost:11434`. Garantiza cero costos de API y operatividad total sin conexion a internet.

### Arquitectura de Resiliencia, Fallbacks Cruzados y Excepciones
El modulo [`config/models.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/config/models.py) implementa un sistema multicapa de tolerancia a fallos:

* **Introspeccion Dinamica de Modelos**: Antes de instanciar cualquier LLM, los modulos [`config/models_gemini.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/config/models_gemini.py), [`config/models_groq.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/config/models_groq.py) y [`config/models_cohere.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/config/models_cohere.py) consultan las APIs oficiales en vivo. Si el modelo asignado en YAML fue descontinuado (HTTP 404), la fabrica mapea automaticamente al reemplazo oficial mas cercano sin quebrar la ejecucion.
* **Cadena de Fallbacks Cruzados (`_crear_fallbacks_cruzados`)**: Cada LLM es envuelto en una cadena nativa `with_fallbacks` de LangChain. Si el proveedor principal falla, el enjambre conmuta automaticamente al siguiente proveedor:
  $$\text{Gemini} \longrightarrow \text{Groq} \longrightarrow \text{Cohere} \longrightarrow \text{Ollama (Local)}$$
* **Manejo Automatico de Excepciones**:
  - `429 Too Many Requests / ResourceExhausted`: Cuota de API agotada o limitacion de tasa.
  - `404 Not Found / ModelDecommissioned`: Modelos deprecados o retirados por el proveedor.
  - `503 Service Unavailable`: Sobrecarga temporal del backend.
  - `TimeoutError / ConnectionError`: Cortes en la conexion de red externa.
* **Degradacion Graciosa 100% Offline**: Si la conexion a internet se pierde por completo o todas las API keys externas agotan sus limites, el sistema conmuta a Ollama local (`llama3.1:latest`), completando la consulta sin interrumpir al usuario.

---

## 5. [DATOS] [CATALOGOS: RAG] Datos, Catalogos y Motor RAG

### Catalogo de Biodiversidad Mexicana (`data/descargas_masivas/`)
Integra bases masivas procesadas a nivel nacional:
* **1,188 especies de flora nativa y melifera**.
* **2,734 especies de polinizadores nativos** (himenopteros, lepidopteros, colibries, quiropteros).
* Indexacion rapida mediante `tools/catalogo_biodiversidad.py` con busqueda contextual por region o nombre.

### Motor RAG Tematico (`data/knowledge/` y `tools/rag_engine.py`)
Estructurado en 4 colecciones vectoriales especializadas utilizando FAISS / Chroma:
1. `suelo/`: Monografias edafologicas, curvas de retencion de humedad, analisis de texturas y pH.
2. `agricultura/`: Guias tecnicas de manejo agronomico de SADER, INIFAP y manuales de rotacion.
3. `polinizadores/`: Guias de identificacion de polinizadores, periodos de floracion y conservacion.
4. `general/`: Normativas SEMARNAT, ordenamiento ecologico territorial y agroforesteria.

### Repositorio Jerarquico Regional (`regiones/<estado>/<municipio>/`)
El sistema organiza y conserva toda la informacion descargada de forma ordenada y modular por region geografica (ejemplo: `regiones/oaxaca/puerto_escondido/`), vinculada mediante el gestor [`tools/gestor_regiones.py`](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/tools/gestor_regiones.py):
* **`referencias.json` Local**: Alojado directamente en su carpeta regional correspondiente (`regiones/<estado>/<municipio>/referencias.json`). Contiene los metadatos completos de las fuentes oficiales consultadas, instituciones emisoras (SADER, CONABIO, UNAM, INEGI, SEMAR), URLs, tamanos en bytes y estado de descarga.
* **`diagnostico.md`**: El dossier agroecologico integral completo con las 8 secciones tecnicas y frontmatter YAML para consulta offline.
* **`datos_relevantes.json`**: Parametros estructurados clave (clasificacion Koppen, temperatura, precipitacion mm, pH del suelo, enmiendas NOM-021, cultivos viables, rotacion regenerativa en 4 grupos, flora nativa NOM-059 y fauna auxiliar de control biologico).
* **`fuentes/`**:
  - `fuentes/pdf/`: Documentos oficiales, monografias y normativas en formato PDF (ej. SEMAR, SEMARNAT, INIFAP).
  - `fuentes/html/`: Paginas web institucionales descargadas (`.html`) y su version limpia en Markdown (`.md`) para lectura de agentes e indexacion RAG.
  - `fuentes/csv/`: Tablas de datos agricolas (SIAP), censos (INEGI) y registros de biodiversidad (GBIF).
* **Alimentacion y Precision del Sistema (RAG)**: El motor vectorial ([tools/rag_engine.py](file:///home/m4r10/Documents/AgriPoli/enjambre_agentes/tools/rag_engine.py)) ingesta automaticamente los archivos de `regiones/<estado>/<municipio>/fuentes/` en sus colecciones semanticas, incrementando la precision de futuras consultas sin requerir re-descargas.
* **Compatibilidad Conservada**: Se mantiene la logica base previa escribiendo en paralelo a `data/reportes/` e indexando en el catalogo maestro `data/referencias.json`.

---

## 6. [MAPA] [ESTRUCTURA: CODIGO] Mapa del Repositorio

```
AgriPoli/enjambre_agentes/
├── agents/
│   ├── groups/                     # [NUEVO V3] Sub-grafos jerarquicos independientes
│   │   ├── group_extractor.py      # Sub-grafo Grupo Extractor (mini-agentes + join + descargador)
│   │   ├── group_agronomo.py       # Sub-grafo Grupo Agronomo (mini-agentes + loop edafoclimatico)
│   │   ├── group_ecologico.py      # Sub-grafo Grupo Ecologico (mini-agentes + loop simbiotico)
│   │   └── group_3d.py             # Sub-grafo Grupo 3D (fusionador + estructurador + validador)
│   ├── graph_v3.py                 # [NUEVO V3] Grafo Maestro con nodo_sintetizador y loops inter-grupo
│   ├── supervisor_v2.py            # [NUEVO V3] Supervisor Maestro con 6 herramientas de delegacion
│   ├── state_v3.py                 # [NUEVO V3] TypedDicts por grupo y estado maestro (resumen_ejecutivo, dossier)
│   ├── agro_experto.py             # [V1 Preservado] Agente ReAct agricola
│   ├── ecologico.py                # [V1 Preservado] Agente ReAct ecologico
│   ├── estructurador.py            # [V1 Preservado] Agente estructurador Pydantic Mapa3D
│   ├── extractor.py                # [V1 Preservado] Agente extractor
│   ├── graph_v2.py                 # [V2 Preservado] Grafo plano con streaming
│   ├── supervisor.py               # [V1 Preservado] Supervisor original
│   └── state.py / state_v2.py      # [V1/V2 Preservados] Estados legacy
├── config/
│   ├── agentes.yaml                # [NUEVO V3] Hot-reload granular (Gemini, Groq, Cohere, Ollama)
│   ├── agri_logger.py              # Logger formal con kaomojis ASCII y etiquetas
│   ├── silenciador.py              # Supresor centralizado de warnings de librerias
│   ├── models.py                   # Fabrica LLM multi-proveedor con introspeccion y fallbacks cruzados
│   ├── models_gemini.py            # Descubrimiento de modelos Gemini en vivo
│   ├── models_groq.py              # Descubrimiento de modelos Groq en vivo
│   ├── models_cohere.py            # Descubrimiento de modelos Cohere Command en vivo
│   └── keys.py                     # Carga de variables de entorno y API keys
├── data/
│   ├── descargas_masivas/          # Catalogo local de biodiversidad (3,922+ especies)
│   ├── knowledge/                  # Carpetas para indexacion RAG (suelo, agricultura, polinizadores, general)
│   │   └── descargas/              # Descarga local paralela de fuentes PDF y web por region
│   ├── reportes/                   # Dossiers tecnicos de diagnostico en markdown
│   └── referencias.json            # Metadatos estructurados y fuentes de trazabilidad
├── docs/
│   ├── ESTADO_PROYECTO.md          # Documento de referencia integral y estado del arte
│   ├── arquitectura_v3.png         # Diagrama estatico del Grafo Maestro V3 con Sintetizador
│   ├── arquitectura_agentes.png    # Diagrama estatico de la arquitectura global de agentes
│   ├── grupo_extractor.png         # Diagrama estatico del Grupo Extractor
│   ├── grupo_agronomo.png          # Diagrama estatico del Grupo Agronomo
│   ├── grupo_ecologico.png         # Diagrama estatico del Grupo Ecologico
│   ├── grupo_3d.png                # Diagrama estatico del Grupo 3D
│   └── grupo_supervisor.png        # Diagrama estatico del Supervisor Maestro
├── schemas/
│   └── threejs_schema.py           # Esquema Pydantic estricto para Three.js Mapa3D
├── scripts/
│   ├── main_supervisor_v2.py       # CLI interactivo conversacional V3 con presentacion ejecutiva y guardado local
│   ├── generar_diagrama_v3.py      # Generador de los 7 diagramas estaticos PNG
│   ├── generar_diagrama.py         # Generador de diagrama legacy V1/V2
│   ├── consulta_agricola.py        # Script de prueba directa
│   └── descargar_catalogo.py       # Descargador masivo oficial CONABIO/SIAP
└── tools/
    ├── catalogo_biodiversidad.py   # Consulta al catalogo de 3,922+ especies locales
    ├── gbif_client.py              # Cliente asincrono API GBIF
    ├── herramientas_cientificas.py # SymPy, arXiv, Semantic Scholar, Wikipedia MX
    ├── inegi_client.py             # Cliente API oficial INEGI BISE
    ├── rag_engine.py               # Motor FAISS/Chroma multi-coleccion
    ├── scraper.py                  # Playwright y lector PDF
    └── search.py                   # Tavily, CONABIO, EncicloVida, SADER, UNAM
```

---

## 7. (^_^) [CLI: COMANDOS] Guia de Uso del CLI V3

Punto de entrada principal:
```bash
uv run python scripts/main_supervisor_v2.py
```

### Comandos Slash Disponibles
* `/help`: Muestra el manual de ayuda completo y las rutas RAG.
* `/config`: Muestra el estado de API keys y el proveedor global activo.
* `/config-agentes`: Imprime la tabla completa de modelos configurados en `config/agentes.yaml`.
* `/agente <nombre_agente> <modelo>`: Cambia el modelo de un agente especifico (hot-reload en caliente).
* `/agente-provider <nombre_agente> <proveedor>`: Cambia el proveedor de un agente (Gemini, Groq, Cohere, Ollama).
* `/run <region>`: Ejecuta el flujo integral del Enjambre V3 (Extractor -> Agronomo -> Ecologico -> Supervisor -> Sintetizador). Despliega el **Resumen Ejecutivo de 8 secciones** en la terminal y lanza el prompt interactivo Human-in-the-Loop `[S/n]` para conservar el informe tecnico en `data/reportes/` y descargar las fuentes a disco.
* `/run3d <region>`: Ejecuta el flujo integral V3, genera el resumen ejecutivo y compila el modelo 3D Three.js.
* `/biodiversidad <especie>`: Consulta directa al catalogo de 3,922+ especies locales.
* `/rag status` / `/rag rebuild`: Inspecciona o reconstruye las 4 colecciones vectoriales locales.
* `/diagrama`: Regenera los 7 diagramas PNG de arquitectura en `docs/`.
* `/clear`: Reinicia la sesion de conversacion.
* `/exit`: Sale de la terminal interactiva.

---

## 8. [V3] [DIAGRAMAS: SISTEMA] Diagramas de Arquitectura Guardados

Los diagramas estaticos actualizados se encuentran renderizados en la carpeta `docs/`:

1. **Arquitectura Maestra V3 con Sintetizador**: `docs/arquitectura_v3.png`
2. **Arquitectura Global de Agentes**: `docs/arquitectura_agentes.png`
3. **Grupo Extractor**: `docs/grupo_extractor.png`
4. **Grupo Agronomo con Loop**: `docs/grupo_agronomo.png`
5. **Grupo Ecologico con Loop**: `docs/grupo_ecologico.png`
6. **Grupo Generador 3D**: `docs/grupo_3d.png`
7. **Supervisor Maestro V2**: `docs/grupo_supervisor.png`
