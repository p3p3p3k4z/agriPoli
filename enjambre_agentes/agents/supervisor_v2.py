"""
Supervisor Maestro V2 del Sistema de Apoyo Multiagente AgriPoli.

Extiende el Supervisor V1 (agents/supervisor.py) con herramientas
que invocan el Grafo Maestro V3 y los sub-grafos de cada grupo.

El V1 se preserva intacto.
"""
from __future__ import annotations

import os
import json
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

import config.silenciador
from config.models import get_llm_para_agente, cargar_config_agentes
from config.agri_logger import log_agente, log_mini_agente, log_flujo, log_ok, log_info, log_error
from tools.catalogo_biodiversidad import consultar_catalogo_biodiversidad_local


# ─────────────────────────────────────────────────────────────────────────────
# HERRAMIENTAS DEL SUPERVISOR MAESTRO V2
# ─────────────────────────────────────────────────────────────────────────────

@tool
def ejecutar_enjambre_v3(
    region: str,
    indice_degradacion: float = 0.5,
    cultivos_previos: str = "",
    flow_type: str = "Hibrido",
    activar_3d: bool = False,
) -> str:
    """Ejecuta el flujo completo del Enjambre Jerarquico V3 de AgriPoli.

    Orquesta los cuatro grupos de agentes en secuencia:
      1. Grupo Extractor (informacion fresca: web, academica, gubernamental)
      2. Grupo Agronomo (propuestas de cultivos y suelo con loop de retroalimentacion)
      3. Grupo Ecologico (diseno de isla polinizadora con loop de retroalimentacion)
      4. Supervisor Validador (coherencia global, loops inter-grupo)
      5. Grupo 3D (opcional, si activar_3d=True)

    Usalo cuando el usuario solicite un diagnostico formal, plan de rotacion
    completo o la generacion de un modelo 3D para su region.

    Args:
        region:             Nombre de la region o municipio a analizar.
        indice_degradacion: Indice de degradacion del suelo (0.0 a 1.0).
        cultivos_previos:   Lista de cultivos anteriores separados por coma.
        flow_type:          Modo de investigacion: 'Hibrido', 'Solo Local', 'Solo Web'.
        activar_3d:         Si True, genera el modelo Three.js al final.
    """
    try:
        from agents.graph_v3 import run_enjambre_v3
        log_flujo("supervisor", "enjambre_v3", "Iniciando flujo completo V3 de 4 grupos", kaomoji="[>_<]")
        log_agente("ENJAMBRE_V3", f"Orquestando Extractor -> Agronomo -> Ecologico -> Supervisor_Validador{' -> 3D' if activar_3d else ''} para '{region}'...", kaomoji="[>_<]")
        historial = [c.strip() for c in cultivos_previos.split(",") if c.strip()]
        res = run_enjambre_v3(
            region=region,
            indice_degradacion_rf=indice_degradacion,
            historial_siembra=historial,
            flow_type=flow_type,
            activar_3d=activar_3d,
        )
        n_agro = len(res.get("propuestas_agricolas", []))
        n_eco  = len(res.get("propuestas_ecologicas", []))
        tiene_3d = bool(res.get("json_threejs_final"))
        notas = "; ".join(res.get("notas_supervisor", [])[-2:])
        log_flujo("enjambre_v3", "supervisor", "Enjambre completado", kaomoji="(^o^)/")
        return (
            f"(^o^)/ [ENJAMBRE V3 COMPLETADO]\n"
            f"  Region analizada: {region}\n"
            f"  Propuestas agricolas generadas: {n_agro}\n"
            f"  Propuestas ecologicas generadas: {n_eco}\n"
            f"  Modelo 3D generado: {'SI' if tiene_3d else 'NO'}\n"
            f"  Notas del Supervisor: {notas or 'Sin observaciones.'}"
        )
    except Exception as e:
        return f"[X_X] [ERROR: ENJAMBRE_V3] {e}"


@tool
def delegar_solo_extractor(region: str = "Mexico", flow_type: str = "Hibrido", consulta: str = "") -> str:
    """Invoca unicamente el Grupo Extractor (4 mini-agentes en paralelo + fusionador).

    Usa esto cuando el usuario pregunta por clima, biodiversidad, suelo o datos
    generales de una region y sus fuentes oficiales.

    Args:
        region:    Nombre de la region o municipio (defecto 'Mexico').
        flow_type: 'Hibrido', 'Solo Local' o 'Solo Web'.
        consulta:  Peticion original o tema especifico a consultar (opcional).
    """
    try:
        from agents.groups.group_extractor import crear_grafo_extractor
        log_flujo("supervisor", "grupo_extractor", "Delegando extraccion de informacion regional y fuentes", kaomoji="[>_<]")
        log_agente("GRUPO_EXTRACTOR", f"Iniciando 4 mini-agentes para '{region}' en modo {flow_type}...", kaomoji="[>_<]")
        grafo = crear_grafo_extractor()
        resultado = grafo.invoke({
            "consulta_original": consulta or f"estudio de suelo, clima y vegetacion en {region}",
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
        })
        contexto = resultado.get("contexto_web", "Sin datos disponibles.")
        fuentes = resultado.get("referencias_fuentes", []) or resultado.get("fuentes_web", [])
        log_flujo("grupo_extractor", "supervisor", "Contexto regional y fuentes listos", kaomoji="(^-^)/")
        log_ok(f"Grupo Extractor completo para '{region}'.", kaomoji="[>_<]")
        
        bloque_fuentes = ""
        if fuentes:
            bloque_fuentes = "\n\n[FUENTES Y REFERENCIAS: GRUPO EXTRACTOR]:\n" + "\n".join(f"- {u}" for u in fuentes[:6])

        return (
            f"(^-^) [EXTRACTOR COMPLETADO] Region: {region}\n\n"
            f"{contexto[:3000]}"
            f"{bloque_fuentes}"
        )
    except Exception as e:
        return f"[X_X] [ERROR: EXTRACTOR] {e}"


@tool
def delegar_solo_agronomo(region: str = "Mexico", contexto: str = "", indice_degradacion: float = 0.5, consulta: str = "") -> str:
    """Invoca al Grupo Agronomo (7 mini-agentes en paralelo + fusionador).

    OBLIGATORIO: Invoca esta herramienta cuando el usuario pregunte por cultivos,
    listados de grupos de cultivos en Mexico, parcelas, rotaciones regenerativas,
    compatibilidad, analisis agronomico de suelo o referencias agronomicas.

    Args:
        region:             Nombre de la region o estado/pais (defecto 'Mexico').
        contexto:           Contexto previo o detalles de la solicitud (opcional).
        indice_degradacion: Indice de degradacion del suelo (0.0 a 1.0).
        consulta:           Peticion original o tema especifico del usuario (opcional).
    """
    try:
        from agents.groups.group_agronomo import crear_grafo_agronomo
        log_flujo("supervisor", "grupo_agronomo", "Delegando analisis agronomico y busqueda de antecedentes", kaomoji="[>_<]")

        # Consultar Tavily para enriquecer con antecedentes reales de cultivos en Mexico si falta contexto
        if not contexto:
            try:
                from tools.search import buscar_antecedentes_cultivo
                ctx_tavily = buscar_antecedentes_cultivo.invoke({"consulta": consulta or f"asociacion cultivos antecedentes rendimiento suelo {region}"})
                contexto = f"[ANTECEDENTES TAVILY EN VIVO]\n{ctx_tavily[:1500]}"
            except Exception:
                pass

        log_agente(
            "GRUPO_AGRONOMO",
            f"Iniciando 7 mini-agentes en paralelo para '{region}' "
            f"(suelo, cultivo, SIAP, INEGI, calculadora, rotacion_regenerativa, referencias)...",
            kaomoji="(-w-)/",
        )
        grafo = crear_grafo_agronomo()
        resultado = grafo.invoke({
            "consulta_original": consulta or contexto or f"asociacion de cultivos y rotacion regenerativa en {region}",
            "region": region,
            "contexto_extractor": contexto,
            "contexto_rag_agro": "",
            "indice_degradacion_rf": indice_degradacion,
            "historial_siembra": [],
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
        })
        propuestas = resultado.get("propuestas_agricolas", [])
        ciclos = resultado.get("ciclo_agronomo", 0)
        texto = propuestas[0].get("texto", "Sin propuesta.") if propuestas else "Sin propuesta generada."
        fuentes = resultado.get("referencias_fuentes", [])
        log_flujo("grupo_agronomo", "supervisor", f"Plan agronomico y referencias listas (ciclos={ciclos})", kaomoji="(^-^)/")
        
        bloque_fuentes = ""
        if fuentes:
            bloque_fuentes = "\n\n[FUENTES Y REFERENCIAS: GRUPO AGRONOMO]:\n" + "\n".join(f"- {u}" for u in fuentes[:6])

        return (
            f"(-w-)/ [AGRONOMO COMPLETADO] Region: {region} | Ciclos de retroalimentacion: {ciclos}\n\n"
            f"{texto[:3000]}"
            f"{bloque_fuentes}"
        )
    except Exception as e:
        return f"[X_X] [ERROR: AGRONOMO] {e}"


@tool
def delegar_solo_ecologico(region: str = "Mexico", propuestas_agricolas_json: str = "", consulta: str = "") -> str:
    """Invoca unicamente el Grupo Ecologico (7 mini-agentes en paralelo + fusionador).

    Usa esto cuando el usuario pregunta sobre flora nativa, polinizadores,
    control biologico de plagas, conservacion biologica o fuentes agroecologicas.

    Args:
        region:                     Nombre de la region o municipio (defecto 'Mexico').
        propuestas_agricolas_json:  JSON string de propuestas del Agronomo (opcional).
        consulta:                   Peticion original o especie/plaga a consultar (opcional).
    """
    try:
        from agents.groups.group_ecologico import crear_grafo_ecologico
        propuestas = json.loads(propuestas_agricolas_json) if propuestas_agricolas_json else []
        log_flujo("supervisor", "grupo_ecologico", "Delegando diseno agroecologico y fuentes de biodiversidad", kaomoji="[>_<]")
        log_agente(
            "GRUPO_ECOLOGICO",
            f"Iniciando 7 mini-agentes en paralelo para '{region}' "
            f"(flora_nativa, polinizadores, catalogo, GBIF, control_biologico, atractores, referencias)...",
            kaomoji="(*-*)",
        )
        grafo = crear_grafo_ecologico()
        resultado = grafo.invoke({
            "consulta_original": consulta or f"islas polinizadoras, flora nativa y control biologico en {region}",
            "region": region,
            "contexto_extractor": "",
            "propuestas_agricolas": propuestas,
            "contexto_rag_eco": "",
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
        })
        propuestas_eco = resultado.get("propuestas_ecologicas", [])
        ciclos = resultado.get("ciclo_ecologico", 0)
        texto = propuestas_eco[0].get("texto", "Sin propuesta.") if propuestas_eco else "Sin propuesta generada."
        fuentes = resultado.get("referencias_fuentes", [])
        log_flujo("grupo_ecologico", "supervisor", f"Diseno agroecologico y fuentes listos (ciclos={ciclos})", kaomoji="(^-^)/")

        bloque_fuentes = ""
        if fuentes:
            bloque_fuentes = "\n\n[FUENTES Y REFERENCIAS: GRUPO ECOLOGICO]:\n" + "\n".join(f"- {u}" for u in fuentes[:6])

        return (
            f"(*_*)! [ECOLOGICO COMPLETADO] Region: {region} | Ciclos de retroalimentacion: {ciclos}\n\n"
            f"{texto[:3000]}"
            f"{bloque_fuentes}"
        )
    except Exception as e:
        return f"[X_X] [ERROR: ECOLOGICO] {e}"


@tool
def consultar_conocimiento_rag(consulta: str, categoria: str = "general") -> str:
    """Consulta la base de conocimientos RAG local en una categoria especifica.
    Categorias: 'suelo', 'agricultura', 'polinizadores', 'general'.
    Usa esto cuando el usuario pregunta por tecnicas agricolas o ecologicas especificas.
    """
    from tools.rag_engine import consultar
    return consultar(query=consulta, collection_name=categoria, provider="Gemini", db_type="FAISS")


@tool
def buscar_biodiversidad_local(consulta: str) -> str:
    """Consulta el catalogo local de biodiversidad mexicana (3,900+ especies).
    Busca plantas meliferas, polinizadores nativos, abejas nativas y flora endemica.
    Usa esto cuando el usuario pregunta por especies especificas de Mexico.
    """
    return consultar_catalogo_biodiversidad_local.invoke({"consulta": consulta})


@tool
def buscar_web_tavily(consulta: str, tema: str = "agricultura") -> str:
    """Busca informacion en vivo en la web mediante Tavily Search API con filtro en fuentes oficiales mexicanas.
    Filtra por sitios de SADER, INIFAP, CONABIO, SciELO Mexico, INEGI y UNAM.
    Usa esto para verificar antecedentes actuales, cultivos viables, plagas o citas bibliograficas.

    Args:
        consulta: Consulta de busqueda (ej. 'antecedentes asociacion cultivos maiz frijol calabaza mexico').
        tema: 'agricultura', 'polinizadores', 'flora', 'suelo', 'clima', o 'general'.
    """
    from tools.search import buscar_tavily_mexico
    return buscar_tavily_mexico.invoke({"query": consulta, "tema": tema})


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCTOR DEL SUPERVISOR V2
# ─────────────────────────────────────────────────────────────────────────────

def crear_supervisor_v2(provider: str = "Gemini"):
    """Crea el Agente Supervisor Maestro V2.

    Usa config/agentes.yaml para determinar el modelo LLM del supervisor.
    El provider pasado como argumento es solo un fallback si el YAML no existe.
    """
    llm = get_llm_para_agente("supervisor")

    tools = [
        ejecutar_enjambre_v3,
        delegar_solo_extractor,
        delegar_solo_agronomo,
        delegar_solo_ecologico,
        buscar_web_tavily,
        consultar_conocimiento_rag,
        buscar_biodiversidad_local,
    ]

    system_prompt = (
        "Eres el Supervisor Maestro V2 del Sistema Multiagente AgriPoli "
        "(Manejo Agricola y Preservacion de Polinizadores Nativos en Mexico).\n\n"
        "PERSONALIDAD: Eres sereno, tecnico, cercano y altamente resolutivo. "
        "Combinas la experiencia de un agronomo y ecologo con la calidez de un asesor de confianza. "
        "Tus kaomojis caracteristicos para tus intervenciones son:\n"
        "  (^-^)/ [BIENVENIDA] al saludar\n"
        "  (o.O)? [INDAGACION] si requieres mas datos del usuario\n"
        "  (u_u) [PROPUESTA] al presentar recomendaciones tecnicas\n"
        "  (*-*)! [HALLAZGO] para hallazgos o descubrimientos\n"
        "  (^o^)/ [COMPLETADO] al entregar conclusiones finales\n\n"
        "REGLAS CRITICAS DE EJECUCION DE HERRAMIENTAS:\n"
        "1. PROHIBICION DE TEXTO DE ESPERA: NUNCA emitas mensajes de texto preliminares "
        "diciendo que estas procesando, calculando o consultando la base de datos "
        "(PROHIBIDO emitir '(-.-)zzz [PROCESANDO]' o mensajes similares como texto). "
        "SIEMPRE DEBES INVOCAR LA HERRAMIENTA ADECUADA DIRECTAMENTE EN TU PRIMERA RESPUESTA.\n"
        "2. ASIGNACION OBLIGATORIA DE HERRAMIENTAS:\n"
        "   - Cultivos, listados de grupos de cultivos en Mexico, parcelas, hortalizas, frutas, rotacion regenerativa o suelo -> "
        "DEBES INVOCAR OBLIGATORIAMENTE 'delegar_solo_agronomo(region=...)'. Si el usuario no especifico municipio, usa region='Mexico'.\n"
        "   - Investigacion web fresca, antecedentes en vivo o fuentes actualizadas -> "
        "DEBES INVOCAR 'buscar_web_tavily(consulta=..., tema='agricultura')'.\n"
        "   - Flora nativa, abejas nativas, polinizadores o islas de conservacion -> "
        "DEBES INVOCAR 'delegar_solo_ecologico(region=...)'.\n"
        "   - Clima, datos web o geografia regional fresca -> "
        "DEBES INVOCAR 'delegar_solo_extractor(region=...)'.\n"
        "   - Diagnostico integral o modelo 3D -> "
        "DEBES INVOCAR 'ejecutar_enjambre_v3(region=...)'.\n"
        "   - Consulta de tecnicas especificas o manuales -> "
        "DEBES INVOCAR 'consultar_conocimiento_rag(consulta=..., categoria='agricultura')'.\n"
        "   - Catalogo de especies mexicanas -> "
        "DEBES INVOCAR 'buscar_biodiversidad_local(consulta=...)'.\n\n"
        "3. TRAZABILIDAD Y REFERENCIAS OBLIGATORIAS:\n"
        "   - En TODA respuesta tecnica donde recomiendes cultivos, rotaciones o polinizadores, DEBES incluir al final una seccion obligatoria de fuentes:\n"
        "     [REFERENCIAS Y ANTECEDENTES DOCUMENTADOS]\n"
        "     * Instituciones citadas (INIFAP, SADER, SIAP, CONABIO, CIMMYT, Chapingo, UNAM).\n"
        "     * Normas oficiales aplicables (ej. NOM-021-SEMARNAT-2000 para analisis edafologico, NOM-059 para conservacion).\n"
        "     * Manuales y articulos cientificos recuperados via Tavily Search (con sus URLs correspondientes).\n\n"
        "REGLAS DE FORMATO DE RESPUESTA FINAL:\n"
        "- SOLO kaomojis ASCII y etiquetas formales en MAYUSCULAS. PROHIBIDOS emojis unicode graficos.\n"
        "- Sin caracteres especiales decorativos (no *, no #, no ---, no ===).\n"
        "- Usa separadores de texto plano con lineas simples o espacios.\n"
        "- Respuestas CONCISAS y estructuradas: enumera con claridad los grupos de cultivos viables en Mexico, sus antecedentes y beneficios.\n"
        "- Al concluir, ofrece amablemente al usuario profundizar en algun grupo o modelar su parcela en 3D."
    )

    return create_react_agent(llm, tools=tools, prompt=system_prompt)
