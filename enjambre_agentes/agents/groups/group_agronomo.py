"""
Grupo Agronomo — Sub-grafo LangGraph del Sistema Multiagente AgriPoli V3.

Responsabilidad: Proponer cultivos, rotaciones regenerativas y analisis de suelo.
Mini-agentes paralelos:
  * mini_suelo              — Estudios de suelo, RAG edafologico, SymPy
  * mini_cultivo            — Bases locales SIAP, monografias SADER, literatura
  * mini_siap               — Scraping dinamico SADER/SIAP
  * mini_inegi_agro         — Indicadores INEGI agropecuarios
  * mini_calculadora        — Calculos agronomicos con SymPy
  * mini_rotacion_regenerativa — Secuencias de cultivos funcionales (Agricola Regenerativa)
                               Logica de 4 grupos: Nitrogeno, Descompactacion,
                               Control de Plagas/Hongos y Optimizacion Hidrica.

Fusionador interno con LOOP de retroalimentacion:
  * fusionador_agronomo — Valida viabilidad climatica/edafologica
                          y regresa al mini_cultivo si detecta inconsistencias.
"""
from __future__ import annotations

import json
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import create_react_agent

import config.silenciador
from config.models import get_llm_para_agente, cargar_config_agentes
from config.agri_logger import log_agente, log_mini_agente, log_flujo, log_ok, log_info, log_error
from agents.state_v3 import EstadoGrupoAgronomo


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 1: Analisis de Suelo
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_suelo(state: EstadoGrupoAgronomo) -> dict:
    """Fork A: Estudios de suelo, RAG edafologico y calculos con SymPy."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_suelo")
    log_mini_agente("MINI_SUELO", f"Analizando composicion y salud del suelo en '{region}'...", kaomoji="[O_O]")

    from tools.search import buscar_estudios_suelo
    from tools.herramientas_cientificas import calcular_agronomia
    from tools.rag_engine import consultar

    agente = create_react_agent(
        model=llm,
        tools=[buscar_estudios_suelo, calcular_agronomia],
        prompt=(
            "Eres el Mini-Agente de Suelos del Grupo Agronomo de AgriPoli. "
            "Analiza el tipo de suelo, pH, texturas y recomendaciones de enmiendas organicas "
            "para la region indicada. Usa calcular_agronomia para formulas edafologicas. "
            "Responde con datos tecnicos precisos."
        ),
    )
    contexto_rag = state.get("contexto_rag_agro", "")
    consulta = (
        f"Estudio de suelos, textura, pH y fertilidad en {region} Mexico. "
        f"Indice de degradacion: {state.get('indice_degradacion_rf', 0.5)}\n"
        f"Contexto RAG disponible:\n{contexto_rag[:1500]}"
    )
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_suelo] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_SUELO", "Analisis edafologico completado.", kaomoji="[O_O]")
    return {"resultado_mini_suelo": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 2: Cultivos y Rotaciones (retroalimentable)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_cultivo(state: EstadoGrupoAgronomo) -> dict:
    """Fork B: Propuesta de cultivos y rotaciones, recibe anotacion del fusionador."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_cultivo")
    ciclo = state.get("ciclo_agronomo", 0)
    anotacion = state.get("anotacion_fusionador_agro", "")

    if anotacion and ciclo > 0:
        log_mini_agente(
            "MINI_CULTIVO",
            f"Ciclo {ciclo}: Recibiendo retroalimentacion del Fusionador -- corrigiendo propuesta...",
            kaomoji="(~_~;)",
        )
    else:
        log_mini_agente("MINI_CULTIVO", f"Formulando propuesta de cultivos para '{region}'...", kaomoji="(-w-)/")

    from agents.agro_experto import crear_agro_experto
    agente = crear_agro_experto(provider="Gemini")  # Usa el agente existente como base

    nota_correccion = f"\n\n[CORRECCION DEL FUSIONADOR - Ciclo {ciclo}]:\n{anotacion}" if anotacion else ""
    prompt = (
        f"Region: {region}. "
        f"Indice de degradacion RF: {state.get('indice_degradacion_rf', 0)}. "
        f"Historial de siembra: {state.get('historial_siembra', [])}.\n\n"
        f"Contexto extractor:\n{state.get('contexto_extractor', '')[:2000]}"
        f"{nota_correccion}"
    )
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=prompt)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_cultivo] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_CULTIVO", "Propuesta de cultivos formulada.", kaomoji="(-w-)/")
    return {"resultado_mini_cultivo": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 3: SIAP / SADER Web
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_siap(state: EstadoGrupoAgronomo) -> dict:
    """Fork C: Scraping dinamico de estadisticas SADER/SIAP."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_siap")
    log_mini_agente("MINI_SIAP", f"Consultando estadisticas SADER/SIAP para '{region}'...", kaomoji="[._.]")

    from tools.search import buscar_literatura_agricola
    from tools.agro_data import AgroDataManager
    import os
    DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "agricultura"))

    agente = create_react_agent(
        model=llm,
        tools=[buscar_literatura_agricola],
        prompt=(
            "Eres el Mini-Agente SIAP del Grupo Agronomo de AgriPoli. "
            "Busca estadisticas de produccion agricola, superficie sembrada y rendimientos "
            "de SADER/SIAP para la region indicada."
        ),
    )
    consulta = f"estadisticas produccion agricola superficie sembrada {region} SADER SIAP"
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_siap] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_SIAP", "Datos SIAP recopilados.", kaomoji="[._.]")
    return {"resultado_mini_siap": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 4: INEGI Agropecuario
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_inegi_agro(state: EstadoGrupoAgronomo) -> dict:
    """Fork D: Indicadores estadisticos agropecuarios del INEGI."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_inegi_agro")
    log_mini_agente("MINI_INEGI_AGRO", f"Consultando indicadores INEGI agropecuarios para '{region}'...", kaomoji="(O_O)")

    from tools.inegi_client import consultar_indicador_inegi, usar_inegipy_catalogo
    agente = create_react_agent(
        model=llm,
        tools=[consultar_indicador_inegi, usar_inegipy_catalogo],
        prompt=(
            "Eres el Mini-Agente INEGI del Grupo Agronomo de AgriPoli. "
            "Busca indicadores de produccion agricola, uso de suelo y actividad agropecuaria "
            "usando las herramientas INEGI disponibles."
        ),
    )
    consulta = f"superficie sembrada produccion agricola {region} indicadores INEGI"
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_inegi] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_INEGI_AGRO", "Indicadores INEGI recopilados.", kaomoji="(O_O)")
    return {"resultado_mini_inegi": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 5: Calculadora Agronomica
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_calculadora(state: EstadoGrupoAgronomo) -> dict:
    """Fork E: Calculos agronomicos con SymPy (densidad de siembra, balance hidrico)."""
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_calculadora")
    log_mini_agente("MINI_CALCULADORA", "Ejecutando calculos agronomicos...", kaomoji="(˘ワ˘)")

    from tools.herramientas_cientificas import calcular_agronomia
    agente = create_react_agent(
        model=llm,
        tools=[calcular_agronomia],
        prompt=(
            "Eres el Mini-Agente Calculadora del Grupo Agronomo de AgriPoli. "
            "Realiza calculos de densidad de siembra, balance hidrico, indice de cosecha "
            "y necesidades de nitrogeno usando calcular_agronomia con SymPy."
        ),
    )
    consulta = (
        f"Calcular densidad de siembra optima y balance hidrico para la region {region}. "
        f"Indice de degradacion de suelo: {state.get('indice_degradacion_rf', 0.5)}"
    )
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_calculadora] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente("MINI_CALCULADORA", "Calculos agronomicos completados.", kaomoji="(˘ワ˘)")
    return {"resultado_mini_calculadora": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 6: Rotacion Regenerativa (Agricultura Regenerativa)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_rotacion_regenerativa(state: EstadoGrupoAgronomo) -> dict:
    """Fork F: Agronomo Experto en Agricultura Regenerativa.
    Recomienda el SIGUIENTE cultivo en la secuencia de rotacion funcional.
    NUNCA mezcla cultivos en el mismo surco al mismo tiempo.
    Opera con 4 grupos funcionales:
      Grupo N — Leguminosas que restauran nitrogeno (frijol, haba, cacahuate, trevol)
      Grupo D — Raices profundas que descompactan el suelo (rabano, nabo, girasol)
      Grupo P — Cultivos resistentes o que controlan plagas/hongos (sorgo, centeno, marigold)
      Grupo H — Cultivos que optimizan la retencion hidrica (avena, trigo sarraceno, avena)
    """
    region = state.get("region", "Mexico")
    llm = get_llm_para_agente("mini_rotacion_regenerativa")
    historial = state.get("historial_siembra", [])
    anotacion = state.get("anotacion_fusionador_agro", "")
    ciclo = state.get("ciclo_agronomo", 0)

    log_mini_agente(
        "MINI_ROTACION_REGENERATIVA",
        f"Calculando secuencia de rotacion regenerativa para '{region}'...",
        kaomoji="(u_u)",
    )

    from tools.search import buscar_literatura_agricola
    agente = create_react_agent(
        model=llm,
        tools=[buscar_literatura_agricola],
        prompt=(
            "Eres un Agronomo de campo experto en Agricultura Regenerativa. "
            "Tu trabajo es recomendar el SIGUIENTE cultivo en la rotacion, "
            "nunca mezclar cultivos en el mismo surco al mismo tiempo. "
            "Usas 4 grupos funcionales para sanar la tierra: "
            "N (restaurar nitrogeno con leguminosas como frijol o haba), "
            "D (descompactar con raices profundas como rabano o girasol), "
            "P (controlar plagas o hongos con sorgo, centeno o tagetes) y "
            "H (mejorar retencion de agua con avena o vetiver). "
            "Diagnostica el problema principal del suelo y da maximo 3 opciones de cultivo. "
            "FORMATO DE SALIDA OBLIGATORIO, sin caracteres especiales ni markdown, solo texto plano: "
            "Diagnostico: [una sola oracion sobre el estado del suelo] "
            "Grupo funcional: [N / D / P / H] "
            "Opcion 1: [nombre del cultivo] | Beneficio: [una oracion breve] "
            "Opcion 2: [nombre del cultivo] | Beneficio: [una oracion breve] "
            "Opcion 3: [nombre del cultivo] | Beneficio: [una oracion breve] "
            "Duracion estimada: [en semanas] "
            "Siguiente rotacion sugerida: [nombre del cultivo principal]. "
            "Tono: directo, amable, de campo. Sin terminos academicos ni listas largas."
        ),
    )

    nota_correccion = (
        f"\n\n[CORRECCION DEL FUSIONADOR - Ciclo {ciclo}]:\n{anotacion}"
        if anotacion and ciclo > 0 else ""
    )
    historial_texto = ", ".join(historial) if historial else "sin historial previo"
    consulta = (
        f"Region: {region}. "
        f"Estado del suelo: indice de degradacion {state.get('indice_degradacion_rf', 0.5):.2f} (0=sano, 1=muy degradado). "
        f"Historial de siembra: {historial_texto}. "
        f"Contexto adicional del suelo: {state.get('resultado_mini_suelo', '')[:800]}"
        f"{nota_correccion}"
    )
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_rotacion_regenerativa] {e}"
        log_error(str(e), kaomoji="[X_X]")
    log_mini_agente(
        "MINI_ROTACION_REGENERATIVA",
        "Secuencia de rotacion regenerativa calculada.",
        kaomoji="(u_u)",
    )
    return {"resultado_mini_rotacion": texto}


# ─────────────────────────────────────────────────────────────────────────────
# MINI-AGENTE 7: Referencias, Antecedentes y Trazabilidad (Tavily + Fuentes MX)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_mini_referencias(state: EstadoGrupoAgronomo) -> dict:
    """Fork G: De la consulta original y ambito agronomico, extrae exclusivamente
    las fuentes, instituciones, normas y enlaces web tecnicos y cientificos de Mexico
    (INIFAP, SADER, SIAP, CIMMYT, Chapingo, UNAM, SciELO, NOM-021) en formato estandarizado.
    """
    region = state.get("region", "Mexico")
    consulta_orig = state.get("consulta_original", "") or state.get("contexto_extractor", "") or f"cultivos y rotacion de suelos en {region} Mexico"
    llm = get_llm_para_agente("mini_referencias")
    log_mini_agente("MINI_REFERENCIAS_AGRO", f"Extrayendo fuentes tecnicas y antecedentes para '{region}'...", kaomoji="(^_~)")

    from tools.search import buscar_antecedentes_cultivo, buscar_literatura_agricola
    import re

    agente = create_react_agent(
        model=llm,
        tools=[buscar_antecedentes_cultivo, buscar_literatura_agricola],
        prompt=(
            "Eres el Mini-Agente de Referencias del Grupo Agronomo de AgriPoli. "
            "Tu UNICO objetivo es extraer de la consulta original las fuentes, autores, instituciones, antecedentes tecnicos y enlaces web agronomicos. "
            "No inventes datos ni hagas recomendaciones de cultivo adicionales. Solo extrae y formatea las fuentes tecnicas: "
            "1. Cita antecedentes verificados de instituciones mexicanas (INIFAP, SADER, SIAP, CIMMYT, Chapingo, UNAM, SciELO). "
            "2. Cita normas oficiales mexicanas aplicables (ej. NOM-021-SEMARNAT-2000 fertilidad de suelos). "
            "3. Incluye las URLs y nombres de articulos o manuales reales recuperados con tus herramientas de busqueda. "
            "FORMATO ESTANDAR OBLIGATORIO: "
            "[FUENTES Y REFERENCIAS: GRUPO AGRONOMO]\n"
            "1. [Institucion / Repositorio] Titulo o investigacion consultada | Enlace: <URL>\n"
            "2. [Norma Oficial] Titulo de la norma aplicable | Referencia: <Cita oficial>"
        ),
    )
    consulta = (
        f"fuentes cientificas, manuales tecnicos y normas agronomicas sobre: {consulta_orig} en {region} Mexico. "
        f"Asociacion de cultivos, rotacion y conservacion de suelos."
    )
    try:
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
        texto = resultado["messages"][-1].content
    except Exception as e:
        texto = f"[ERROR mini_referencias] {e}"
        log_error(str(e), kaomoji="[X_X]")

    urls = re.findall(r'https?://[^\s)\]>"\']+', str(texto))
    log_mini_agente("MINI_REFERENCIAS_AGRO", f"Fuentes agronomicas extraidas ({len(urls)} enlaces).", kaomoji="(^_~)")
    return {
        "resultado_mini_referencias": texto,
        "referencias_fuentes": urls,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FUSIONADOR AGRONOMO (con LOOP de retroalimentacion)
# ─────────────────────────────────────────────────────────────────────────────

def nodo_fusionador_agronomo(state: EstadoGrupoAgronomo) -> dict:
    """Join + Arbitro: Valida viabilidad climatica y edafologica.
    Si detecta inconsistencias, RECHAZA y retroalimenta al mini_cultivo.
    """
    llm = get_llm_para_agente("fusionador_agronomo")
    ciclo = state.get("ciclo_agronomo", 0) + 1
    log_flujo(
        "[mini_suelo|mini_cultivo|mini_siap|mini_inegi|mini_calc|mini_rotacion|mini_referencias]",
        "fusionador_agronomo",
        f"Join: auditando coherencia agronomica y trazabilidad documental (ciclo {ciclo})",
    )
    log_agente("FUSIONADOR_AGRONOMO", f"Validando propuestas agronomicas, rotacion y referencias (ciclo {ciclo})...", kaomoji="[x_x]")

    config = cargar_config_agentes().get("configuracion", {})
    max_ciclos = int(config.get("max_ciclos_retroalimentacion", 3))

    prompt = (
        f"Eres el Fusionador Agronomo del Sistema AgriPoli (ciclo {ciclo}/{max_ciclos}).\n"
        f"Region analizada: {state.get('region', 'Desconocida')}\n\n"
        "Evalua si las propuestas de cultivo Y la rotacion regenerativa son VIABLES climatica y edafologicamente.\n"
        "VERIFICA:\n"
        "  1. Compatibilidad con el clima de la region (Koppen)\n"
        "  2. Compatibilidad con el tipo de suelo\n"
        "  3. Coherencia con el historial de siembra\n"
        "  4. La secuencia de rotacion regenerativa es logica y factible\n"
        "  5. No se recomienda un cultivo incompatible con la region (ej: manzana en zona arida tropical)\n"
        "  6. Incorpora OBLIGATORIAMENTE un apartado final con las referencias tecnicas, instituciones y enlaces web recuperados por mini_referencias.\n\n"
        "Si hay inconsistencias criticas responde: RECHAZADO\n[razon especifica y cultivos alternativos sugeridos]\n"
        "Si todo es viable responde: APROBADO\n[resumen ejecutivo de propuestas, rotacion y seccion explicita [REFERENCIAS Y ANTECEDENTES DOCUMENTADOS]]\n\n"
        f"--- SUELO ---\n{state.get('resultado_mini_suelo', 'Sin datos')[:1200]}\n\n"
        f"--- PROPUESTA CULTIVOS ---\n{state.get('resultado_mini_cultivo', 'Sin datos')[:1200]}\n\n"
        f"--- ROTACION REGENERATIVA ---\n{state.get('resultado_mini_rotacion', 'Sin datos')[:1000]}\n\n"
        f"--- SIAP/SADER ---\n{state.get('resultado_mini_siap', 'Sin datos')[:600]}\n\n"
        f"--- INEGI ---\n{state.get('resultado_mini_inegi', 'Sin datos')[:600]}\n\n"
        f"--- CALCULOS ---\n{state.get('resultado_mini_calculadora', 'Sin datos')[:400]}\n\n"
        f"--- REFERENCIAS Y ANTECEDENTES (TAVILY / INIFAP / SADER) ---\n{state.get('resultado_mini_referencias', 'Sin datos')[:1200]}"
    )
    try:
        response = llm.invoke(prompt)
        texto = response.content if isinstance(response.content, str) else str(response.content)
    except Exception as e:
        texto = f"APROBADO\n[Error en fusionador: {e}]"
        log_error(str(e), kaomoji="[X_X]")

    if "RECHAZADO" in texto and ciclo < max_ciclos:
        estado = "RECHAZADO"
        anotacion = texto.replace("RECHAZADO", "").strip()
        log_info(f"Propuesta RECHAZADA en ciclo {ciclo}. Retroalimentando mini_cultivo...", kaomoji="[o_o]")
    else:
        estado = "APROBADO"
        anotacion = ""
        if ciclo >= max_ciclos and "RECHAZADO" in texto:
            log_info(f"Max ciclos ({max_ciclos}) alcanzados. Aprobando con advertencias.", kaomoji="[x_x]")
        else:
            log_ok(f"Propuestas agronomicas APROBADAS en ciclo {ciclo}.", kaomoji="(^_^)/")

    propuestas = [{"texto": texto, "ciclo": ciclo, "estado": estado}] if estado == "APROBADO" else []

    return {
        "ciclo_agronomo": ciclo,
        "anotacion_fusionador_agro": anotacion,
        "estado_fusion_agro": estado,
        "propuestas_agricolas": propuestas,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER DEL LOOP
# ─────────────────────────────────────────────────────────────────────────────

def router_fusion_agronomo(state: EstadoGrupoAgronomo) -> str:
    estado = state.get("estado_fusion_agro", "PENDIENTE")
    config = cargar_config_agentes().get("configuracion", {})
    max_ciclos = int(config.get("max_ciclos_retroalimentacion", 3))

    if estado == "APROBADO":
        log_flujo("fusionador_agronomo", "END", "Plan agronomico aprobado -> salida del grupo")
        return "Aprobado"
    if state.get("ciclo_agronomo", 0) >= max_ciclos:
        log_flujo("fusionador_agronomo", "END", f"Max ciclos {max_ciclos} -> forzar salida")
        return "Aprobado"
    log_flujo("fusionador_agronomo", "mini_cultivo", "Retroalimentando al agronomo con anotacion de error")
    return "Reintentar"


# ─────────────────────────────────────────────────────────────────────────────
# CONSTRUCCION DEL SUB-GRAFO
# ─────────────────────────────────────────────────────────────────────────────

def crear_grafo_agronomo():
    """Compila y retorna el sub-grafo del Grupo Agronomo con loop de retroalimentacion."""
    workflow = StateGraph(EstadoGrupoAgronomo)

    workflow.add_node("mini_suelo",                   nodo_mini_suelo)
    workflow.add_node("mini_cultivo",                  nodo_mini_cultivo)
    workflow.add_node("mini_siap",                     nodo_mini_siap)
    workflow.add_node("mini_inegi_agro",               nodo_mini_inegi_agro)
    workflow.add_node("mini_calculadora",              nodo_mini_calculadora)
    workflow.add_node("mini_rotacion_regenerativa",    nodo_mini_rotacion_regenerativa)
    workflow.add_node("mini_referencias",              nodo_mini_referencias)
    workflow.add_node("fusionador_agronomo",           nodo_fusionador_agronomo)

    # Fork paralelo desde START (7 mini-agentes en paralelo)
    workflow.add_edge(START,              "mini_suelo")
    workflow.add_edge(START,              "mini_cultivo")
    workflow.add_edge(START,              "mini_siap")
    workflow.add_edge(START,              "mini_inegi_agro")
    workflow.add_edge(START,              "mini_calculadora")
    workflow.add_edge(START,              "mini_rotacion_regenerativa")
    workflow.add_edge(START,              "mini_referencias")

    # Join: todos convergen en el fusionador
    workflow.add_edge("mini_suelo",                   "fusionador_agronomo")
    workflow.add_edge("mini_cultivo",                 "fusionador_agronomo")
    workflow.add_edge("mini_siap",                    "fusionador_agronomo")
    workflow.add_edge("mini_inegi_agro",              "fusionador_agronomo")
    workflow.add_edge("mini_calculadora",             "fusionador_agronomo")
    workflow.add_edge("mini_rotacion_regenerativa",   "fusionador_agronomo")
    workflow.add_edge("mini_referencias",             "fusionador_agronomo")

    # Loop: fusionador puede regresar a mini_cultivo con anotacion
    workflow.add_conditional_edges("fusionador_agronomo", router_fusion_agronomo, {
        "Aprobado":  END,
        "Reintentar": "mini_cultivo",  # Solo el mini_cultivo recibe la retroalimentacion
    })

    return workflow.compile()


# ─────────────────────────────────────────────────────────────────────────────
# Mini-agentes FUTUROS (stubs — descomentar para activar)
# ─────────────────────────────────────────────────────────────────────────────

# def nodo_mini_random_forest(state):
#     """FUTURO: Modelo de degradacion de suelo (sklearn RandomForest).
#     Calcula el indice de degradacion desde parametros de suelo medidos."""
#     pass

# def nodo_mini_mercado_agricola(state):
#     """FUTURO: Precios de mercado SNIIM para evaluar rentabilidad de cultivos."""
#     pass

# def nodo_mini_agua(state):
#     """FUTURO: Balance hidrico Penman-Monteith + datos NASA POWER."""
#     pass

# def nodo_mini_fitosanidad(state):
#     """FUTURO: Alertas de plagas y enfermedades del SENASICA."""
#     pass

# def nodo_mini_agroforesteria(state):
#     """FUTURO: Sistemas de agroforesteria (milpa, huerto familiar, acahual).
#     Recomienda combinaciones de arboles + cultivos para regeneracion profunda."""
#     pass

# def nodo_mini_clima_historico(state):
#     """FUTURO: Clima historico CONAGUA / SMN por municipio.
#     Enriquece la recomendacion de rotacion con datos de lluvia historica."""
#     pass
