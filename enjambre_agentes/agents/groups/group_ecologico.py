"""
Grupo Ecologico — Sub-grafo LangGraph del Sistema Multiagente AgriPoli V3.

Responsabilidad: Disenar islas polinizadoras, control biologico de plagas
y matrices de conservacion con enfoque agroecologico.

Mini-agentes paralelos:
  * mini_flora_nativa          — Flora endemica y nativa por clima Koppen
  * mini_polinizadores         — Catalogo local (1,188 plantas + 2,734 polinizadores)
  * mini_catalogo_local        — Busqueda por especie en descargas masivas SNIB/EncicloVida
  * mini_gbif                  — Taxonomia y distribucion GBIF (API global)
  * mini_control_biologico     — Insectos y plantas depredadoras de plagas (agroecologia)
                                 Ejemplo: catarinas (Coccinellidae) vs pulgones (Aphididae)
  * mini_atractores_polinizadores — Plantas que atraen polinizadores beneficiosos

Fusionador interno con LOOP de retroalimentacion:
  * fusionador_ecologico — Verifica compatibilidad con cultivos del Agronomo
                           y con el clima local. Regresa a mini_flora si hay
                           incompatibilidades.
"""
from __future__ import annotations

import json
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

import config.silenciador
from config.models import get_llm_para_agente, cargar_config_agentes
from config.agri_logger import log_agente, log_mini_agente, log_flujo, log_ok, log_info, log_error
from agents.state_v3 import EstadoGrupoEcologico


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 1: Flora Nativa y Endemica
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_flora_nativa(state: EstadoGrupoEcologico) -> dict:
    """Fork A: Busqueda de flora nativa adaptada al clima Koppen de la region.
    Si hay anotacion del fusionador, reselecciona con las restricciones indicadas.
    """
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_flora_nativa")
    ciclo = state.get("ciclo_ecologico", 0)
    anotacion = state.get("anotacion_fusionador_eco", "")

    if anotacion and ciclo > 0:
        log_mini_agente(
            "MINI_FLORA_NATIVA",
            f"Ciclo {ciclo}: Reseleccionando flora con restricciones del Fusionador...",
            kaomoji="(*_*)",
        )
    else:
        log_mini_agente("MINI_FLORA_NATIVA", f"Buscando flora nativa para '{region}'...", kaomoji="(*-*)")

    from agents.ecologico import crear_agente_ecologico
    agente = crear_agente_ecologico(provider="Gemini")

    nota_correccion = (
        f"\n\n[CORRECCION DEL FUSIONADOR - Ciclo {ciclo}]:\n{anotacion}"
        if anotacion else ""
    )
    prompt = (
        f"Diseña una propuesta de flora nativa para la region: {region}.\n"
        f"Los cultivos propuestos por el Agronomo son: "
        f"{json.dumps(state.get('propuestas_agricolas', []))[:1000]}\n"
        f"Contexto ecologico disponible:\n{state.get('contexto_extractor', '')[:1500]}"
        f"{nota_correccion}"
    )
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=prompt)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_flora_nativa] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_FLORA_NATIVA", "Propuesta de flora nativa generada.", kaomoji="(*-*)")
    return {"resultado_mini_flora": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 2: Catalogo de Polinizadores
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_polinizadores(state: EstadoGrupoEcologico) -> dict:
    """Fork B: Consulta el catalogo local de 3,922+ especies de flora y polinizadores."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_polinizadores")
    log_mini_agente("MINI_POLINIZADORES", f"Consultando catalogo local de polinizadores para '{region}'...", kaomoji="(^w^)")

    from tools.catalogo_biodiversidad import consultar_catalogo_biodiversidad_local
    # Extraer terminos clave de las propuestas agricolas para buscar polinizadores relacionados
    propuestas = json.dumps(state.get("propuestas_agricolas", []))

    agente = create_react_agent(
        model=llm,
        tools=[consultar_catalogo_biodiversidad_local],
        prompt=(
            "Eres el Mini-Agente de Polinizadores del Grupo Ecologico de AgriPoli. "
            "Usa el catalogo local de biodiversidad mexicana para encontrar polinizadores "
            "y flora melifera nativos de Mexico relevantes para la region y los cultivos propuestos. "
            "Incluye abejas nativas, meliponas, abejorros, mariposas y colibries."
        ),
    )
    consulta = f"polinizadores nativos y flora melifera para region {region} Mexico"
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_polinizadores] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_POLINIZADORES", "Catalogo de polinizadores consultado.", kaomoji="(^w^)")
    return {"resultado_mini_polinizadores": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 3: Catalogo Local SNIB/EncicloVida
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_catalogo_local(state: EstadoGrupoEcologico) -> dict:
    """Fork C: Busqueda por especie en el catalogo SNIB/EncicloVida local."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_catalogo_local")
    log_mini_agente("MINI_CATALOGO", f"Explorando catalogo SNIB/EncicloVida para '{region}'...", kaomoji="(._.)/")

    from tools.search import buscar_conabio, buscar_datos_unam
    agente = create_react_agent(
        model=llm,
        tools=[buscar_conabio, buscar_datos_unam],
        prompt=(
            "Eres el Mini-Agente de Catalogo del Grupo Ecologico de AgriPoli. "
            "Busca registros taxonomicos y de distribucion en CONABIO, EncicloVida y "
            "el Portal de Datos Abiertos de la UNAM. "
            "Encuentra especies NOM-059 y endemicas prioritarias para la region."
        ),
    )
    consulta = f"especies endemicas prioritarias flora polinizadores {region} CONABIO EncicloVida"
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_catalogo] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_CATALOGO", "Catalogo SNIB consultado.", kaomoji="(._.)/")
    return {"resultado_mini_catalogo": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 4: GBIF (Global Biodiversity Information Facility)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_gbif(state: EstadoGrupoEcologico) -> dict:
    """Fork D: Taxonomia y distribucion global de especies via API GBIF."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_gbif")
    log_mini_agente("MINI_GBIF", f"Consultando API GBIF para taxonomia en '{region}'...", kaomoji="[~_~]")

    # Intentar obtener datos taxonomicos GBIF para especies clave
    try:
        from tools.gbif_client import fetch_gbif_species
        import asyncio

        # Consultar algunas especies representativas de polinizadores mexicanos
        especies_consulta = ["Melipona beecheii", "Bombus ephippiatus", "Xylocopa mexicanorum"]
        resultados_gbif = []

        async def _consultar_gbif():
            import aiohttp
            async with aiohttp.ClientSession() as session:
                for sp in especies_consulta:
                    datos = await fetch_gbif_species(session, sp)
                    if datos:
                        resultados_gbif.append(
                            f"- {sp}: taxonKey={datos.get('usageKey', 'N/A')}, "
                            f"confianza={datos.get('confidence', 'N/A')}%, "
                            f"kingdom={datos.get('kingdom', 'N/A')}"
                        )

        try:
            asyncio.get_event_loop().run_until_complete(_consultar_gbif())
        except RuntimeError:
            asyncio.run(_consultar_gbif())

        texto = (
            f"[GBIF API] Datos taxonomicos para polinizadores relevantes en Mexico:\n"
            + "\n".join(resultados_gbif) if resultados_gbif
            else f"[GBIF API] Sin coincidencias exactas. Region: {region}"
        )
    except Exception as e:
        texto = f"[GBIF] No disponible: {e}. Continuando con datos locales."
        log_info(str(e), kaomoji="(o_o)")

    log_mini_agente("MINI_GBIF", "Datos GBIF recopilados.", kaomoji="[~_~]")
    return {"resultado_mini_gbif": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 5: Control Biologico de Plagas (Agroecologia)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_control_biologico(state: EstadoGrupoEcologico) -> dict:
    """Fork E: Control biologico de plagas mediante depredadores e insectos beneficiosos.
    Enfoque agroecologico: usa el ecosistema para controlar plagas sin quimicos.
    Ejemplo canonico: catarinas (Coccinella septempunctata) vs pulgones (Aphididae).
    """
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_control_biologico")
    propuestas = state.get("propuestas_agricolas", [])
    log_mini_agente(
        "MINI_CONTROL_BIOLOGICO",
        "Identificando insectos depredadores y plantas trampa para control biologico...",
        kaomoji="(>o<)",
    )

    from tools.search import buscar_conabio

    cultivos_texto = ""
    if propuestas:
        p = propuestas[0]
        cultivos_texto = p.get("texto", "")[:500] if isinstance(p, dict) else str(p)[:500]

    agente = create_react_agent(
        model=llm,
        tools=[buscar_conabio],
        prompt=(
            "Eres el Mini-Agente de Control Biologico del Grupo Ecologico de AgriPoli. "
            "Tu enfoque es AGROECOLOGICO: recomienda insectos depredadores, parasitoides "
            "y plantas trampa o repelentes para controlar plagas de forma natural. "
            "Ejemplos: catarinas (Coccinellidae) comen pulgones (Aphididae); "
            "crisopas (Chrysopidae) comen trips y mosca blanca; "
            "avispas parasitoides Trichogramma eliminan huevos de lepidopteros. "
            "Para plantas: caléndula repele nemátodos; albahaca repele pulgones; "
            "tagetes repele mosca blanca. "
            "Siempre indica: 1) La plaga objetivo, 2) El agente de control biologico, "
            "3) Como implementarlo en la parcela. Prioriza especies nativas de Mexico."
        ),
    )
    consulta = (
        f"Control biologico de plagas para cultivos en {region} Mexico. "
        f"Cultivos propuestos: {cultivos_texto or 'hortaliza general'}. "
        f"Recomienda insectos depredadores, plantas trampa y plantas repelentes nativas."
    )
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_control_biologico] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_CONTROL_BIOLOGICO", "Plan de control biologico formulado.", kaomoji="(>o<)")
    return {"resultado_mini_control_biologico": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 6: Atractores de Polinizadores
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_atractores_polinizadores(state: EstadoGrupoEcologico) -> dict:
    """Fork F: Plantas estrategicas que atraen y retienen polinizadores beneficiosos.
    Disenio de corredores biologicos y bandas florales para la parcela.
    """
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_atractores_polinizadores")
    propuestas = state.get("propuestas_agricolas", [])
    log_mini_agente(
        "MINI_ATRACTORES",
        "Disenando banda floral y corredores para atraer polinizadores...",
        kaomoji="(^-^)~",
    )

    from tools.search import buscar_conabio
    from tools.catalogo_biodiversidad import consultar_catalogo_biodiversidad_local

    cultivos_texto = ""
    if propuestas:
        p = propuestas[0]
        cultivos_texto = p.get("texto", "")[:500] if isinstance(p, dict) else str(p)[:500]

    agente = create_react_agent(
        model=llm,
        tools=[buscar_conabio, consultar_catalogo_biodiversidad_local],
        prompt=(
            "Eres el Mini-Agente de Atractores de Polinizadores del Grupo Ecologico de AgriPoli. "
            "Recomienda plantas que atraigan abejas nativas, meliponas, abejorros, "
            "mariposas y colibries a la parcela agricola. "
            "Tu objetivo es disenar una BANDA FLORAL o ISLA POLINIZADORA que: "
            "1) Tenga floracion escalonada durante todo el ano, "
            "2) Incluya plantas nativas de la region, "
            "3) Sea compatible con los cultivos propuestos por el Agronomo, "
            "4) Proporcione refugio y nidacion a los insectos beneficiosos. "
            "Incluye nombre comun, nombre cientifico, epoca de floracion y beneficio especifico."
        ),
    )
    consulta = (
        f"Plantas atractoras de polinizadores nativos para banda floral en {region} Mexico. "
        f"Cultivos en la parcela: {cultivos_texto or 'hortaliza general'}. "
        f"Diseniar isla polinizadora con floracion escalonada anual."
    )
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_atractores_polinizadores] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_ATRACTORES", "Diseno de isla polinizadora completado.", kaomoji="(^-^)~")
    return {"resultado_mini_atractores": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 7: Referencias y Fuentes Agroecologicas (CONABIO + NOM-059 + Tavily)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_referencias_ecologico(state: EstadoGrupoEcologico) -> dict:
    """Fork G: De la consulta original y ambito ecologico, extrae exclusivamente
    las fuentes, catalogos oficiales, normas de conservacion (NOM-059-SEMARNAT)
    y enlaces web tecnicos de biodiversidad mexicana (CONABIO, EncicloVida, GBIF, SciELO).
    """
    region = state.get("region", "Mexico")
    consulta_orig = state.get("consulta_original", "") or f"polinizadores nativos, flora nativa y biodiversidad en {region} Mexico"
    llm = get_llm_para_agente("mini_referencias_ecologico")
    log_mini_agente("MINI_REFERENCIAS_ECO", f"Extrayendo fuentes y catalogos ecologicos para '{region}'...", kaomoji="(^_~)")

    from tools.search import buscar_conabio, buscar_tavily_mexico
    import re

    agente = create_react_agent(
        model=llm,
        tools=[buscar_conabio, buscar_tavily_mexico],
        prompt=(
            "Eres el Mini-Agente de Referencias del Grupo Ecologico de AgriPoli. "
            "Tu UNICO objetivo es extraer de la consulta original las fuentes, autores, instituciones, normas y enlaces web pertinentes a la biodiversidad, conservacion y agroecologia. "
            "No inventes datos ni hagas recomendaciones generales. Solo identifica, extrae y formatea las fuentes tecnicas y oficiales: "
            "1. Cita fuentes de biodiversidad y conservacion en Mexico (CONABIO, EncicloVida, Red de Polinizadores de Mexico, INECOL, UNAM, GBIF, SciELO). "
            "2. Cita normas oficiales mexicanas aplicables (ej. NOM-059-SEMARNAT-2010 proteccion de especies en riesgo). "
            "3. Incluye las URLs reales recuperadas con tus herramientas de busqueda en sitios confiables. "
            "FORMATO ESTANDAR OBLIGATORIO: "
            "[FUENTES Y REFERENCIAS: GRUPO ECOLOGICO]\n"
            "1. [Institucion / Repositorio] Titulo o catalogo consultado | Enlace: <URL>\n"
            "2. [Norma Oficial / Catalogo] Titulo de la norma o base taxonomica | Referencia: <Cita oficial>"
        ),
    )
    consulta = (
        f"fuentes cientificas, catalogos oficiales y normas de biodiversidad, polinizadores y flora sobre: {consulta_orig} en {region} Mexico."
    )
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_referencias_ecologico] {e}"
        log_error(str(e), kaomoji="[X_X]")

    urls = re.findall(r'https?://[^\s)\]>"\']+', str(texto))
    log_mini_agente("MINI_REFERENCIAS_ECO", f"Fuentes agroecologicas extraidas ({len(urls)} enlaces).", kaomoji="(^_~)")
    return {
        "resultado_mini_referencias": texto,
        "referencias_fuentes": urls,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUSIONADOR ECOLOGICO (con LOOP de retroalimentacion)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_fusionador_ecologico(state: EstadoGrupoEcologico) -> dict:
    """Join + Arbitro: Verifica compatibilidad ecologica con cultivos del Agronomo.
    Integra resultados de 7 mini-agentes: flora, polinizadores, catalogo, gbif,
    control biologico, atractores de polinizadores y referencias ecologicas.
    Si hay especies incompatibles con el clima o los cultivos, RECHAZA y retroalimenta.
    """
    llm = get_llm_para_agente("fusionador_ecologico")
    ciclo = state.get("ciclo_ecologico", 0) + 1
    config = cargar_config_agentes().get("configuracion", {})
    max_ciclos = int(config.get("max_ciclos_retroalimentacion", 3))

    log_flujo(
        "[mini_flora|mini_poli|mini_cat|mini_gbif|mini_ctrl_bio|mini_atractores|mini_refs_eco]",
        "fusionador_ecologico",
        f"Join: auditando coherencia agroecologica y fuentes (ciclo {ciclo})",
    )
    log_agente("FUSIONADOR_ECOLOGICO", f"Validando propuestas ecologicas y referencias (ciclo {ciclo})...", kaomoji="[x_x]")

    prompt = (
        f"Eres el Fusionador Ecologico del Sistema AgriPoli (ciclo {ciclo}/{max_ciclos}).\n"
        f"Region: {state.get('region', 'Desconocida')}\n\n"
        "Evalua si las propuestas son COMPATIBLES con:\n"
        "  1. El clima de la region (Koppen — verifica que no propongas Oyamel en tropico)\n"
        "  2. Los cultivos propuestos por el Agronomo\n"
        "  3. El control biologico de plagas (insectos depredadores y plantas trampa)\n"
        "  4. El diseno de banda floral (atractores de polinizadores)\n"
        "  5. Incorpora OBLIGATORIAMENTE al final el bloque estandarizado de fuentes y referencias tecnicas: [FUENTES Y REFERENCIAS: GRUPO ECOLOGICO]\n\n"
        "Si hay incompatibilidades criticas responde: RECHAZADO\n[razon y especies alternativas]\n"
        "Si todo es coherente responde: APROBADO\n[diseno integral agroecologico de la parcela + [FUENTES Y REFERENCIAS: GRUPO ECOLOGICO]]\n\n"
        f"--- CULTIVOS AGRONOMO ---\n{json.dumps(state.get('propuestas_agricolas', []))[:1000]}\n\n"
        f"--- FLORA NATIVA ---\n{state.get('resultado_mini_flora', 'Sin datos')[:1200]}\n\n"
        f"--- POLINIZADORES ---\n{state.get('resultado_mini_polinizadores', 'Sin datos')[:800]}\n\n"
        f"--- CONTROL BIOLOGICO ---\n{state.get('resultado_mini_control_biologico', 'Sin datos')[:800]}\n\n"
        f"--- ATRACTORES ---\n{state.get('resultado_mini_atractores', 'Sin datos')[:800]}\n\n"
        f"--- GBIF ---\n{state.get('resultado_mini_gbif', 'Sin datos')[:500]}\n\n"
        f"--- REFERENCIAS Y FUENTES ECOLOGICAS (CONABIO / NOM-059 / TAVILY) ---\n{state.get('resultado_mini_referencias', 'Sin datos')[:1000]}"
    )
    try:
        response = llm.invoke(prompt)
        texto = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as e:
        texto = f"APROBADO\n[Error en fusionador ecologico: {e}]"
        log_error(str(e), kaomoji="[X_X]")

    if "RECHAZADO" in texto and ciclo < max_ciclos:
        estado = "RECHAZADO"
        anotacion = texto.replace("RECHAZADO", "").strip()
        log_info(f"Propuesta RECHAZADA en ciclo {ciclo}. Retroalimentando mini_flora...", kaomoji="[o_o]")
    else:
        estado = "APROBADO"
        anotacion = ""
        if ciclo >= max_ciclos and "RECHAZADO" in texto:
            log_info(f"Max ciclos ({max_ciclos}) alcanzados. Aprobando con advertencias.", kaomoji="[x_x]")
        else:
            log_ok(f"Propuestas ecologicas APROBADAS en ciclo {ciclo}.", kaomoji="(^_^)/")

    propuestas = [{"texto": texto, "ciclo": ciclo, "estado": estado}] if estado == "APROBADO" else []

    return {
        "ciclo_ecologico": ciclo,
        "anotacion_fusionador_eco": anotacion,
        "estado_fusion_eco": estado,
        "propuestas_ecologicas": propuestas,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER DEL LOOP
# ─────────────────────────────────────────────────────────────────────────────

def router_fusion_ecologico(state: EstadoGrupoEcologico) -> str:
    estado = state.get("estado_fusion_eco", "PENDIENTE")
    config = cargar_config_agentes().get("configuracion", {})
    max_ciclos = int(config.get("max_ciclos_retroalimentacion", 3))

    if estado == "APROBADO":
        log_flujo("fusionador_ecologico", "END", "Diseno ecologico aprobado -> salida del grupo")
        return "Aprobado"
    if state.get("ciclo_ecologico", 0) >= max_ciclos:
        log_flujo("fusionador_ecologico", "END", f"Max ciclos {max_ciclos} -> forzar salida")
        return "Aprobado"
    log_flujo("fusionador_ecologico", "mini_flora_nativa", "Retroalimentando al ecologo con anotacion")
    return "Reintentar"


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCCION DEL SUB-GRAFO
# ─────────────────────────────────────────────────────────────────────────────

def crear_grafo_ecologico():
    """Compila y retorna el sub-grafo del Grupo Ecologico con loop de retroalimentacion.
    7 mini-agentes paralelos con enfoque agroecologico integral y referencias.
    """
    workflow = StateGraph(EstadoGrupoEcologico)

    workflow.add_node("mini_flora_nativa",              nodo_mini_flora_nativa)
    workflow.add_node("mini_polinizadores",              nodo_mini_polinizadores)
    workflow.add_node("mini_catalogo_local",             nodo_mini_catalogo_local)
    workflow.add_node("mini_gbif",                       nodo_mini_gbif)
    workflow.add_node("mini_control_biologico",          nodo_mini_control_biologico)
    workflow.add_node("mini_atractores_polinizadores",   nodo_mini_atractores_polinizadores)
    workflow.add_node("mini_referencias_ecologico",      nodo_mini_referencias_ecologico)
    workflow.add_node("fusionador_ecologico",            nodo_fusionador_ecologico)

    # Fork paralelo desde START (7 mini-agentes en paralelo)
    workflow.add_edge(START, "mini_flora_nativa")
    workflow.add_edge(START, "mini_polinizadores")
    workflow.add_edge(START, "mini_catalogo_local")
    workflow.add_edge(START, "mini_gbif")
    workflow.add_edge(START, "mini_control_biologico")
    workflow.add_edge(START, "mini_atractores_polinizadores")
    workflow.add_edge(START, "mini_referencias_ecologico")

    # Join: todos convergen en el fusionador
    workflow.add_edge("mini_flora_nativa",             "fusionador_ecologico")
    workflow.add_edge("mini_polinizadores",            "fusionador_ecologico")
    workflow.add_edge("mini_catalogo_local",           "fusionador_ecologico")
    workflow.add_edge("mini_gbif",                    "fusionador_ecologico")
    workflow.add_edge("mini_control_biologico",        "fusionador_ecologico")
    workflow.add_edge("mini_atractores_polinizadores", "fusionador_ecologico")
    workflow.add_edge("mini_referencias_ecologico",    "fusionador_ecologico")

    # Loop: fusionador puede regresar a mini_flora con anotacion
    workflow.add_conditional_edges("fusionador_ecologico", router_fusion_ecologico, {
        "Aprobado":  END,
        "Reintentar": "mini_flora_nativa",
    })

    return workflow.compile()


# ─────────────────────────────────────────────────────────────────────────────
# Mini-agentes FUTUROS (stubs — descomentar para activar)
# ─────────────────────────────────────────────────────────────────────────────

# def nodo_mini_nom059(state):
#     """FUTURO: Verifica estatus de conservacion NOM-059-SEMARNAT.
#     Garantiza que no se propongan especies protegidas para extraccion."""
#     pass

# def nodo_mini_koppen(state):
#     """FUTURO: Clasifica la region por clima Koppen (INEGI + SMN).
#     Alimenta la seleccion de flora y cultivos con el tipo de clima real."""
#     pass

# def nodo_mini_corredor_biologico(state):
#     """FUTURO: Sugiere conexiones de corredores biologicos entre parcelas (CONABIO)."""
#     pass

# def nodo_mini_inaturalist(state):
#     """FUTURO: Observaciones ciudadanas geo-referenciadas de iNaturalist Mexico."""
#     pass

# def nodo_mini_hongos_beneficiosos(state):
#     """FUTURO: Micorrizas y hongos entomopatogenos (Beauveria bassiana vs pulgon).
#     Control biologico a nivel fungico para complementar mini_control_biologico."""
#     pass

# def nodo_mini_banco_semillas(state):
#     """FUTURO: Banco de semillas nativas disponibles en viveros locales de Mexico.
#     Integra con CONABIO y red de conservacion de semillas criollas."""
#     pass
