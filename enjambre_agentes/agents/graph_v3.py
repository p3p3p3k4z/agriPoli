"""
Grafo Maestro V3 del Sistema de Apoyo Multiagente AgriPoli.

Orquesta los cuatro grupos de agentes mediante un StateGraph maestro
con loops de retroalimentacion inter-grupo:

Flujo principal:
  START -> nodo_extractor -> nodo_agronomo -> nodo_ecologico
        -> nodo_supervisor_validador -> [nodo_3d_opcional] -> END

Loops inter-grupo (manejados por el Supervisor):
  * nodo_agronomo detecta falta de contexto -> re-invoca nodo_extractor
  * nodo_ecologico incompatible con agronomo -> regresa a nodo_agronomo
  * nodo_supervisor decide activar 3D -> nodo_3d_opcional
"""
from __future__ import annotations

import json
import os
import re
import datetime
from typing import Literal
from langchain_core.messages import HumanMessage

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

import config.silenciador
from config.models import get_llm_para_agente, cargar_config_agentes, extraer_texto_mensaje
from config.agri_logger import log_agente, log_flujo, log_ok, log_info, log_error
from agents.state_v3 import EstadoMaestroV3
from agents.groups.group_extractor import crear_grafo_extractor, EstadoGrupoExtractor
from agents.groups.group_agronomo import crear_grafo_agronomo, EstadoGrupoAgronomo
from agents.groups.group_ecologico import crear_grafo_ecologico, EstadoGrupoEcologico
from agents.groups.group_3d import crear_grafo_3d, EstadoGrupo3D


# ─────────────────────────────────────────────────────────────────────────────
# NODO: Grupo Extractor
# ─────────────────────────────────────────────────────────────────────────────

def nodo_extractor(state: EstadoMaestroV3) -> dict:
    """Invoca el sub-grafo del Grupo Extractor y transfiere el contexto al estado maestro."""
    config = cargar_config_agentes().get("configuracion", {})
    flow_type = state.get("flow_type", config.get("flow_type", "Hibrido"))
    region = state.get("region", "Mexico")

    log_flujo("START" if state.get("iteraciones_supervisor", 0) == 0 else "supervisor", "grupo_extractor",
              f"Invocando Grupo Extractor (flow_type='{flow_type}')")
    log_agente("GRUPO_EXTRACTOR", f"Iniciando recopilacion de informacion para '{region}'...", kaomoji="[>_<]")

    grafo = crear_grafo_extractor()
    estado_inicial: EstadoGrupoExtractor = {
        "region": region,
        "flow_type": flow_type,
        "resultado_tavily": "",
        "resultado_academico": "",
        "resultado_scraper": "",
        "resultado_mini_referencias": "",
        "referencias_fuentes": [],
        "contexto_web": "",
        "fuentes_web": [],
        "descarga_confirmada": False,
    }
    resultado = grafo.invoke(estado_inicial)
    contexto = resultado.get("contexto_web", "")
    fuentes = resultado.get("referencias_fuentes", []) or resultado.get("fuentes_web", [])
    log_ok(f"Grupo Extractor completado. Contexto: {len(contexto)} caracteres.", kaomoji="(^_^)/")
    return {"contexto_extractor": contexto, "referencias_fuentes": fuentes}


# ─────────────────────────────────────────────────────────────────────────────
# NODO: Grupo Agronomo
# ─────────────────────────────────────────────────────────────────────────────

def nodo_agronomo(state: EstadoMaestroV3) -> dict:
    """Invoca el sub-grafo del Grupo Agronomo con el contexto del Extractor."""
    config = cargar_config_agentes().get("configuracion", {})
    region = state.get("region", "Mexico")

    log_flujo("grupo_extractor", "grupo_agronomo", "Enviando contexto al Agronomo")
    log_agente("GRUPO_AGRONOMO", f"Iniciando analisis agricola para '{region}'...", kaomoji="(^-^)")

    # Construir RAG local para el Agronomo
    contexto_rag = ""
    try:
        from tools.rag_engine import consultar
        for col in ("suelo", "agricultura", "manuales_agricolas"):
            parte = consultar(
                query=f"cultivos suelo rotacion {region}",
                collection_name=col,
                provider="Gemini",
                db_type="FAISS",
            )
            if "vacia" not in parte and "no disponible" not in parte:
                contexto_rag += f"\n[{col}]\n{parte}"
    except Exception:
        pass

    grafo = crear_grafo_agronomo()
    estado_inicial: EstadoGrupoAgronomo = {
        "region": region,
        "contexto_extractor": state.get("contexto_extractor", ""),
        "contexto_rag_agro": contexto_rag,
        "indice_degradacion_rf": state.get("indice_degradacion_rf", 0.5),
        "historial_siembra": state.get("historial_siembra", []),
        "resultado_mini_suelo": "",
        "resultado_mini_cultivo": "",
        "resultado_mini_siap": "",
        "resultado_mini_inegi": "",
        "resultado_mini_calculadora": "",
        "resultado_mini_rotacion": "",
        "resultado_mini_referencias": "",
        "referencias_fuentes": [],
        "propuestas_agricolas": [],
        "anotacion_fusionador_agro": "",
        "ciclo_agronomo": 0,
        "estado_fusion_agro": "PENDIENTE",
    }
    resultado = grafo.invoke(estado_inicial)
    propuestas = resultado.get("propuestas_agricolas", [])
    fuentes = resultado.get("referencias_fuentes", [])
    log_ok(f"Grupo Agronomo: {len(propuestas)} propuesta(s) aprobada(s) en {resultado.get('ciclo_agronomo', 0)} ciclo(s).", kaomoji="(^_^)/")
    return {"propuestas_agricolas": propuestas, "referencias_fuentes": fuentes}


# ─────────────────────────────────────────────────────────────────────────────
# NODO: Grupo Ecologico
# ─────────────────────────────────────────────────────────────────────────────

def nodo_ecologico(state: EstadoMaestroV3) -> dict:
    """Invoca el sub-grafo del Grupo Ecologico con el contexto del Extractor y del Agronomo."""
    region = state.get("region", "Mexico")

    log_flujo("grupo_agronomo", "grupo_ecologico", "Transmitiendo propuestas al Ecologo")
    log_agente("GRUPO_ECOLOGICO", f"Iniciando diseno de isla polinizadora para '{region}'...", kaomoji="(*_*)")

    # RAG local para el Ecologo
    contexto_rag_eco = ""
    try:
        from tools.rag_engine import consultar
        for col in ("polinizadores", "flora_botanica", "general"):
            parte = consultar(
                query=f"polinizadores flora nativa {region}",
                collection_name=col,
                provider="Gemini",
                db_type="FAISS",
            )
            if "vacia" not in parte and "no disponible" not in parte:
                contexto_rag_eco += f"\n[{col}]\n{parte}"
    except Exception:
        pass

    grafo = crear_grafo_ecologico()
    estado_inicial: EstadoGrupoEcologico = {
        "region": region,
        "contexto_extractor": state.get("contexto_extractor", ""),
        "propuestas_agricolas": state.get("propuestas_agricolas", []),
        "contexto_rag_eco": contexto_rag_eco,
        "resultado_mini_flora": "",
        "resultado_mini_polinizadores": "",
        "resultado_mini_catalogo": "",
        "resultado_mini_gbif": "",
        "resultado_mini_control_biologico": "",
        "resultado_mini_atractores": "",
        "resultado_mini_referencias": "",
        "referencias_fuentes": [],
        "propuestas_ecologicas": [],
        "anotacion_fusionador_eco": "",
        "ciclo_ecologico": 0,
        "estado_fusion_eco": "PENDIENTE",
    }
    resultado = grafo.invoke(estado_inicial)
    propuestas = resultado.get("propuestas_ecologicas", [])
    fuentes = resultado.get("referencias_fuentes", [])
    log_ok(f"Grupo Ecologico: {len(propuestas)} propuesta(s) aprobada(s) en {resultado.get('ciclo_ecologico', 0)} ciclo(s).", kaomoji="(^_^)/")
    return {"propuestas_ecologicas": propuestas, "referencias_fuentes": fuentes}


# ─────────────────────────────────────────────────────────────────────────────
# NODO: Supervisor Validador (con loops inter-grupo)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_supervisor_validador(state: EstadoMaestroV3) -> dict:
    """Supervisor arbitro: valida la coherencia global entre grupos.
    Puede regresar contexto a grupos anteriores si detecta problemas inter-grupo.
    """
    llm = get_llm_para_agente("supervisor")
    cfg = cargar_config_agentes().get("configuracion", {})
    max_iter = int(cfg.get("max_iteraciones_supervisor", 3))
    iteraciones = state.get("iteraciones_supervisor", 0) + 1

    log_flujo("grupo_ecologico", "supervisor_validador", f"Auditoria global inter-grupo (iteracion {iteraciones})")
    log_agente("SUPERVISOR_VALIDADOR", f"Evaluando coherencia global del plan (iteracion {iteraciones})...", kaomoji="[x_x]")

    region = state.get("region", "")
    activar_3d_auto = cfg.get("activar_3d_automatico", False)

    prompt = (
        f"Eres el Supervisor Validador del Sistema AgriPoli (iteracion {iteraciones}/{max_iter}).\n"
        f"Region: {region}\n\n"
        "Evalua la COHERENCIA GLOBAL entre las propuestas de los cuatro grupos:\n"
        "  1. Son compatibles agronomo y ecologo entre si?\n"
        "  2. Hay suficiente contexto del Extractor?\n"
        "  3. El plan es factible para el productor?\n\n"
        "Responde en formato:\n"
        "DECISION: [COMPLETADO | REQUIERE_MAS_CONTEXTO | INCOMPATIBLE_INTER_GRUPO]\n"
        "ACTIVAR_3D: [SI | NO]\n"
        "NOTAS: [observaciones tecnicas]\n\n"
        f"--- PROPUESTAS AGRICOLAS ---\n{json.dumps(state.get('propuestas_agricolas', []), ensure_ascii=False)[:1500]}\n\n"
        f"--- PROPUESTAS ECOLOGICAS ---\n{json.dumps(state.get('propuestas_ecologicas', []), ensure_ascii=False)[:1500]}\n\n"
        f"--- CONTEXTO EXTRACTOR ---\n{state.get('contexto_extractor', '')[:800]}"
    )
    try:
        response = llm.invoke(prompt)
        texto = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as e:
        texto = "DECISION: COMPLETADO\nACTIVAR_3D: NO\nNOTAS: Error en supervisor."
        log_error(str(e), kaomoji="[X_X]")

    # Parsear decision
    decision = "COMPLETADO"
    activar_3d = activar_3d_auto
    notas = texto

    for linea in texto.split("\n"):
        linea = linea.strip()
        if linea.startswith("DECISION:"):
            decision = linea.replace("DECISION:", "").strip().upper()
        elif linea.startswith("ACTIVAR_3D:"):
            val = linea.replace("ACTIVAR_3D:", "").strip().upper()
            activar_3d = val == "SI"
        elif linea.startswith("NOTAS:"):
            notas = linea.replace("NOTAS:", "").strip()

    if iteraciones >= max_iter:
        decision = "COMPLETADO"
        log_info(f"Max iteraciones ({max_iter}) alcanzadas. Forzando COMPLETADO.", kaomoji="[x_x]")
    else:
        if decision == "COMPLETADO":
            log_ok(f"Plan integral APROBADO por el Supervisor en iteracion {iteraciones}.", kaomoji="(^_^)/")
        else:
            log_info(f"Decision: {decision}. Nota: {notas[:100]}", kaomoji="[o_o]")

    return {
        "iteraciones_supervisor": iteraciones,
        "notas_supervisor": [f"Iteracion {iteraciones}: {decision} — {notas}"],
        "activar_3d": activar_3d,
        "estado_final": decision,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODO: Grupo 3D (Opcional)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_3d_opcional(state: EstadoMaestroV3) -> dict:
    """Invoca el sub-grafo del Grupo 3D si el Supervisor lo activa."""
    region = state.get("region", "Mexico")
    log_flujo("supervisor_validador", "grupo_3d", "Activando Generador 3D Three.js")
    log_agente("GRUPO_3D", "Generando modelo 3D de la parcela y isla polinizadora...", kaomoji="(^o^)")

    grafo = crear_grafo_3d()
    estado_inicial: EstadoGrupo3D = {
        "region": region,
        "indice_degradacion_rf": state.get("indice_degradacion_rf", 0.5),
        "suelo_resumen": "",
        "propuestas_agricolas": state.get("propuestas_agricolas", []),
        "propuestas_ecologicas": state.get("propuestas_ecologicas", []),
        "resultado_mini_referencias": "",
        "referencias_fuentes": [],
        "json_threejs_final": {},
        "validacion_3d": "PENDIENTE",
        "ciclo_3d": 0,
    }
    resultado = grafo.invoke(estado_inicial)
    json_final = resultado.get("json_threejs_final", {})

    # Guardar el JSON en disco
    if json_final:
        output_path = os.path.join(
            os.path.dirname(__file__), "..", "data",
            f"mapa3d_{region.replace(' ', '_').lower()}.json"
        )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(json_final, f, ensure_ascii=False, indent=2)
            log_ok(f"JSON 3D guardado en: {output_path}", kaomoji="(^o^)")
        except Exception as e:
            log_error(f"Error guardando JSON 3D: {e}", kaomoji="[X_X]")

    return {"json_threejs_final": json_final, "estado_final": "COMPLETADO"}


# ─────────────────────────────────────────────────────────────────────────────
# NODO: Agente Sintetizador (Resumen Ejecutivo y Diagnostico Integral)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_sintetizador(state: EstadoMaestroV3) -> dict:
    """Sintetiza la investigacion de los tres grupos (Extractor, Agronomo, Ecologico)
    y la evaluacion del Supervisor en un Resumen Ejecutivo estructurado de alto valor.
    """
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("agente_sintetizador")

    log_flujo("supervisor_validador", "agente_sintetizador", "Generando diagnostico integral y resumen ejecutivo")
    log_agente("AGENTE_SINTETIZADOR", f"Sintetizando hallazgos de extraccion, agronomia y ecologia para '{region}'...", kaomoji="(^-^)")

    contexto_extr = state.get("contexto_extractor", "")
    prop_agro = state.get("propuestas_agricolas", [])
    prop_eco = state.get("propuestas_ecologicas", [])
    notas_sup = state.get("notas_supervisor", [])

    # Consolidar todas las fuentes conocidas y extraer URLs en los textos
    fuentes_acumuladas = list(state.get("referencias_fuentes", []))
    texto_total = f"{contexto_extr}\n{str(prop_agro)}\n{str(prop_eco)}\n{str(notas_sup)}"
    urls_encontradas = re.findall(r'https?://[^\s)\]>"\']+', texto_total)
    todas_fuentes = []
    vistos = set()
    for f in fuentes_acumuladas + urls_encontradas:
        f_limpia = f.rstrip(".,;:)")
        if f_limpia and f_limpia not in vistos and len(f_limpia) > 10:
            vistos.add(f_limpia)
            todas_fuentes.append(f_limpia)

    prompt = (
        f"Eres el Agente Sintetizador y Director Cientifico del Sistema Multiagente AgriPoli V3.\n"
        f"Tu mision es formular el DIAGNOSTICO AGROECOLOGICO INTEGRAL Y RESUMEN EJECUTIVO para la region: '{region}'.\n"
        "Transforma la informacion recopilada por los grupos Extractor, Agronomo y Ecologico en un reporte tecnico de alto impacto,\n"
        "exhaustivo, estructurado y directamente accionable para el productor, tecnico o investigador.\n\n"
        "ESTRUCTURA OBLIGATORIA DEL REPORTE (utiliza Markdown formal con titulos, tablas y listas detalladas):\n\n"
        f"# DIAGNOSTICO AGROECOLOGICO INTEGRAL: {region.upper()}\n"
        "**Sistema de Apoyo Multiagente AgriPoli V3**\n\n"
        "## 1. RESUMEN EJECUTIVO Y PERFIL REGIONAL\n"
        "- Sintesis global de la region, caracteristicas agroecologicas clave y viabilidad integral del proyecto.\n\n"
        "## 2. CONDICIONES CLIMATICAS Y AGROCLIMATOLOGIA\n"
        "- Temperatura media anual, maximas y minimas de la region.\n"
        "- Precipitacion anual acumulada (mm) y regimen estacional (meses secos vs. lluvias torrenciales).\n"
        "- Clasificacion climatica de Köppen especifica para la region (ej. Aw cálido subhúmedo, etc.).\n"
        "- Vientos dominantes, brisa termica y su influencia en la floracion, evaporacion y retencion de humedad.\n\n"
        "## 3. PROPIEDADES, SALUD Y MANEJO DEL SUELO\n"
        "- Tipos de suelo edafologicos dominantes (segun cartas INEGI / CONABIO: ej. Cambisoles, Regosoles, Vertisoles).\n"
        "- Textura superficial y profunda (arenosa, franca, arcillosa), rango de pH estimado y materia organica.\n"
        "- Fertilidad natural, capacidad de retencion hidrica y riesgos de degradacion (erosion hidrica o salinidad).\n"
        "- Enmiendas organicas recomendadas, biofertilizantes y practicas de recuperacion de acuerdo con NOM-021-SEMARNAT.\n\n"
        "## 4. CULTIVOS COMUNES Y PROPUESTAS AGRICOLAS REGENERATIVAS\n"
        "- Cultivos anuales y tradicionales mas viables para la zona.\n"
        "- Arboles frutales y especies perennes de la region (ej. mango, papaya, coco, citricos, guanabana).\n"
        "- Arreglo espacial de siembra: intercalado, curvas a nivel, franjas o sistemas agroforestales (MIAF). Explica las ventajas de la siembra asociada y por que ciertas especies no deben mezclarse en floracion/maduracion.\n"
        "- Secuencia de Rotacion Regenerativa en 4 Grupos Funcionales:\n"
        "  * Grupo 1 (Fijadoras de N): Leguminosas adaptadas para enriquecer el suelo.\n"
        "  * Grupo 2 (Descompactadoras): Raices pivotantes profundas para oxigenacion edafica.\n"
        "  * Grupo 3 (Control Fitosanitario/Alelopaticas): Biofumigantes y reductoras de nematodos/plagas.\n"
        "  * Grupo 4 (Eficiencia Hidrica y Cobertura): Cultivos de densa cobertura y bajo consumo de agua.\n\n"
        "## 5. FLORA NATIVA Y ESPECIES ADAPTADAS\n"
        "- Especies arboreas, arbustivas y herbaceas autoctonas de la zona.\n"
        "- Especies con estatus prioritario o de conservacion de acuerdo con la NOM-059-SEMARNAT-2010.\n"
        "- Rol bioclimatico de la vegetacion nativa frente al calor y sequia.\n\n"
        "## 6. POLINIZADORES NATIVOS Y FAUNA BENEFICA\n"
        "- Especies clave de polinizadores: abejas meliponas y trigoninas nativas sin aguijon, abejorros, mariposas, colibries y murcielagos nectarivoros.\n"
        "- Factores de anidacion y disponibilidad de polen/nectar.\n\n"
        "## 7. DISENO ECOSISTEMICO Y CONTROL BIOLOGICO\n"
        "- Diseno de islas polinizadoras y bandas florales continuas en la parcela.\n"
        "- Estrategia de control biologico por conservacion: insectos depredadores (crisopas, mariquitas/coccinelidos) y parasitoides contra plagas comunes.\n"
        "- Plantas trampa y repelentes perimetrales.\n"
        "- Manejo del factor viento: barreras rompevientos para evitar la perdida de polen y favorecer el cuajado y maduracion de frutos.\n\n"
        "## 8. FUENTES OFICIALES, INSTITUCIONES Y TRAZABILIDAD DOCUMENTAL\n"
        "- Listado de instituciones consultadas (SADER, INIFAP, CONABIO, INEGI, CIMMYT, SciELO, UNAM).\n"
        "- Normativas tecnicas aplicadas (NOM-021-SEMARNAT, NOM-059-SEMARNAT).\n"
        "- Directorio de enlaces y fuentes web recuperadas durante la investigacion (enumera las URLs directas encontradas).\n\n"
        f"--- CONTEXTO DEL GRUPO EXTRACTOR ---\n{contexto_extr[:2000]}\n\n"
        f"--- PROPUESTAS AGRICOLAS DEL AGRONOMO ---\n{json.dumps(prop_agro, ensure_ascii=False)[:2500]}\n\n"
        f"--- PROPUESTAS ECOLOGICAS DEL ECOLOGO ---\n{json.dumps(prop_eco, ensure_ascii=False)[:2500]}\n\n"
        f"--- EVALUACION DEL SUPERVISOR ---\n{json.dumps(notas_sup, ensure_ascii=False)[:800]}\n\n"
        f"--- ENLACES Y FUENTES RECOPILADAS ---\n" + "\n".join(f"- {u}" for u in todas_fuentes[:25])
    )

    try:
        response = llm.invoke(prompt)
        resumen_texto = extraer_texto_mensaje(response.content)
    except Exception as e:
        log_error(f"Error generando sintesis en agente_sintetizador: {e}", kaomoji="[X_X]")
        resumen_texto = f"# DIAGNOSTICO: {region}\n\nError al generar resumen ejecutivo: {e}"

    dossier = {
        "region": region,
        "fecha": datetime.datetime.now().isoformat(),
        "total_fuentes": len(todas_fuentes),
        "fuentes": todas_fuentes,
        "iteraciones_supervisor": state.get("iteraciones_supervisor", 1),
    }

    log_ok(f"Diagnostico y Resumen Ejecutivo completado para '{region}' ({len(resumen_texto)} caracteres).", kaomoji="(^_^)/")

    return {
        "resumen_ejecutivo": resumen_texto,
        "dossier_tecnico": dossier,
        "referencias_fuentes": todas_fuentes,
        "estado_final": "COMPLETADO",
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROUTERS DEL GRAFO MAESTRO
# ─────────────────────────────────────────────────────────────────────────────

def router_supervisor(state: EstadoMaestroV3) -> str:
    decision = state.get("estado_final", "COMPLETADO")

    if decision == "REQUIERE_MAS_CONTEXTO":
        log_flujo("supervisor", "grupo_extractor", "Re-invocando Extractor: se necesita mas contexto")
        return "Re-Extractor"
    if decision == "INCOMPATIBLE_INTER_GRUPO":
        log_flujo("supervisor", "grupo_agronomo", "Incompatibilidad inter-grupo: reprocessando Agronomo")
        return "Re-Agronomo"

    log_flujo("supervisor_validador", "agente_sintetizador", "Plan aprobado -> invocando Agente Sintetizador")
    return "Sintetizar"


def router_sintetizador(state: EstadoMaestroV3) -> str:
    activar = state.get("activar_3d", False)
    if activar:
        log_flujo("agente_sintetizador", "grupo_3d", "Activando Generador 3D opcional tras sintesis")
        return "Activar 3D"
    log_flujo("agente_sintetizador", "END", "Sintesis finalizada -> Fin del Enjambre V3")
    return "Fin"


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCCION DEL GRAFO MAESTRO
# ─────────────────────────────────────────────────────────────────────────────

def crear_grafo_v3(provider: str = "Gemini"):
    """Compila el Grafo Maestro V3 con MemorySaver."""
    workflow = StateGraph(EstadoMaestroV3)

    workflow.add_node("grupo_extractor",        nodo_extractor)
    workflow.add_node("grupo_agronomo",         nodo_agronomo)
    workflow.add_node("grupo_ecologico",        nodo_ecologico)
    workflow.add_node("supervisor_validador",   nodo_supervisor_validador)
    workflow.add_node("agente_sintetizador",    nodo_sintetizador)
    workflow.add_node("grupo_3d",              nodo_3d_opcional)

    # Flujo principal
    workflow.add_edge(START,                "grupo_extractor")
    workflow.add_edge("grupo_extractor",    "grupo_agronomo")
    workflow.add_edge("grupo_agronomo",     "grupo_ecologico")
    workflow.add_edge("grupo_ecologico",    "supervisor_validador")

    # Loops inter-grupo y derivacion a sintesis
    workflow.add_conditional_edges("supervisor_validador", router_supervisor, {
        "Re-Extractor": "grupo_extractor",     # Loop: falta contexto
        "Re-Agronomo":  "grupo_agronomo",      # Loop: incompatibilidad inter-grupo
        "Sintetizar":   "agente_sintetizador", # Plan aprobado -> Sintesis
    })

    # Bifurcacion 3D o Fin tras el Agente Sintetizador
    workflow.add_conditional_edges("agente_sintetizador", router_sintetizador, {
        "Activar 3D":   "grupo_3d",            # Opcional: generar modelo 3D
        "Fin":          END,                   # Plan completado sin 3D
    })
    workflow.add_edge("grupo_3d", END)

    memory = MemorySaver()
    return workflow.compile(checkpointer=memory)


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIONES DE EJECUCION PUBLICA
# ─────────────────────────────────────────────────────────────────────────────

def run_enjambre_v3(
    region: str,
    indice_degradacion_rf: float = 0.5,
    historial_siembra: list[str] | None = None,
    thread_id: str = "default",
    flow_type: Literal["Hibrido", "Solo Local", "Solo Web"] = "Hibrido",
    activar_3d: bool = False,
) -> dict:
    """Ejecuta el Enjambre Jerarquico V3 de forma sincrona.

    Args:
        region:                Nombre de la region a analizar.
        indice_degradacion_rf: Indice del modelo Random Forest (0-1).
        historial_siembra:     Cultivos anteriores del productor.
        thread_id:             ID de sesion para MemorySaver.
        flow_type:             Modo de investigacion del Extractor.
        activar_3d:            Si True, genera el modelo Three.js al final.

    Returns:
        Estado final del grafo con propuestas, notas y JSON 3D.
    """
    cfg = cargar_config_agentes().get("configuracion", {})
    grafo = crear_grafo_v3()
    estado_inicial: EstadoMaestroV3 = {
        "region": region,
        "indice_degradacion_rf": indice_degradacion_rf,
        "historial_siembra": historial_siembra or [],
        "mensajes": [],
        "contexto_extractor": "",
        "propuestas_agricolas": [],
        "propuestas_ecologicas": [],
        "json_threejs_final": {},
        "activar_3d": activar_3d or bool(cfg.get("activar_3d_automatico", False)),
        "notas_supervisor": [],
        "iteraciones_supervisor": 0,
        "estado_final": "PENDIENTE",
        "resumen_ejecutivo": "",
        "dossier_tecnico": {},
        "referencias_fuentes": [],
        "flow_type": flow_type,
        "max_ciclos": int(cfg.get("max_ciclos_retroalimentacion", 3)),
    }
    config = {"configurable": {"thread_id": thread_id}}
    return grafo.invoke(estado_inicial, config=config)


def run_enjambre_v3_stream(
    region: str,
    indice_degradacion_rf: float = 0.5,
    historial_siembra: list[str] | None = None,
    thread_id: str = "default",
    flow_type: Literal["Hibrido", "Solo Local", "Solo Web"] = "Hibrido",
    activar_3d: bool = False,
):
    """Ejecuta el Enjambre V3 con streaming de eventos.
    Yields cada evento del grafo para visualizacion en tiempo real.
    """
    cfg = cargar_config_agentes().get("configuracion", {})
    grafo = crear_grafo_v3()
    estado_inicial: EstadoMaestroV3 = {
        "region": region,
        "indice_degradacion_rf": indice_degradacion_rf,
        "historial_siembra": historial_siembra or [],
        "mensajes": [],
        "contexto_extractor": "",
        "propuestas_agricolas": [],
        "propuestas_ecologicas": [],
        "json_threejs_final": {},
        "activar_3d": activar_3d or bool(cfg.get("activar_3d_automatico", False)),
        "notas_supervisor": [],
        "iteraciones_supervisor": 0,
        "estado_final": "PENDIENTE",
        "resumen_ejecutivo": "",
        "dossier_tecnico": {},
        "referencias_fuentes": [],
        "flow_type": flow_type,
        "max_ciclos": int(cfg.get("max_ciclos_retroalimentacion", 3)),
    }
    config = {"configurable": {"thread_id": thread_id}}
    for event in grafo.stream(estado_inicial, config=config):
        yield event

