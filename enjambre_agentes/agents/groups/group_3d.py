"""
Grupo 3D — Sub-grafo LangGraph del Sistema Multiagente AgriPoli V3.

Responsabilidad: Traducir propuestas narrativas de Agronomo + Ecologico
a JSON estructurado compatible con Three.js.

Sub-agentes:
  * fusionador_3d — Reconcilia y ensambla propuestas para el esquema Mapa3D
  * estructurador — LLM con structured output (Pydantic Mapa3D)
  * validador_3d  — Verifica el JSON contra el esquema antes de exportar

Este grupo es OPCIONAL — solo se activa si el Supervisor lo solicita
y el usuario confirma.
"""
from __future__ import annotations

import json
from langgraph.graph import StateGraph, START, END

import config.silenciador
from config.models import get_llm_para_agente
from config.agri_logger import log_agente, log_flujo, log_ok, log_info, log_error
from agents.state_v3 import EstadoGrupo3D
from agents.estructurador import invocar_estructurador
from schemas.threejs_schema import Mapa3D


# ─────────────────────────────────────────────────────────────────────────────
# NODO: Fusionador 3D
# ─────────────────────────────────────────────────────────────────────────────

def nodo_fusionador_3d(state: EstadoGrupo3D) -> dict:
    """Ensambla y reconcilia las propuestas agro + eco en un prompt coherente para el estructurador."""
    llm = get_llm_para_agente("fusionador_3d")
    log_flujo("propuestas_agro+eco", "fusionador_3d", "Ensamblando datos para generacion 3D")
    log_agente("FUSIONADOR_3D", "Reconciliando propuestas agricola y ecologica para el modelo 3D...", kaomoji="(^o^)")

    region = state.get("region", "region desconocida")
    agro = json.dumps(state.get("propuestas_agricolas", []), ensure_ascii=False)[:2000]
    eco  = json.dumps(state.get("propuestas_ecologicas", []), ensure_ascii=False)[:2000]

    prompt = (
        f"Eres el Fusionador 3D del Sistema AgriPoli.\n"
        f"Region: {region}\n\n"
        "Tu tarea es preparar un resumen tecnico consolidado que combine:\n"
        "- La propuesta agricola (cultivos, rotaciones, coordenadas logicas)\n"
        "- La propuesta ecologica (flora polinizadora, islas, barreras vivas)\n"
        "Incluye coordenadas relativas (x, y, z) y colores hex para cada especie.\n\n"
        f"--- PROPUESTA AGRICOLA ---\n{agro}\n\n"
        f"--- PROPUESTA ECOLOGICA ---\n{eco}"
    )
    try:
        response = llm.invoke(prompt)
        resumen = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as e:
        resumen = f"{agro}\n{eco}"
        log_error(str(e), kaomoji="[X_X]")

    log_ok("Resumen 3D ensamblado.", kaomoji="(^_^)/")
    return {"suelo_resumen": resumen}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE: Referencias y Estandares 3D (FAO / INIFAP / Three.js Specs)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_referencias_3d(state: EstadoGrupo3D) -> dict:
    """Extrae exclusivamente especificaciones espaciales, manuales de densidad de siembra y referencias Three.js.
    De la consulta original y propuestas solo extrae las fuentes de arquitectura vegetal y estandares espaciales
    y da el formato correspondiente estandarizado.
    """
    region = state.get("region", "region desconocida")
    consulta_orig = state.get("consulta_original", "") or f"marcos de siembra y densidades de plantacion en {region}"
    llm = get_llm_para_agente("mini_referencias_3d")
    log_mini_agente("MINI_REFERENCIAS_3D", f"Extrayendo estandares espaciales y fuentes para modelado 3D...", kaomoji="(^_~)")

    from tools.search import buscar_tavily_mexico
    from langchain_core.messages import HumanMessage
    from langgraph.prebuilt import create_react_agent
    import re

    agente = create_react_agent(
        model=llm,
        tools=[buscar_tavily_mexico],
        prompt=(
            "Eres el Mini-Agente de Referencias del Grupo 3D de AgriPoli. "
            "Tu UNICO objetivo es extraer de la consulta original y del ambito de diseno espacial las fuentes tecnicas, manuales agronomicos de densidad/espaciamiento y estandares graficos 3D. "
            "No inventes datos ni hagas modelos geometricos directos. Solo extrae y formatea las referencias tecnicas: "
            "1. Guias tecnicas de espaciamiento, marcos de siembra y arquitectura de copas (INIFAP, SADER, FAO). "
            "2. Estandares y especificaciones de representacion espacial y Three.js (Three.js Docs, coordenadas cartesianas relativas, modelos de dosel vegetal). "
            "FORMATO ESTANDAR OBLIGATORIO: "
            "[FUENTES Y REFERENCIAS: GRUPO 3D]\n"
            "1. [Institucion / Manual] Guia tecnica de espaciamiento y marco de plantacion | Enlace/Referencia: <URL o cita>\n"
            "2. [Estandar Grafico / Software] Especificacion de coordenadas y grafo de escena 3D | Enlace: <URL>"
        ),
    )
    consulta = (
        f"guias tecnicas espaciamiento marcos de siembra INIFAP FAO y especificacion Three.js para {consulta_orig} en {region}"
    )
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_referencias_3d] {e}"
        log_error(str(e), kaomoji="[X_X]")

    urls = re.findall(r'https?://[^\s)\]>"\']+', str(texto))
    log_mini_agente("MINI_REFERENCIAS_3D", f"Fuentes de diseno 3D extraidas ({len(urls)} enlaces).", kaomoji="(^_~)")
    return {
        "resultado_mini_referencias": texto,
        "referencias_fuentes": urls,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODO: Estructurador (Structured Output con Pydantic)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_estructurador(state: EstadoGrupo3D) -> dict:
    """Traduce el resumen fusionado y referencias espaciales a JSON Mapa3D estructurado via Pydantic."""
    log_flujo("fusionador_3d + mini_refs_3d", "estructurador", "Generando JSON Three.js con estandares espaciales")
    log_agente("ESTRUCTURADOR", "Compilando esquema visual Three.js desde propuestas...", kaomoji="(^o^)")

    resumen_suelo = state.get("suelo_resumen", "Suelo no especificado")
    refs_3d = state.get("resultado_mini_referencias", "")
    if refs_3d:
        resumen_suelo += f"\n\n--- REFERENCIAS Y ESTANDARES ESPACIALES 3D ---\n{refs_3d[:800]}"

    try:
        json_final = invocar_estructurador(
            region=state.get("region", ""),
            degradacion=state.get("indice_degradacion_rf", 0.0),
            suelo=resumen_suelo,
            prop_agro=json.dumps(state.get("propuestas_agricolas", []), ensure_ascii=False)[:3000],
            prop_eco=json.dumps(state.get("propuestas_ecologicas", []), ensure_ascii=False)[:3000],
        )
        if not json_final.get("referencias_fuentes"):
            json_final["referencias_fuentes"] = state.get("referencias_fuentes", [])
        log_ok("JSON Three.js generado exitosamente.", kaomoji="(^_^)/")
        return {"json_threejs_final": json_final, "validacion_3d": "VALIDO"}
    except Exception as e:
        log_error(f"Error generando JSON 3D: {e}", kaomoji="[X_X]")
        return {"json_threejs_final": {}, "validacion_3d": "INVALIDO"}


# ─────────────────────────────────────────────────────────────────────────────
# NODO: Validador 3D
# ─────────────────────────────────────────────────────────────────────────────

def nodo_validador_3d(state: EstadoGrupo3D) -> dict:
    """Valida el JSON generado contra el esquema Pydantic Mapa3D."""
    log_flujo("estructurador", "validador_3d", "Verificando esquema JSON")
    log_agente("VALIDADOR_3D", "Auditando el JSON Three.js contra el esquema Pydantic...", kaomoji="[x_x]")

    json_final = state.get("json_threejs_final", {})
    ciclo = state.get("ciclo_3d", 0) + 1

    if not json_final:
        log_error("JSON vacio. Marcando como invalido.", kaomoji="[X_X]")
        return {"validacion_3d": "INVALIDO", "ciclo_3d": ciclo}

    try:
        # Validar contra el esquema Pydantic
        Mapa3D(**json_final)
        log_ok("JSON Three.js VALIDO segun esquema Pydantic Mapa3D.", kaomoji="(^_^)/")
        return {"validacion_3d": "VALIDO", "ciclo_3d": ciclo}
    except Exception as e:
        log_error(f"JSON invalido: {e}", kaomoji="[X_X]")
        return {"validacion_3d": "INVALIDO", "ciclo_3d": ciclo}


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────

def router_validacion_3d(state: EstadoGrupo3D) -> str:
    validacion = state.get("validacion_3d", "INVALIDO")
    ciclo = state.get("ciclo_3d", 0)

    if validacion == "VALIDO":
        log_flujo("validador_3d", "END", "JSON valido -> exportando")
        return "Valido"
    if ciclo >= 2:
        log_info("Max reintentos 3D alcanzados. Exportando con advertencias.", kaomoji="[x_x]")
        return "Valido"
    log_flujo("validador_3d", "estructurador", "JSON invalido -> reintentando estructuracion")
    return "Reintentar"


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCCION DEL SUB-GRAFO
# ─────────────────────────────────────────────────────────────────────────────

def crear_grafo_3d():
    """Compila y retorna el sub-grafo del Grupo Generador 3D con mini-agente de referencias."""
    workflow = StateGraph(EstadoGrupo3D)

    workflow.add_node("fusionador_3d",       nodo_fusionador_3d)
    workflow.add_node("mini_referencias_3d", nodo_mini_referencias_3d)
    workflow.add_node("estructurador",       nodo_estructurador)
    workflow.add_node("validador_3d",        nodo_validador_3d)

    # Fork paralelo desde START
    workflow.add_edge(START,                 "fusionador_3d")
    workflow.add_edge(START,                 "mini_referencias_3d")

    # Join hacia estructurador
    workflow.add_edge("fusionador_3d",       "estructurador")
    workflow.add_edge("mini_referencias_3d", "estructurador")

    workflow.add_edge("estructurador",       "validador_3d")

    # Loop de reintento: max 2 ciclos si el JSON no pasa la validacion
    workflow.add_conditional_edges("validador_3d", router_validacion_3d, {
        "Valido":    END,
        "Reintentar": "estructurador",
    })

    return workflow.compile()
