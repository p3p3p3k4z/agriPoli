"""
Grupo Extractor — Sub-grafo LangGraph del Sistema Multiagente AgriPoli V3.

Responsabilidad: Recopilar informacion fresca de fuentes externas.
Mini-agentes paralelos:
  * mini_tavily    — Busqueda Tavily + CONABIO + EncicloVida
  * mini_academico — Papers arXiv + Semantic Scholar + Wikipedia
  * mini_scraper   — Playwright + PDF gubernamentales + Selenium
  * descargador    — Gestor de descargas masivas (con confirmacion del usuario)
Fusionador interno:
  * fusionador_extractor — Consolida y deduplica los resultados (join)
"""
from __future__ import annotations

import re
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

import config.silenciador
from config.models import get_llm_para_agente, cargar_config_agentes
from config.agri_logger import log_agente, log_mini_agente, log_flujo, log_ok, log_info, log_error
from agents.state_v3 import EstadoGrupoExtractor


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 1: Tavily / CONABIO / EncicloVida
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_tavily(state: EstadoGrupoExtractor) -> dict:
    """Fork A: Busqueda rapida con Tavily, CONABIO y EncicloVida."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_tavily")
    log_mini_agente("MINI_TAVILY", f"Buscando biodiversidad y clima en '{region}'...", kaomoji="(O_O)")

    from tools.search import buscar_tavily_mexico, buscar_conabio, explorador_enciclovida
    agente = create_react_agent(
        model=llm,
        tools=[buscar_tavily_mexico, buscar_conabio, explorador_enciclovida],
        prompt=(
            "Eres el Mini-Agente Tavily/CONABIO del Grupo Extractor de AgriPoli. "
            "Busca informacion actualizada sobre biodiversidad, clima y cultivos de la region. "
            "Incluye siempre las URLs de tus fuentes."
        ),
    )
    consulta = f"clima, biodiversidad, polinizadores y cultivos en {region} Mexico"
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_tavily] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_TAVILY", "Busqueda Tavily/CONABIO completada.", kaomoji="(o_o)")
    return {"resultado_tavily": texto, "fuentes_web": [region]}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 2: Papers Academicos
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_academico(state: EstadoGrupoExtractor) -> dict:
    """Fork B: Papers arXiv + Semantic Scholar + Wikipedia."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_academico")
    log_mini_agente("MINI_ACADEMICO", f"Indagando literatura cientifica para '{region}'...", kaomoji="(^_~)")

    from tools.herramientas_cientificas import (
        buscar_arxiv_agricola, buscar_semantic_scholar_agricola,
        formateador_citas_agricola, buscar_wikipedia_mx,
    )
    agente = create_react_agent(
        model=llm,
        tools=[buscar_arxiv_agricola, buscar_semantic_scholar_agricola,
               formateador_citas_agricola, buscar_wikipedia_mx],
        prompt=(
            "Eres el Mini-Agente Academico del Grupo Extractor de AgriPoli. "
            "Busca papers cientificos sobre agricultura regenerativa, polinizadores "
            "y ecologia de suelos. Incluye DOIs y formatea citas con formateador_citas_agricola."
        ),
    )
    consulta = f"agricultura regenerativa polinizadores suelos {region} Mexico"
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_academico] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_ACADEMICO", "Literatura cientifica recopilada.", kaomoji="(o_o)")
    return {"resultado_academico": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 3: Scraper Profundo
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_scraper(state: EstadoGrupoExtractor) -> dict:
    """Fork C: Scraping profundo de paginas gubernamentales y PDFs oficiales."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_scraper")
    log_mini_agente("MINI_SCRAPER", f"Extrayendo informacion gubernamental para '{region}'...", kaomoji="[~_~]")

    from tools.scraper import lector_web_playwright, lector_pdf_web
    from tools.herramientas_cientificas import lector_web_selenium
    from tools.search import buscar_tavily_mexico
    agente = create_react_agent(
        model=llm,
        tools=[buscar_tavily_mexico, lector_web_playwright, lector_pdf_web, lector_web_selenium],
        prompt=(
            "Eres el Mini-Agente Scraper del Grupo Extractor de AgriPoli. "
            "Usa Tavily para encontrar URLs de SADER, CONABIO, INIFAP y UNAM. "
            "Luego extrae el contenido completo con lector_web_playwright o lector_pdf_web. "
            "Prioriza documentos PDF oficiales de la region."
        ),
    )
    consulta = f"monografias cultivos flora nativa {region} SADER CONABIO PDF"
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_scraper] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_SCRAPER", "Extraccion web completada.", kaomoji="(o_o)")
    return {"resultado_scraper": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 4: Referencias y Fuentes Extractor (Tavily Formatter)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_referencias_extractor(state: EstadoGrupoExtractor) -> dict:
    """Fork/Paso: De la consulta original, extrae unicamente las fuentes y referencias
    (articulos cientificos, manuales gubernamentales, enlaces web de Tavily)
    y les da el formato estandarizado correspondiente.
    """
    region = state.get("region", "Mexico")
    consulta_orig = state.get("consulta_original", "") or f"clima, suelo y agricultura en {region} Mexico"
    llm = get_llm_para_agente("mini_referencias_extractor")
    log_mini_agente("MINI_REFERENCIAS_EXTR", f"Extrayendo y formateando fuentes para '{region}'...", kaomoji="(^_~)")

    from tools.search import buscar_tavily_mexico

    agente = create_react_agent(
        model=llm,
        tools=[buscar_tavily_mexico],
        prompt=(
            "Eres el Mini-Agente de Referencias del Grupo Extractor de AgriPoli. "
            "Tu UNICO objetivo es extraer de la consulta original las fuentes, autores, instituciones y enlaces web pertinentes. "
            "No inventes datos ni hagas recomendaciones de cultivo ni des explicaciones extensas. "
            "Solo identifica, extrae y formatea las fuentes tecnicas y oficiales: "
            "1. Cita instituciones oficiales mexicanas (SADER, CONABIO, INEGI, UNAM, SciELO, SMN). "
            "2. Extrae las URLs reales encontradas mediante la herramienta de busqueda Tavily. "
            "FORMATO ESTANDAR OBLIGATORIO: "
            "[FUENTES Y REFERENCIAS: GRUPO EXTRACTOR]\n"
            "1. [Institucion / Repositorio] Titulo o tematica consultada | Enlace: <URL>\n"
            "2. [Institucion / Repositorio] Titulo o tematica consultada | Enlace: <URL>"
        ),
    )
    consulta = f"fuentes oficiales, articulos y manuales tecnicos sobre: {consulta_orig} en {region} Mexico"
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_referencias_extractor] {e}"
        log_error(str(e), kaomoji="[X_X]")

    urls = re.findall(r'https?://[^\s)\]>"\']+', str(texto))
    log_mini_agente("MINI_REFERENCIAS_EXTR", f"Fuentes extraidas ({len(urls)} enlaces).", kaomoji="(^_~)")
    return {
        "resultado_mini_referencias": texto,
        "referencias_fuentes": urls,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUSIONADOR EXTRACTOR (Join de los mini-agentes)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_fusionador_extractor(state: EstadoGrupoExtractor) -> dict:
    """Join: Consolida y deduplica los resultados de los mini-agentes paralelos."""
    llm = get_llm_para_agente("fusionador_extractor")
    log_flujo(
        "[mini_tavily | mini_academico | mini_scraper | mini_referencias_extractor]",
        "fusionador_extractor",
        "Join: consolidando hallazgos y fuentes formateadas",
    )
    log_agente("FUSIONADOR_EXTRACTOR", "Sintetizando y deduplicando informacion...", kaomoji="(^-^)/")

    prompt = (
        "Eres el Fusionador del Grupo Extractor del Sistema AgriPoli.\n"
        "Consolida en un reporte estructurado los hallazgos de tus mini-agentes. "
        "Elimina duplicados y organiza por categorias: Clima/Suelo, Cultivos, Flora/Polinizadores, Fuentes.\n"
        "AL FINAL incluye el bloque estandarizado de fuentes:\n\n"
        f"--- MINI-AGENTE TAVILY ---\n{state.get('resultado_tavily', 'Sin datos')}\n\n"
        f"--- MINI-AGENTE ACADEMICO ---\n{state.get('resultado_academico', 'Sin datos')}\n\n"
        f"--- MINI-AGENTE SCRAPER ---\n{state.get('resultado_scraper', 'Sin datos')}\n\n"
        f"--- MINI-AGENTE REFERENCIAS ---\n{state.get('resultado_mini_referencias', 'Sin datos')}"
    )
    try:
        response = llm.invoke(prompt)
        texto = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as e:
        texto = f"Error en fusionador_extractor: {e}"
        log_error(str(e), kaomoji="[X_X]")

    fuentes = re.findall(r'https?://[^\s)\]]+', texto)
    log_ok(f"Contexto web fusionado con {len(fuentes)} fuentes citadas.", kaomoji="(^_^)/")
    return {"contexto_web": texto, "fuentes_web": fuentes, "referencias_fuentes": fuentes}


# ─────────────────────────────────────────────────────────────────────────────
# NODO DESCARGADOR (Condicional — pregunta al usuario)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_descargador(state: EstadoGrupoExtractor) -> dict:
    """Nodo condicional: si no hay contexto web suficiente, pregunta al usuario
    si desea descargar datos localmente antes de continuar.
    """
    contexto = state.get("contexto_web", "")
    config = cargar_config_agentes().get("configuracion", {})
    modo_descarga = config.get("confirmacion_descarga", "manual")

    if len(contexto.strip()) > 200:
        # Hay suficiente contexto web — no es necesario descargar
        return {"descarga_confirmada": False}

    log_agente(
        "DESCARGADOR",
        "(o.O)? [CONSULTA: DESCARGA] La informacion local no es suficiente para esta region.",
        kaomoji="(o.O)?",
    )

    if modo_descarga == "auto":
        log_info("Modo auto: descarga confirmada automaticamente.", kaomoji="(^_^)/")
        return {"descarga_confirmada": True}

    # Modo manual: mostrar pregunta al usuario
    print(
        "\n(o.O)? [CONSULTA: DESCARGA]\n"
        "  No hay suficientes datos locales para esta region.\n"
        "  Deseas descargar y guardar los datos en disco? [s/n]: ",
        end="", flush=True,
    )
    try:
        respuesta = input().strip().lower()
        confirmado = respuesta in ("s", "si", "yes", "y", "1")
    except (EOFError, KeyboardInterrupt):
        confirmado = False

    if confirmado:
        log_ok("Descarga confirmada por el usuario. Iniciando descarga masiva...", kaomoji="(^_^)/")
    else:
        log_info("Descarga rechazada por el usuario. Continuando con datos disponibles.", kaomoji="(o_o)")

    return {"descarga_confirmada": confirmado}


# ─────────────────────────────────────────────────────────────────────────────
# ROUTERS
# ─────────────────────────────────────────────────────────────────────────────

def router_flow_type(state: EstadoGrupoExtractor) -> str:
    flow = state.get("flow_type", "Hibrido")
    if flow == "Solo Local":
        log_flujo("START", "fusionador_extractor", f"Modo '{flow}': omitiendo mini-agentes web")
        return "Solo Local"
    log_flujo("START", "[mini_tavily|mini_academico|mini_scraper|mini_referencias]", f"Modo '{flow}': activando fork")
    return "Con Web"


def router_post_fusion(state: EstadoGrupoExtractor) -> str:
    contexto = state.get("contexto_web", "")
    if len(contexto.strip()) < 200:
        log_flujo("fusionador_extractor", "descargador", "Contexto insuficiente -> consultar descarga")
        return "Verificar Descarga"
    return "Listo"


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCCION DEL SUB-GRAFO
# ─────────────────────────────────────────────────────────────────────────────

def crear_grafo_extractor():
    """Compila y retorna el sub-grafo del Grupo Extractor."""
    workflow = StateGraph(EstadoGrupoExtractor)

    def nodo_inicio(state: EstadoGrupoExtractor) -> dict:
        flow = state.get("flow_type", "Hibrido")
        if flow == "Solo Local":
            log_flujo("START", "fusionador_extractor", f"Modo '{flow}': omitiendo mini-agentes web")
        else:
            log_flujo("START", "mini_tavily->mini_academico->mini_scraper->mini_referencias", f"Modo '{flow}': cadena web")
        return {}

    def router_inicio(state: EstadoGrupoExtractor) -> str:
        flow = state.get("flow_type", "Hibrido")
        return "Solo Local" if flow == "Solo Local" else "Con Web"

    workflow.add_node("inicio",                     nodo_inicio)
    workflow.add_node("mini_tavily",                nodo_mini_tavily)
    workflow.add_node("mini_academico",             nodo_mini_academico)
    workflow.add_node("mini_scraper",               nodo_mini_scraper)
    workflow.add_node("mini_referencias_extractor", nodo_mini_referencias_extractor)
    workflow.add_node("fusionador_extractor",       nodo_fusionador_extractor)
    workflow.add_node("descargador",                nodo_descargador)

    # Inicio -> ruteo por modo
    workflow.add_edge(START, "inicio")
    workflow.add_conditional_edges("inicio", router_inicio, {
        "Solo Local": "fusionador_extractor",
        "Con Web":    "mini_tavily",
    })

    # Cadena de mini-agentes (incluye mini_referencias_extractor antes del fusionador)
    workflow.add_edge("mini_tavily",                "mini_academico")
    workflow.add_edge("mini_academico",             "mini_scraper")
    workflow.add_edge("mini_scraper",               "mini_referencias_extractor")
    workflow.add_edge("mini_referencias_extractor", "fusionador_extractor")

    # Post-fusion: verificar si necesita descarga
    workflow.add_conditional_edges("fusionador_extractor", router_post_fusion, {
        "Verificar Descarga": "descargador",
        "Listo":              END,
    })
    workflow.add_edge("descargador", END)

    return workflow.compile()

    # Post-fusion: verificar si necesita descarga
    workflow.add_conditional_edges("fusionador_extractor", router_post_fusion, {
        "Verificar Descarga": "descargador",
        "Listo":              END,
    })
    workflow.add_edge("descargador", END)

    return workflow.compile()


# ─────────────────────────────────────────────────────────────────────────────
# Mini-agentes FUTUROS (stubs — descomentar para activar)
# ─────────────────────────────────────────────────────────────────────────────

# def nodo_mini_nasa_power(state):
#     """FUTURO: Consulta la API NASA POWER para datos climaticos reales por GPS."""
#     from agents.extractor import extraer_datos_clima_nasa
#     region = state.get("region", "Mexico")
#     resultado = extraer_datos_clima_nasa.invoke(region)
#     return {"resultado_tavily": state.get("resultado_tavily", "") + "\n[NASA POWER]\n" + resultado}

# def nodo_mini_soilgrids(state):
#     """FUTURO: Datos reales de textura, pH y carbono organico (ISRIC SoilGrids)."""
#     from agents.extractor import extraer_topografia_soilgrids
#     region = state.get("region", "Mexico")
#     resultado = extraer_topografia_soilgrids.invoke(region)
#     return {"resultado_scraper": state.get("resultado_scraper", "") + "\n[SoilGrids]\n" + resultado}

# def nodo_mini_inaturalist(state):
#     """FUTURO: Observaciones ciudadanas de iNaturalist/Naturalista Mexico."""
#     pass

# def nodo_mini_sentinel(state):
#     """FUTURO: Imagenes satelitales Sentinel-2 (NDVI, humedad de suelo)."""
#     pass
