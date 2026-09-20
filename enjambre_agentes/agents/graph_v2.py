"""
Grafo Principal V2 del Sistema Multiagente AgriPoli.

Implementa la arquitectura de Soporte de Decisiones (DSS) inspirada en OptiAgent:
  - Nodos paralelos de investigación (fork + join)
  - MemorySaver para historial persistente por thread_id
  - Modos de flujo: "Hibrido" | "Solo Local" | "Solo Web"
  - Streaming de eventos para la terminal
  - Ciclo de validación con Conditional Edges y deadlock prevention
"""
from __future__ import annotations

import json
from typing import Literal
from operator import add
from typing import Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage

import config.silenciador
from config.agri_logger import (
    log_agente, log_mini_agente, log_flujo, log_ok, log_info, log_error
)
from agents.state_v2 import EstadoEnjambreV2
from agents.extractor import crear_agente_extractor
from agents.agro_experto import crear_agro_experto
from agents.ecologico import crear_agente_ecologico
from agents.estructurador import invocar_estructurador
from config.models import get_llm

# ──────────────────────────────────────────────────────────────────────────────
# ESTADO EXTENDIDO (compatibilidad con flujos paralelos y modo de flujo)
# ──────────────────────────────────────────────────────────────────────────────

class EstadoGrafoV2(EstadoEnjambreV2, total=False):
    """Extensión del estado base con campos para OptiAgent patterns."""
    flow_type: str          # "Hibrido" | "Solo Local" | "Solo Web"
    provider: str           # Proveedor LLM activo
    # Resultados de los tres mini-agentes paralelos del Extractor
    resultado_tavily: str
    resultado_academico: str
    resultado_scraper: str
    # Contexto web fusionado por el Parseador
    contexto_web: str
    # Contexto local RAG
    contexto_local: str
    # Contexto final fusionado (RAG + Web)
    contexto_fusionado: str
    # Fuentes citadas (para el reporte)
    fuentes_web: Annotated[list[str], add]
    fuentes_locales: Annotated[list[str], add]
    # Reporte final en texto
    reporte_final: str


# ──────────────────────────────────────────────────────────────────────────────
# NODO: RAG Local (Mini-Agente A)
# ──────────────────────────────────────────────────────────────────────────────

def nodo_rag_local(state: EstadoGrafoV2) -> dict:
    """Consulta el RAG local (FAISS/Pinecone) con las colecciones temáticas."""
    provider = state.get("provider", "Gemini")
    region = state.get("region", "Mexico")
    log_agente("RAG_LOCAL", f"Consultando base de conocimientos para region '{region}' [{provider}]...", kaomoji="[O_O]")

    from tools.rag_engine import consultar, COLLECTIONS
    contexto_partes = []
    fuentes = []

    for coleccion in COLLECTIONS:
        resultado = consultar(
            query=f"informacion agricola ecologica para region {region}",
            collection_name=coleccion,
            provider=provider,
            db_type="FAISS",
        )
        if "vacia" not in resultado and "no disponible" not in resultado:
            contexto_partes.append(f"[{coleccion}]\n{resultado}")
            fuentes.append(coleccion)

    contexto = "\n\n".join(contexto_partes) if contexto_partes else "Base de conocimientos local vacia."
    log_ok(f"RAG Local recopilo {len(fuentes)} colecciones tematicas activas", kaomoji="(^_^)/")
    return {"contexto_local": contexto, "fuentes_locales": fuentes}


# ──────────────────────────────────────────────────────────────────────────────
# NODO: Despachador Web (Fork → mini-agentes paralelos)
# ──────────────────────────────────────────────────────────────────────────────

def nodo_despachador_web(state: EstadoGrafoV2) -> dict:
    """Fork: despacha la investigación a los tres mini-agentes web en paralelo."""
    log_flujo("inicio/rag_local", "despachador", "Bifurcacion paralela activada")
    log_agente("DESPACHADOR_WEB", "Despachando tareas en paralelo a 3 mini-agentes (Tavily, Academico, Scraper)...", kaomoji="[>_<]")
    return {}


# ──────────────────────────────────────────────────────────────────────────────
# NODO: Mini-Agente Tavily/CONABIO
# ──────────────────────────────────────────────────────────────────────────────

def nodo_mini_tavily(state: EstadoGrafoV2) -> dict:
    """Mini-Agente 1: Búsqueda rápida con Tavily y CONABIO."""
    provider = state.get("provider", "Gemini")
    region = state.get("region", "Mexico")
    llm = get_llm(provider=provider, temperature=0.1)
    log_mini_agente("TAVILY_CONABIO", f"Buscando biodiversidad, clima y cultivos en {region} [{provider}]...", kaomoji="(O_O)")

    from tools.search import buscar_tavily_mexico, buscar_conabio
    from langgraph.prebuilt import create_react_agent

    agente = create_react_agent(
        model=llm,
        tools=[buscar_tavily_mexico, buscar_conabio],
        prompt=(
            "Eres un mini-agente de busqueda rapida del Sistema Multiagente AgriPoli. "
            "Busca informacion sobre la region indicada usando Tavily y CONABIO. "
            "Siempre incluye las URLs de tus fuentes."
        )
    )
    consulta = f"clima, cultivos y polinizadores en {region} Mexico CONABIO SADER"
    resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
    texto = resultado["messages"][-1].content
    log_mini_agente("TAVILY_CONABIO", "Busqueda ambiental completada.", kaomoji="(o_o)")
    return {"resultado_tavily": texto}


# ──────────────────────────────────────────────────────────────────────────────
# NODO: Mini-Agente Académico
# ──────────────────────────────────────────────────────────────────────────────

def nodo_mini_academico(state: EstadoGrafoV2) -> dict:
    """Mini-Agente 2: Papers académicos sobre la región (arXiv + Semantic Scholar)."""
    provider = state.get("provider", "Gemini")
    region = state.get("region", "Mexico")
    llm = get_llm(provider=provider, temperature=0.1)
    log_mini_agente("ACADEMICO", f"Indagando articulos cientificos (arXiv, Semantic Scholar) para {region} [{provider}]...", kaomoji="(^_~)")

    from tools.herramientas_cientificas import buscar_arxiv_agricola, buscar_semantic_scholar_agricola, formateador_citas_agricola
    from langgraph.prebuilt import create_react_agent

    agente = create_react_agent(
        model=llm,
        tools=[buscar_arxiv_agricola, buscar_semantic_scholar_agricola, formateador_citas_agricola],
        prompt=(
            "Eres un mini-agente de investigacion academica del Sistema Multiagente AgriPoli. "
            "Busca papers cientificos sobre agricultura regenerativa, polinizadores y ecologia de suelos. "
            "Incluye siempre los DOIs o URLs de los papers y formatea las citas usando formateador_citas_agricola."
        )
    )
    consulta = f"agricultura regenerativa polinizadores suelos {region} Mexico"
    resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
    texto = resultado["messages"][-1].content
    log_mini_agente("ACADEMICO", "Recopilacion de literatura cientifica completada.", kaomoji="(o_o)")
    return {"resultado_academico": texto}


# ──────────────────────────────────────────────────────────────────────────────
# NODO: Mini-Agente Scraper Profundo
# ──────────────────────────────────────────────────────────────────────────────

def nodo_mini_scraper(state: EstadoGrafoV2) -> dict:
    """Mini-Agente 3: Scraping profundo de páginas gubernamentales."""
    provider = state.get("provider", "Gemini")
    region = state.get("region", "Mexico")
    llm = get_llm(provider=provider, temperature=0.1)
    log_mini_agente("SCRAPER", f"Extrayendo informacion profunda de fuentes gubernamentales [{provider}]...", kaomoji="[~_~]")

    from tools.scraper import lector_web_playwright, lector_pdf_web
    from tools.herramientas_cientificas import lector_web_selenium
    from tools.search import buscar_tavily_mexico
    from langgraph.prebuilt import create_react_agent

    agente = create_react_agent(
        model=llm,
        tools=[buscar_tavily_mexico, lector_web_playwright, lector_pdf_web, lector_web_selenium],
        prompt=(
            "Eres un mini-agente de scraping profundo del Sistema Multiagente AgriPoli. "
            "Usa Tavily para encontrar URLs relevantes de sitios del gobierno (SADER, CONABIO, INIFAP, UNAM). "
            "Luego usa lector_web_playwright o lector_pdf_web para extraer el contenido COMPLETO. "
            "Prioriza documentos PDF oficiales sobre la region."
        )
    )
    consulta = f"monografias cultivos flora nativa {region} SADER CONABIO PDF"
    resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
    texto = resultado["messages"][-1].content
    log_mini_agente("SCRAPER", "Extraccion web completada.", kaomoji="(o_o)")
    return {"resultado_scraper": texto}


# ──────────────────────────────────────────────────────────────────────────────
# NODO: Parseador Web (Join → consolida los 3 mini-agentes)
# ──────────────────────────────────────────────────────────────────────────────

def nodo_parseador_web(state: EstadoGrafoV2) -> dict:
    """Join: consolida los resultados de los 3 mini-agentes en un contexto único."""
    provider = state.get("provider", "Gemini")
    llm = get_llm(provider=provider, temperature=0.0)
    log_flujo("[mini_tavily, mini_academico, mini_scraper]", "parseador_web", "Union (join) de mini-agentes")
    log_agente("PARSEADOR_WEB", "Sintetizando y estructurando hallazgos web...", kaomoji="(^o^)")

    import re
    prompt = (
        f"Eres el Parseador Web del Sistema Multiagente AgriPoli.\n"
        f"Consolida en un solo reporte estructurado los resultados de tus 3 mini-agentes.\n"
        f"Organiza por categorias: Clima/Suelo, Cultivos/Agricultura, Flora/Polinizadores, Ecologia.\n"
        f"AL FINAL incluye un bloque XML: <fuentes>url1\nurl2\n...</fuentes>\n\n"
        f"--- MINI-AGENTE TAVILY ---\n{state.get('resultado_tavily', 'Sin datos')}\n\n"
        f"--- MINI-AGENTE ACADEMICO ---\n{state.get('resultado_academico', 'Sin datos')}\n\n"
        f"--- MINI-AGENTE SCRAPER ---\n{state.get('resultado_scraper', 'Sin datos')}"
    )
    response = llm.invoke(prompt)
    texto = response.content if isinstance(response.content, str) else str(response.content)

    # Extraer URLs del bloque XML
    fuentes = []
    match = re.search(r"<fuentes>(.*?)</fuentes>", texto, re.DOTALL | re.IGNORECASE)
    if match:
        fuentes = [s.strip() for s in match.group(1).strip().split("\n") if s.strip()]
        texto = re.sub(r"<fuentes>.*?</fuentes>", "", texto, flags=re.DOTALL).strip()

    log_ok(f"Parseador consolido contexto web con {len(fuentes)} fuentes citadas", kaomoji="(^_^)/")
    return {"contexto_web": texto, "fuentes_web": fuentes}


# ──────────────────────────────────────────────────────────────────────────────
# NODO: Fusionador (RAG Local + Web)
# ──────────────────────────────────────────────────────────────────────────────

def nodo_fusionador(state: EstadoGrafoV2) -> dict:
    """Reconcilia el contexto local (RAG) con el contexto web."""
    provider = state.get("provider", "Gemini")
    llm = get_llm(provider=provider, temperature=0.1)
    log_flujo("parseador_web", "fusionador", "Reconciliacion de datos")
    log_agente("FUSIONADOR", "Reconciliando contexto local RAG con hallazgos web...", kaomoji="(^-^)/")

    prompt = (
        f"Eres un sintetizador cientifico del dominio agricola-ecologico mexicano.\n"
        f"Fusiona las dos fuentes de informacion. Etiqueta con [LOCAL] o [WEB] segun origen.\n"
        f"Detecta complementariedades y discrepancias.\n\n"
        f"--- CONTEXTO LOCAL (RAG) ---\n{state.get('contexto_local', 'Sin datos locales')}\n\n"
        f"--- CONTEXTO WEB ---\n{state.get('contexto_web', 'Sin datos web')}"
    )
    response = llm.invoke(prompt)
    texto = response.content if isinstance(response.content, str) else str(response.content)
    log_ok("Contexto fusionado exitosamente.", kaomoji="(^_^)/")
    return {"contexto_fusionado": texto}


# ──────────────────────────────────────────────────────────────────────────────
# NODOS: Agro Experto y Ecológico (usando contexto enriquecido)
# ──────────────────────────────────────────────────────────────────────────────

def nodo_agro(state: EstadoGrafoV2) -> dict:
    provider = state.get("provider", "Gemini")
    log_flujo("fusionador/rag", "agro", "Envio de contexto a diseno agronomico")
    log_agente("AGRO_EXPERTO", f"Formulando recomendaciones de cultivos, suelo y rotacion [{provider}]...", kaomoji="(^-^)")
    agente = crear_agro_experto(provider=provider)
    flow = state.get("flow_type", "Hibrido")
    if flow == "Solo Local":
        contexto = state.get("contexto_local", "")
    elif flow == "Solo Web":
        contexto = state.get("contexto_web", "")
    else:
        contexto = state.get("contexto_fusionado", "")

    prompt = (
        f"Region: {state.get('region')}. "
        f"Indice de degradacion RF: {state.get('indice_degradacion_rf', 0)}. "
        f"Historial de siembra: {state.get('historial_siembra', [])}.\n\n"
        f"Contexto investigado:\n{contexto[:4000]}"
    )
    resultado = agente.invoke({"messages": [HumanMessage(content=prompt)]})
    texto = resultado["messages"][-1].content
    log_ok("Propuestas agronomicas formuladas.", kaomoji="(^_^)/")
    return {"propuestas_agricolas": [{"texto": texto}]}


def nodo_ecologico(state: EstadoGrafoV2) -> dict:
    provider = state.get("provider", "Gemini")
    log_flujo("agro", "ecologico", "Transmitiendo propuestas agricolas para diseno simbiotico")
    log_agente("ECOLOGICO", f"Disenando islas de polinizadores y conservacion biologica [{provider}]...", kaomoji="(*_*)")
    agente = crear_agente_ecologico(provider=provider)
    propuestas_agro = json.dumps(state.get("propuestas_agricolas", []))
    contexto = state.get("contexto_fusionado", state.get("contexto_web", ""))
    prompt = (
        f"Diseña una isla polinizadora para {state.get('region')} "
        f"que complemente estos cultivos propuestos: {propuestas_agro}.\n\n"
        f"Contexto ecologico disponible:\n{contexto[:3000]}"
    )
    resultado = agente.invoke({"messages": [HumanMessage(content=prompt)]})
    texto = resultado["messages"][-1].content
    log_ok("Isla polinizadora y matriz de conservacion disenadas.", kaomoji="(^_^)/")
    return {"propuestas_ecologicas": [{"texto": texto}]}


# ──────────────────────────────────────────────────────────────────────────────
# NODO: Validador (Supervisor con Conditional Edges)
# ──────────────────────────────────────────────────────────────────────────────

def nodo_validador(state: EstadoGrafoV2) -> dict:
    provider = state.get("provider", "Gemini")
    iteraciones = state.get("iteraciones_revision", 0) + 1
    log_flujo("ecologico", "validador", "Sometiendo plan completo a evaluacion de consistencia")
    log_agente("VALIDADOR", f"Auditoria tecnica agronomo-ecologica (Revision #{iteraciones})...", kaomoji="[x_x]")

    llm = get_llm(provider=provider, temperature=0.0)
    prompt = (
        f"Evalua si hay conflicto biologico entre:\n"
        f"Cultivos: {json.dumps(state.get('propuestas_agricolas', []))}\n"
        f"Flora ecologica: {json.dumps(state.get('propuestas_ecologicas', []))}\n"
        f"Responde APROBADO o RECHAZADO con una breve justificacion."
    )
    response = llm.invoke(prompt)
    texto = response.content if isinstance(response.content, str) else str(response.content)
    estado = "APROBADO" if "APROBADO" in texto else "RECHAZADO"
    if iteraciones >= 3:
        estado = "APROBADO"

    if estado == "APROBADO":
        log_ok(f"Plan Integral APROBADO por el Validador en revision #{iteraciones}.", kaomoji="(^_^)/")
    else:
        log_info(f"Plan observado por el Validador: {texto[:100]}... Reenviando a correccion.", kaomoji="[o_o]")

    return {
        "estado_revision": estado,
        "revisiones_supervisor": [f"Revision #{iteraciones}: {texto}"],
        "iteraciones_revision": iteraciones,
    }


def nodo_estructurador(state: EstadoGrafoV2) -> dict:
    log_flujo("validador", "estructurador", "Plan Aprobado -> Generacion de Modelo 3D")
    log_agente("ESTRUCTURADOR", "Compilando esquema visual Three.js y resumen ejecutivo...", kaomoji="(^o^)")
    json_final = invocar_estructurador(
        region=state.get("region", ""),
        degradacion=state.get("indice_degradacion_rf", 0.0),
        suelo=state.get("datos_climaticos", {}).get("resumen", "Suelo desconocido"),
        prop_agro=json.dumps(state.get("propuestas_agricolas", [])),
        prop_eco=json.dumps(state.get("propuestas_ecologicas", [])),
    )
    log_ok("Modelo 3D y especificaciones espaciales generadas exitosamente.", kaomoji="(^_^)/")
    return {"json_threejs_final": json_final}


# ──────────────────────────────────────────────────────────────────────────────
# RUTEO (Conditional Edges)
# ──────────────────────────────────────────────────────────────────────────────

def router_inicio(state: EstadoGrafoV2) -> str:
    flow = state.get("flow_type", "Hibrido")
    if flow == "Solo Web":
        log_flujo("START", "despachador", f"Modo de flujo: '{flow}'")
        return "Solo Web"
    log_flujo("START", "rag_local", f"Modo de flujo: '{flow}'")
    return "Analizar Local"

def router_rag(state: EstadoGrafoV2) -> str:
    flow = state.get("flow_type", "Hibrido")
    if flow == "Solo Local":
        log_flujo("rag_local", "agro", f"Modo de flujo: '{flow}'")
        return "Ir a Agro"
    log_flujo("rag_local", "despachador", f"Modo de flujo: '{flow}'")
    return "Ir a Web"

def router_web(state: EstadoGrafoV2) -> str:
    flow = state.get("flow_type", "Hibrido")
    if flow == "Solo Web":
        log_flujo("parseador_web", "agro", f"Modo de flujo: '{flow}'")
        return "Ir a Agro"
    log_flujo("parseador_web", "fusionador", f"Modo de flujo: '{flow}'")
    return "Fusionar"

def router_validacion(state: EstadoGrafoV2) -> str:
    if state.get("estado_revision") == "APROBADO":
        log_flujo("validador", "estructurador", "Auditoria aprobada -> Procediendo a traductor 3D")
        return "Estructurar"
    log_flujo("validador", "agro", "Ajustes requeridos -> Retornando a nodo agricola")
    return "Recalcular Agro"


# ──────────────────────────────────────────────────────────────────────────────
# CONSTRUCCIÓN DEL GRAFO
# ──────────────────────────────────────────────────────────────────────────────

def crear_grafo_v2(provider: str = "Gemini"):
    """Compila el Grafo Principal V2 con MemorySaver y soporte multi-proveedor."""
    workflow = StateGraph(EstadoGrafoV2)

    # Nodos
    workflow.add_node("rag_local",     nodo_rag_local)
    workflow.add_node("despachador",   nodo_despachador_web)
    workflow.add_node("mini_tavily",   nodo_mini_tavily)
    workflow.add_node("mini_academico",nodo_mini_academico)
    workflow.add_node("mini_scraper",  nodo_mini_scraper)
    workflow.add_node("parseador_web", nodo_parseador_web)
    workflow.add_node("fusionador",    nodo_fusionador)
    workflow.add_node("agro",          nodo_agro)
    workflow.add_node("ecologico",     nodo_ecologico)
    workflow.add_node("validador",     nodo_validador)
    workflow.add_node("estructurador", nodo_estructurador)

    # Ruteo de inicio
    workflow.add_conditional_edges(START, router_inicio, {
        "Solo Web":      "despachador",
        "Analizar Local": "rag_local",
    })

    # Desde RAG local: ir a agro (Solo Local) o a web (Hibrido)
    workflow.add_conditional_edges("rag_local", router_rag, {
        "Ir a Agro": "agro",
        "Ir a Web":  "despachador",
    })

    # Fork paralelo desde el despachador
    workflow.add_edge("despachador", "mini_tavily")
    workflow.add_edge("despachador", "mini_academico")
    workflow.add_edge("despachador", "mini_scraper")

    # Join al parseador
    workflow.add_edge("mini_tavily",    "parseador_web")
    workflow.add_edge("mini_academico", "parseador_web")
    workflow.add_edge("mini_scraper",   "parseador_web")

    # Desde el parseador: ir a agro (Solo Web) o fusionar (Hibrido)
    workflow.add_conditional_edges("parseador_web", router_web, {
        "Ir a Agro": "agro",
        "Fusionar":  "fusionador",
    })

    # Fusionador siempre va a agro
    workflow.add_edge("fusionador", "agro")

    # Flujo principal
    workflow.add_edge("agro",      "ecologico")
    workflow.add_edge("ecologico", "validador")

    # Ciclo de validación
    workflow.add_conditional_edges("validador", router_validacion, {
        "Estructurar":     "estructurador",
        "Recalcular Agro": "agro",
    })
    workflow.add_edge("estructurador", END)

    # MemorySaver: historial persistente entre llamadas (por thread_id)
    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN DE EJECUCIÓN CON STREAMING
# ──────────────────────────────────────────────────────────────────────────────

def run_enjambre_stream(
    region: str,
    indice_degradacion_rf: float = 0.5,
    historial_siembra: list[str] = None,
    thread_id: str = "default",
    provider: str = "Gemini",
    flow_type: Literal["Hibrido", "Solo Local", "Solo Web"] = "Hibrido",
):
    """Ejecuta el grafo con streaming de eventos.
    Yields cada evento del grafo para visualización en tiempo real.

    Args:
        region:                Nombre de la región a analizar.
        indice_degradacion_rf: Índice de degradación del modelo Random Forest (0-1).
        historial_siembra:     Lista de cultivos anteriores del campesino.
        thread_id:             ID único para la sesión de memoria (MemorySaver).
        provider:              Proveedor LLM ("Gemini", "Groq", "Ollama", etc.).
        flow_type:             Modo de flujo de investigación.
    """
    grafo = crear_grafo_v2(provider=provider)

    estado_inicial = {
        "region": region,
        "indice_degradacion_rf": indice_degradacion_rf,
        "historial_siembra": historial_siembra or [],
        "provider": provider,
        "flow_type": flow_type,
        "iteraciones_revision": 0,
        "revisiones_supervisor": [],
        "fuentes_web": [],
        "fuentes_locales": [],
        "datos_climaticos": {},
        "datos_geospatiales": {},
        "propuestas_agricolas": [],
        "propuestas_ecologicas": [],
        "json_threejs_final": {},
        "estado_revision": "",
    }

    config = {"configurable": {"thread_id": thread_id}}
    for event in grafo.stream(estado_inicial, config=config):
        yield event


def run_enjambre(
    region: str,
    indice_degradacion_rf: float = 0.5,
    historial_siembra: list[str] = None,
    thread_id: str = "default",
    provider: str = "Gemini",
    flow_type: Literal["Hibrido", "Solo Local", "Solo Web"] = "Hibrido",
) -> dict:
    """Ejecuta el grafo V2 de forma síncrona y retorna el estado final completo."""
    grafo = crear_grafo_v2(provider=provider)
    estado_inicial = {
        "region": region,
        "indice_degradacion_rf": indice_degradacion_rf,
        "historial_siembra": historial_siembra or [],
        "provider": provider,
        "flow_type": flow_type,
        "iteraciones_revision": 0,
        "revisiones_supervisor": [],
        "fuentes_web": [],
        "fuentes_locales": [],
        "datos_climaticos": {},
        "datos_geospatiales": {},
        "propuestas_agricolas": [],
        "propuestas_ecologicas": [],
        "json_threejs_final": {},
        "estado_revision": "",
    }
    config = {"configurable": {"thread_id": thread_id}}
    return grafo.invoke(estado_inicial, config=config)

