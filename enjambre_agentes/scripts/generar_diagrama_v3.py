"""
Generador de Diagramas de Arquitectura V3 — AgriPoli.

Genera las imagenes PNG estaticas del enjambre jerarquico con el flujo actual:
  docs/arquitectura_v3.png     — Diagrama completo del enjambre (4 grupos, mini-agentes, loops, RAG y Three.js)
  docs/arquitectura_agentes.png — Alias del diagrama completo
  docs/grupo_extractor.png     — Sub-grafo del Grupo Extractor
  docs/grupo_agronomo.png      — Sub-grafo del Grupo Agronomo (con loop de retroalimentacion)
  docs/grupo_ecologico.png     — Sub-grafo del Grupo Ecologico (con loop de retroalimentacion)
  docs/grupo_3d.png            — Sub-grafo del Grupo 3D (con loop de validacion Pydantic)

Uso:
  uv run python scripts/generar_diagrama_v3.py
"""
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config.silenciador
from config.agri_logger import log_info, log_ok, log_error

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))

DIAGRAMA_MERMAID_MAESTRO = """
flowchart TD
    %% 1. USUARIO Y CONTROL
    subgraph Control ["1. CONTROL Y USUARIO (Human-in-the-Loop)"]
        direction TB
        Usuario["(^-^) Usuario [Human-in-the-Loop]<br/>Peticiones | Confirmaciones | Decision 3D"]
        Supervisor{{"[O_O] Supervisor Maestro V2 [Orquestador ReAct]<br/>Enrutador de Consultas y Despachador de Tareas"}}
        Usuario <-->|Dialogo y Confirmaciones| Supervisor
    end

    %% 2. ALMACENES LOCALES Y RAG
    subgraph Datos ["2. ALMACENES LOCALES Y RAG"]
        direction LR
        CatalogoBio[("Catalogo Biodiversidad Mexicana<br/>(1,188 Flora + 2,734 Polinizadores)")]
        RAGDB[("Base Vectorial RAG FAISS/Chroma<br/>(Suelo, Agricultura, Polinizadores, General)")]
        RefDB[("referencias.json<br/>(Trazabilidad de descargas)")]
    end

    Supervisor <-->|Consultas directas| CatalogoBio
    Supervisor <-->|Consultas semanticas| RAGDB

    %% 3. GRUPO EXTRACTOR
    subgraph Grupo1 ["3. GRUPO 1: EXTRACTOR (Alimentacion Externa del Sistema)"]
        direction TB
        subgraph MiniExtractores ["Mini-Agentes de Investigacion Web y Documental"]
            direction LR
            Tavily["(O_O) mini_tavily<br/>Tavily / CONABIO / EncicloVida"]
            Acad["(^_~) mini_academico<br/>arXiv / Semantic Scholar / UNAM"]
            Scraper["[~_~] mini_scraper<br/>Playwright / PDFs / Selenium"]
            RefsExtr["(^_~) mini_referencias_extractor<br/>Fuentes oficiales, NOMs y Tavily"]
        end
        FusExtr["(^-^)/ fusionador_extractor<br/>Join, Deduplicacion y Sintesis"]
        Descargador{{"(o.O)? descargador [Human-in-the-Loop]<br/>Pregunta autorizacion al usuario si faltan datos locales"}}

        Tavily --> FusExtr
        Acad --> FusExtr
        Scraper --> FusExtr
        RefsExtr --> FusExtr
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
            Refs["(^_~) mini_referencias<br/>Trazabilidad, antecedentes y Tavily"]
        end
        FusAgro{{"[x_x] fusionador_agronomo<br/>Arbitro y Auditor Edafoclimatico"}}

        Suelo --> FusAgro
        Cultivo --> FusAgro
        SIAP --> FusAgro
        INEGI --> FusAgro
        Calc --> FusAgro
        Rotacion --> FusAgro
        Refs --> FusAgro

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
            RefsEco["(^_~) mini_referencias_ecologico<br/>Fuentes CONABIO, NOM-059 y citas"]
        end
        FusEco{{"[x_x] fusionador_ecologico<br/>Arbitro y Auditor Ecologico"}}

        Flora --> FusEco
        Poli --> FusEco
        CatLocal --> FusEco
        GBIF --> FusEco
        ControlBio --> FusEco
        Atractores --> FusEco
        RefsEco --> FusEco

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

    %% 7. SINTESIS Y RESUMEN EJECUTIVO
    subgraph Sintesis ["6. SINTESIS Y RESUMEN EJECUTIVO"]
        direction TB
        Sintetizador["(^-^) agente_sintetizador<br/>Diagnostico Integral (8 secciones: Flora, Suelo, Clima, Polinizadores, Rotacion, Fuentes)"]
        DossierLocal[("data/reportes/diagnostico.md<br/>data/referencias.json<br/>(Conservacion Local Human-in-the-Loop)")]
        Sintetizador -.->|"[Confirmacion Usuario]"| DossierLocal
    end

    %% 8. GRUPO 3D
    subgraph Grupo4 ["7. GRUPO 4: GENERADOR 3D (Procedural Three.js)"]
        direction TB
        Fus3D["(^o^) fusionador_3d<br/>Consolida coordenadas (x,y,z) y paleta hex"]
        Refs3D["(^_~) mini_referencias_3d<br/>Estandares espaciales y Three.js"]
        Estr["(^o^) estructurador<br/>Pydantic Mapa3D (Structured Output)"]
        Val3D{{"[x_x] validador_3d<br/>Auditor de Esquema Pydantic"}}

        Fus3D --> Estr
        Refs3D --> Estr
        Estr --> Val3D
        Val3D -.->|"[LOOP: INVALIDO]<br/>Reintento estructuracion (Max 2 ciclos)"| Estr
    end

    SalidaFinal([\"(^_^) [SALIDA FINAL]<br/>Resumen Ejecutivo en Pantalla + Dossier Local + JSON 3D\"])

    %% Conexiones principales de flujo
    Supervisor -->|1. Inicia recoleccion externa| Grupo1
    Descargador -->|Contexto web y oficial consolidado| Grupo2
    FusAgro -->|Propuestas agricolas aprobadas| Grupo3
    FusEco -->|Plan ecologico aprobado| SupervisorValidador

    %% Loops inter-grupo
    SupervisorValidador -.->|"[LOOP INTER-GRUPO: Falta contexto]"| Grupo1
    SupervisorValidador -.->|"[LOOP INTER-GRUPO: Colision agro/eco]"| Grupo2

    %% Validacion, Sintesis y ramificaciones 3D
    SupervisorValidador -->|APROBADO: Consolidar diagnostico| Sintetizador
    Sintetizador -->|Activar 3D bajo confirmacion| Grupo4
    Sintetizador -->|Finalizar sin 3D| SalidaFinal
    Val3D -->|VALIDO: Exporta mapa3d.json| SalidaFinal
"""


DIAGRAMA_MERMAID_EXTRACTOR = """
flowchart TD
    classDef entrada fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0f172a,font-weight:bold
    classDef agente fill:#ecfdf5,stroke:#059669,stroke-width:2px,color:#064e3b
    classDef arbitro fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f,font-weight:bold
    classDef hil fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#7f1d1d,font-weight:bold
    classDef stub fill:#f8fafc,stroke:#94a3b8,stroke-width:1px,stroke-dasharray: 5 5,color:#64748b
    classDef salida fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#14532d,font-weight:bold

    Entrada[("[O_O] Solicitud de Investigacion Externa<br/>(Supervisor Maestro V2)")]:::entrada

    subgraph MiniExtr ["Mini-Agentes de Investigacion Web y Documental"]
        direction TB
        Tavily["(O_O) mini_tavily<br/>Tavily Search / CONABIO / EncicloVida"]:::agente
        Acad["(^_~) mini_academico<br/>arXiv / Semantic Scholar / UNAM"]:::agente
        Scraper["[~_~] mini_scraper<br/>Playwright Scraper / Documentos PDF"]:::agente
        RefsExtr["(^_~) mini_referencias_extractor<br/>Fuentes oficiales, NOMs y enlaces Tavily"]:::agente
    end

    FusExtr["(^-^)/ fusionador_extractor<br/>Join, Deduplicacion y Sintesis"]:::arbitro
    Descargador{{"(o.O)? descargador [Human-in-the-Loop]<br/>Pide autorizacion al usuario si faltan datos locales"}}:::hil
    Salida[("[V_V] Contexto Consolidado y Descargas<br/>(Enviado a Grupo Agronomo y RAG/FAISS)")]:::salida

    Entrada --> Tavily
    Entrada --> Acad
    Entrada --> Scraper
    Entrada --> RefsExtr

    Tavily --> FusExtr
    Acad --> FusExtr
    Scraper --> FusExtr
    RefsExtr --> FusExtr
    FusExtr --> Descargador
    Descargador --> Salida

    subgraph StubsExtr ["Futuros Mini-Agentes Extractor"]
        direction LR
        StubNASA["mini_nasa_power<br/>Datos agroclimaticos NASA"]:::stub
        StubSoil["mini_soilgrids<br/>Propiedades de suelo globales"]:::stub
        StubINat["mini_inaturalist<br/>Observaciones ciudadanas"]:::stub
        StubSent["mini_sentinel<br/>Imagenes satelitales NDVI"]:::stub
    end
"""

DIAGRAMA_MERMAID_AGRONOMO = """
flowchart TD
    classDef entrada fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0f172a,font-weight:bold
    classDef agente fill:#ecfdf5,stroke:#059669,stroke-width:2px,color:#064e3b
    classDef arbitro fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f,font-weight:bold
    classDef stub fill:#f8fafc,stroke:#94a3b8,stroke-width:1px,stroke-dasharray: 5 5,color:#64748b
    classDef salida fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#14532d,font-weight:bold

    Entrada[("[O_O] Contexto Edafoclimatico<br/>(Datos de Suelo, Region y Clima)")]:::entrada

    subgraph MiniAgros ["Mini-Agentes Agronomicos Especializados"]
        direction TB
        Suelo["[O_O] mini_suelo<br/>Edafologia, pH, texturas y NPK"]:::agente
        Cultivo["(-w-)/ mini_cultivo<br/>Especies viables y calendarios de siembra"]:::agente
        SIAP["[._.] mini_siap<br/>Estadisticas oficiales SADER y SIAP"]:::agente
        INEGI["(O_O) mini_inegi_agro<br/>Indicadores agropecuarios y censo INEGI"]:::agente
        Calc["(˘ワ˘) mini_calculadora<br/>Balance hidrico y formulas de rendimiento"]:::agente
        Rotacion["(u_u) mini_rotacion_regenerativa<br/>Secuencias funcionales monocultivo (N/D/P/H)"]:::agente
        Refs["(^_~) mini_referencias<br/>Trazabilidad, antecedentes y Tavily"]:::agente
    end

    FusAgro{{"[x_x] fusionador_agronomo<br/>Arbitro y Auditor Edafoclimatico"}}:::arbitro
    Salida[("[V_V] Propuestas Agricolas Aprobadas<br/>(Enviadas a Grupo Ecologico)")]:::salida

    Entrada --> Suelo
    Entrada --> Cultivo
    Entrada --> SIAP
    Entrada --> INEGI
    Entrada --> Calc
    Entrada --> Rotacion
    Entrada --> Refs

    Suelo --> FusAgro
    Cultivo --> FusAgro
    SIAP --> FusAgro
    INEGI --> FusAgro
    Calc --> FusAgro
    Rotacion --> FusAgro
    Refs --> FusAgro

    FusAgro -.->|"[LOOP: RECHAZADO]<br/>Inconsistencia edafoclimatica (Max 3 ciclos)"| Cultivo
    FusAgro -.->|"[LOOP: RECHAZADO]<br/>Ajuste rotacion regenerativa"| Rotacion
    FusAgro -->|"[APROBADO]"| Salida

    subgraph StubsAgro ["Futuros Mini-Agentes Agronomo"]
        direction LR
        StubRF["mini_random_forest<br/>Prediccion rendimiento ML"]:::stub
        StubMercado["mini_mercado_agricola<br/>Precios SNIIM y oferta"]:::stub
        StubAgua["mini_agua<br/>Concesiones CONAGUA"]:::stub
        StubFito["mini_fitosanidad<br/>Monitoreo SENASICA"]:::stub
    end
"""

DIAGRAMA_MERMAID_ECOLOGICO = """
flowchart TD
    classDef entrada fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0f172a,font-weight:bold
    classDef agente fill:#ecfdf5,stroke:#059669,stroke-width:2px,color:#064e3b
    classDef arbitro fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f,font-weight:bold
    classDef stub fill:#f8fafc,stroke:#94a3b8,stroke-width:1px,stroke-dasharray: 5 5,color:#64748b
    classDef salida fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#14532d,font-weight:bold

    Entrada[("[O_O] Propuestas Agricolas Validadas<br/>(Cultivos seleccionados y region)")]:::entrada

    subgraph MiniEcos ["Mini-Agentes Ecologicos Especializados"]
        direction TB
        Flora["(*-*) mini_flora_nativa<br/>Flora nativa segun clasificacion Koppen"]:::agente
        Poli["(^w^) mini_polinizadores<br/>Catalogo de abejas nativas y lepidopteros"]:::agente
        CatLocal["(._.)/ mini_catalogo_local<br/>Registros locales CONABIO y NOM-059"]:::agente
        GBIF["[~_~] mini_gbif<br/>Taxonomia y ocurrencias globales GBIF"]:::agente
        ControlBio["(>o<) mini_control_biologico<br/>Depredadores naturales (catarinas, pulgones)"]:::agente
        Atractores["(^-^)~ mini_atractores_polinizadores<br/>Calendario floral y habitat polinizador"]:::agente
        RefsEco["(^_~) mini_referencias_ecologico<br/>Fuentes CONABIO, NOM-059 y catalogos"]:::agente
    end

    FusEco{{"[x_x] fusionador_ecologico<br/>Arbitro y Auditor Ecologico"}}:::arbitro
    Salida[("[V_V] Plan Ecologico Aprobado<br/>(Enviado a Supervisor Validador)")]:::salida

    Entrada --> Flora
    Entrada --> Poli
    Entrada --> CatLocal
    Entrada --> GBIF
    Entrada --> ControlBio
    Entrada --> Atractores
    Entrada --> RefsEco

    Flora --> FusEco
    Poli --> FusEco
    CatLocal --> FusEco
    GBIF --> FusEco
    ControlBio --> FusEco
    Atractores --> FusEco
    RefsEco --> FusEco

    FusEco -.->|"[LOOP: RECHAZADO]<br/>Incompatibilidad agro/eco (Max 3 ciclos)"| Flora
    FusEco -.->|"[LOOP: RECHAZADO]<br/>Ajuste control biologico y polinizadores"| ControlBio
    FusEco -->|"[APROBADO]"| Salida

    subgraph StubsEco ["Futuros Mini-Agentes Ecologico"]
        direction LR
        StubNOM["mini_nom059<br/>Categorias de riesgo SEMARNAT"]:::stub
        StubKoppen["mini_koppen<br/>Microclimas y fitogeografia"]:::stub
        StubCorredor["mini_corredor_biologico<br/>Conectividad de parches nativos"]:::stub
    end
"""

DIAGRAMA_MERMAID_3D = """
flowchart TD
    classDef entrada fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0f172a,font-weight:bold
    classDef agente fill:#ecfdf5,stroke:#059669,stroke-width:2px,color:#064e3b
    classDef arbitro fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f,font-weight:bold
    classDef salida fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#14532d,font-weight:bold

    Entrada[("[x_x] Supervisor Validador<br/>Plan Agroecologico Completo Aprobado")]:::entrada

    subgraph Pipeline3D ["Pipeline de Modelado Procedural Three.js"]
        direction TB
        Fus3D["(^o^) fusionador_3d<br/>Consolida coordenadas espaciales (x,y,z) y paleta hex"]:::agente
        Refs3D["(^_~) mini_referencias_3d<br/>Guias de espaciamiento y estandares Three.js"]:::agente
        Estr["(^o^) estructurador<br/>Pydantic Mapa3D (Structured Output)"]:::agente
        Val3D{{"[x_x] validador_3d<br/>Auditor de Esquema Pydantic y Colisiones"}}:::arbitro
    end

    Salida([\"(^_^) Archivo mapa3d.json<br/>Visualizacion 3D Procedural en Three.js\"]):::salida

    Entrada --> Fus3D
    Entrada --> Refs3D
    Fus3D --> Estr
    Refs3D --> Estr
    Estr --> Val3D
    Val3D -.->|"[LOOP: INVALIDO]<br/>Reintento estructuracion (Max 2 ciclos)"| Estr
    Val3D -->|"[VALIDO: Exporta JSON]"| Salida
"""

DIAGRAMA_MERMAID_SUPERVISOR = """
flowchart TD
    classDef usuario fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#0f172a,font-weight:bold
    classDef supervisor fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#0f172a,font-weight:bold
    classDef subgrafo fill:#ecfdf5,stroke:#10b981,stroke-width:2px,color:#064e3b
    classDef storage fill:#f1f5f9,stroke:#64748b,stroke-width:2px,color:#0f172a
    classDef salida fill:#f0fdf4,stroke:#16a34a,stroke-width:2px,color:#14532d,font-weight:bold

    Usuario["(^-^) Usuario [Human-in-the-Loop]<br/>Peticiones | Confirmaciones | Decision 3D"]:::usuario
    Supervisor{{"[O_O] Supervisor Maestro V2<br/>Orquestador ReAct y Enrutador de Intenciones"}}:::supervisor

    Usuario <-->|Interaccion en Lenguaje Natural| Supervisor

    Catalogo[("Catalogo Biodiversidad Mexicana<br/>(1,188 Flora + 2,734 Polinizadores)")]:::storage
    RAG[("Base Vectorial RAG FAISS/Chroma<br/>(Suelo, Agricultura, Polinizadores)")]:::storage

    Supervisor <-->|Consultas Locales Directas| Catalogo
    Supervisor <-->|Consultas Semanticas| RAG

    GrupoExtr["Grupo 1: Extractor<br/>Investigacion Externa y Web"]:::subgrafo
    GrupoAgro["Grupo 2: Agronomo<br/>Suelo, Cultivos y Rotacion Regenerativa"]:::subgrafo
    GrupoEco["Grupo 3: Ecologico<br/>Flora Nativa, Polinizadores y Control Biologico"]:::subgrafo
    Grupo3D["Grupo 4: Three.js 3D<br/>Estructuracion Procedural Pydantic"]:::subgrafo

    SupervisorValidador{{"[x_x] Supervisor Validador<br/>Auditor de Coherencia Global Inter-Grupo"}}:::supervisor
    Sintetizador["(^-^) Agente Sintetizador<br/>Resumen Ejecutivo y Dossier Tecnico"]:::subgrafo
    Salida([\"(^_^) [SALIDA FINAL]<br/>Resumen Ejecutivo en Pantalla + Dossier Local + JSON 3D\"]):::salida

    Supervisor -->|1. Requiere contexto web| GrupoExtr
    Supervisor -->|2. Diagnostico agricola| GrupoAgro
    GrupoAgro -->|3. Complemento ecologico| GrupoEco
    GrupoEco -->|4. Validacion cruzada| SupervisorValidador
    SupervisorValidador -->|5. Plan integral aprobado| Sintetizador
    SupervisorValidador -.->|"[LOOP: Falta contexto]"| GrupoExtr
    SupervisorValidador -.->|"[LOOP: Colision agro/eco]"| GrupoAgro
    Sintetizador -->|6. Activacion 3D opcional| Grupo3D
    Sintetizador -->|Finalizar sin 3D| Salida
    Grupo3D -->|APROBADO con 3D| Salida
"""


def _guardar_diagrama_langgraph(grafo, nombre_archivo: str, etiqueta: str) -> str | None:
    """Exporta el grafo LangGraph a PNG mediante draw_mermaid_png() como respaldo."""
    ruta = os.path.join(DOCS_DIR, nombre_archivo)
    os.makedirs(DOCS_DIR, exist_ok=True)
    try:
        png_bytes = grafo.get_graph(xray=True).draw_mermaid_png()
        with open(ruta, "wb") as f:
            f.write(png_bytes)
        log_ok(f"{etiqueta} -> {ruta} ({len(png_bytes):,} bytes)", kaomoji="(^_^)/")
        return ruta
    except Exception as e:
        log_error(f"No se pudo generar PNG para '{etiqueta}': {e}", kaomoji="[X_X]")
        return None


def generar_diagramas_v3() -> list[str]:
    """Genera y guarda los diagramas de arquitectura V3 actualizados para cada subgrafo y el enjambre."""
    log_info("Generando diagramas de arquitectura con el flujo actual...", kaomoji="(o_o)")
    rutas = []

    # Lista de tuplas: (codigo_mermaid, nombre_archivo, etiqueta)
    items_diagramas = [
        (DIAGRAMA_MERMAID_MAESTRO, "arquitectura_v3.png", "Diagrama Maestro V3"),
        (DIAGRAMA_MERMAID_MAESTRO, "arquitectura_agentes.png", "Arquitectura Agentes"),
        (DIAGRAMA_MERMAID_EXTRACTOR, "grupo_extractor.png", "Grupo Extractor"),
        (DIAGRAMA_MERMAID_AGRONOMO, "grupo_agronomo.png", "Grupo Agronomo"),
        (DIAGRAMA_MERMAID_ECOLOGICO, "grupo_ecologico.png", "Grupo Ecologico"),
        (DIAGRAMA_MERMAID_3D, "grupo_3d.png", "Grupo 3D"),
        (DIAGRAMA_MERMAID_SUPERVISOR, "grupo_supervisor.png", "Grupo Supervisor"),
    ]

    # Renderizado en lote de alta resolucion con Playwright
    try:
        from scripts.render_playwright import render_multiple_mermaids_with_playwright
        items_playwright = [
            (codigo, os.path.join(DOCS_DIR, nombre), etiqueta)
            for codigo, nombre, etiqueta in items_diagramas
        ]
        rutas_generadas = render_multiple_mermaids_with_playwright(items_playwright)
        rutas.extend(rutas_generadas)
    except Exception as e_pw:
        log_error(f"Error en renderizado con Playwright: {e_pw}. Intentando respaldo LangGraph...", kaomoji="(-_-;)")
        # Fallback usando LangGraph draw_mermaid_png para los subgrafos
        try:
            from agents.groups.group_extractor import crear_grafo_extractor
            r = _guardar_diagrama_langgraph(crear_grafo_extractor(), "grupo_extractor.png", "Grupo Extractor")
            if r: rutas.append(r)
        except Exception: pass
        try:
            from agents.groups.group_agronomo import crear_grafo_agronomo
            r = _guardar_diagrama_langgraph(crear_grafo_agronomo(), "grupo_agronomo.png", "Grupo Agronomo")
            if r: rutas.append(r)
        except Exception: pass
        try:
            from agents.groups.group_ecologico import crear_grafo_ecologico
            r = _guardar_diagrama_langgraph(crear_grafo_ecologico(), "grupo_ecologico.png", "Grupo Ecologico")
            if r: rutas.append(r)
        except Exception: pass
        try:
            from agents.groups.group_3d import crear_grafo_3d
            r = _guardar_diagrama_langgraph(crear_grafo_3d(), "grupo_3d.png", "Grupo 3D")
            if r: rutas.append(r)
        except Exception: pass

    # Sincronizar automaticamente con el directorio de artefactos del IDE si esta disponible
    _sincronizar_con_artefactos(rutas)

    log_ok(f"Diagramas generados exitosamente en: {DOCS_DIR}/", kaomoji="\\(^o^)/")
    return rutas


def _sincronizar_con_artefactos(rutas: list[str]):
    """Copia los diagramas generados a los directorios de artefactos del IDE."""
    import shutil
    import glob

    # Directorio activo de artefactos de Antigravity IDE
    rutas_destino = glob.glob("/home/m4r10/.gemini/antigravity-ide/brain/*")
    for d in rutas_destino:
        if os.path.isdir(d) and not os.path.basename(d).startswith("."):
            for r in rutas:
                if os.path.exists(r):
                    try:
                        shutil.copy2(r, os.path.join(d, os.path.basename(r)))
                    except Exception:
                        pass


import threading
_lock_generacion = threading.Lock()


def disparar_actualizacion_diagramas(async_mode: bool = True):
    """Dispara la regeneracion y guardado automatico de todas las arquitecturas en PNG.
    
    Args:
        async_mode: Si True, se ejecuta en un hilo daemon en segundo plano para no bloquear.
    """
    def _tarea():
        if _lock_generacion.acquire(blocking=False):
            try:
                log_info("Actualizando arquitecturas de subgrafos y enjambre en segundo plano...", kaomoji="[._.]")
                generar_diagramas_v3()
                log_ok("Arquitecturas de subgrafos y enjambre guardadas exitosamente en docs/ y artefactos.", kaomoji="(^o^)/")
            finally:
                _lock_generacion.release()

    if async_mode:
        t = threading.Thread(target=_tarea, name="DiagramRegeneratorThread", daemon=True)
        t.start()
        return t
    else:
        _tarea()
        return None


if __name__ == "__main__":
    rutas = generar_diagramas_v3()
    if not rutas:
        sys.exit(1)
