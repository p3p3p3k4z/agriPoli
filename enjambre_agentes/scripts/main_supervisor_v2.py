#!/usr/bin/env uv run python
"""
Supervisor CLI del Sistema de Apoyo Multiagente AgriPoli.

Experiencia interactiva conversacional estilo OpenCode:
  - Inicio inmediato en chat sin preguntas previas
  - Inferencia dinámica de necesidades del terreno a partir de la conversación
  - Trazabilidad en tiempo real del flujo de comunicación entre agentes por LangGraph
  - Logs estructurados con kaomojis expresivos y etiquetas formales (cero emojis gráficos)
  - Comandos slash (/help, /config, /provider, /model, /diagrama, /biodiversidad, /mode, /rag, /run, /clear, /exit)
  - Soporte de 4 colecciones RAG temáticas (suelo, agricultura, polinizadores, general)
  - Generación de diagrama de arquitectura estático guardado en imagen PNG
"""
import sys
import os
import uuid
import asyncio

# 1. Silenciamiento centralizado de advertencias ruidosas
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config.silenciador

from langchain_core.messages import HumanMessage, AIMessage

from config.keys import (
    GEMINI_API_KEY, GROQ_API_KEY, COHERE_API_KEY, TAVILY_API_KEY,
    PINECONE_API_KEY, HF_TOKEN, INEGI_API_TOKEN
)
from config.models import (
    get_available_providers, get_llm, extraer_texto_mensaje,
    obtener_modelos_disponibles,
    GEMINI_FLASH, GROQ_LLAMA3, COHERE_CMD, OLLAMA_DEFAULT
)
from config.agri_logger import (
    log_agente, log_mini_agente, log_herramienta, log_flujo, log_ok, log_info, log_error
)
from agents.supervisor_v2 import crear_supervisor_v2
from agents.supervisor import crear_supervisor  # V1 preservado
from agents.graph_v3 import run_enjambre_v3_stream
from agents.graph_v2 import run_enjambre_stream  # V2 legacy
from tools.rag_engine import (
    COLLECTIONS, obtener_estado_rag, build_vectorstore, normalizar_coleccion
)
from tools.catalogo_biodiversidad import consultar_catalogo_biodiversidad_local
from config.models import (
    get_available_providers, get_llm, extraer_texto_mensaje,
    obtener_modelos_disponibles, cargar_config_agentes, actualizar_config_agente,
    GEMINI_FLASH, GROQ_LLAMA3, COHERE_CMD, OLLAMA_DEFAULT
)
try:
    from scripts.generar_diagrama_v3 import generar_diagramas_v3 as generar_diagrama_arquitectura_v3
except Exception:
    generar_diagrama_arquitectura_v3 = None
try:
    from scripts.generar_diagrama import generar_diagrama_arquitectura
except Exception:
    generar_diagrama_arquitectura = None

# Estilos ANSI limpios para texto plano en terminal
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

# Etiquetas amigables con kaomojis para los nodos del grafo
NODO_LABELS = {
    # Grafo V3 (grupos)
    "grupo_extractor":       "[>_<] Grupo Extractor",
    "grupo_agronomo":        "(^-^) Grupo Agronomo",
    "grupo_ecologico":       "(*_*) Grupo Ecologico",
    "supervisor_validador":  "[x_x] Supervisor Validador",
    "agente_sintetizador":   "(^-^) Agente Sintetizador / Resumen Ejecutivo",
    "grupo_3d":              "(^o^) Grupo Generador 3D",
    # Nodos internos V2 (legacy)
    "rag_local":             "(O_O) RAG Local",
    "despachador":           "[>_<] Despachador Web",
    "mini_tavily":           "(O_O) Mini-Tavily/CONABIO",
    "mini_academico":        "(^_~) Mini-Academico",
    "mini_scraper":          "[~_~] Mini-Scraper",
    "parseador_web":         "(^o^) Parseador Web",
    "fusionador":            "(^-^)/ Fusionador",
    "agro":                  "(^-^) Agente Agricola",
    "ecologico":             "(*_*) Agente Ecologico",
    "validador":             "[x_x] Validador",
    "estructurador":         "(^o^) Estructurador 3D",
}


def mostrar_banner(state: dict):
    """Muestra el banner inicial con estado del sistema."""
    print(f"\n{GREEN}{BOLD}{'='*72}{RESET}")
    print(f"{GREEN}{BOLD}  AGRIPOLI — Sistema de Apoyo Multiagente para Manejo Agricola{RESET}")
    print(f"{GREEN}{BOLD}               y Preservacion de Polinizadores Nativos{RESET}")
    print(f"{GREEN}{BOLD}{'='*72}{RESET}")
    print(f"  {BOLD}Proveedor:{RESET} {CYAN}{state['provider']}{RESET} ({state['model'] or 'default'}) "
          f"| {BOLD}Modo:{RESET} {YELLOW}{state['mode']}{RESET} "
          f"| {BOLD}RAG:{RESET} {MAGENTA}{state['db_type']}{RESET}")
    print(f"  {DIM}Escribe tu consulta con naturalidad o usa {BOLD}/help{RESET}{DIM} para ver comandos.{RESET}")
    print(f"{GREEN}{BOLD}{'='*72}{RESET}\n")


def mostrar_ayuda():
    """Muestra la guia completa de comandos y estructura RAG."""
    print(f"""
{CYAN}{BOLD}========================================================================{RESET}
{CYAN}{BOLD}           MANUAL DE COMANDOS — AGRIPOLI CLI V3                         {RESET}
{CYAN}{BOLD}========================================================================{RESET}

{BOLD}COMANDOS DISPONIBLES:{RESET}
  {GREEN}/help{RESET} o {GREEN}/ayuda{RESET}             Muestra este manual de ayuda.
  {GREEN}/config{RESET}                   Configuracion activa y estado de API keys.
  {GREEN}/provider <nombre>{RESET}        Cambia el proveedor global (Gemini, Groq, Cohere, Ollama, HF).
  {GREEN}/model [nombre]{RESET}           Lista modelos en vivo o cambia el modelo global activo.
  {GREEN}/agente <nombre> <modelo>{RESET} Cambia el modelo de un agente especifico en config/agentes.yaml.
                             Ej: /agente fusionador_agronomo llama3-70b-8192
  {GREEN}/agente-provider <nombre> <prov>{RESET} Cambia el proveedor de un agente especifico.
                             Ej: /agente-provider mini_scraper Groq
  {GREEN}/config-agentes{RESET}           Muestra la tabla completa de modelos por agente (agentes.yaml).
  {GREEN}/diagrama{RESET}                 Genera 5 PNGs de arquitectura en docs/ (V3 + 4 grupos).
  {GREEN}/biodiversidad <esp>{RESET}      Catalogo local de 3,900+ flora y polinizadores de Mexico.
  {GREEN}/mode <modo>{RESET}              Modo de investigacion: {YELLOW}Hibrido{RESET} | {YELLOW}Solo Local{RESET} | {YELLOW}Solo Web{RESET}.
  {GREEN}/rag [status]{RESET}             Estado de la base de conocimientos RAG.
  {GREEN}/rag rebuild{RESET}              Reconstruye indices vectoriales FAISS.
  {GREEN}/run [region]{RESET}             Ejecuta el Enjambre Jerarquico V3 completo.
  {GREEN}/run3d [region]{RESET}           Ejecuta el Enjambre V3 + Generador 3D.
  {GREEN}/clear{RESET} o {GREEN}/reset{RESET}            Limpia historial e inicia nueva sesion.
  {GREEN}/exit{RESET} o {GREEN}/quit{RESET} o {GREEN}/q{RESET}        Cierra la sesion del supervisor.

{BOLD}DONDE COLOCAR TUS DOCUMENTOS PARA RAG:{RESET}
  Los documentos van en {BOLD}enjambre_agentes/data/knowledge/{RESET} separados por tema:

  {YELLOW}data/knowledge/suelo/{RESET}          Estudios edafologicos, pH, texturas, NPK (SADER).
  {YELLOW}data/knowledge/agricultura/{RESET}    Manuales SADER/INIFAP/USDA, rotacion de cultivos.
  {YELLOW}data/knowledge/polinizadores/{RESET}  Catalogos CONABIO, abejas nativas, floraciones.
  {YELLOW}data/knowledge/general/{RESET}        Normativas SEMARNAT, guias agroecologicas mixtas.
  {DIM}Formatos compatibles: .pdf, .txt, .md, .csv{RESET}

{BOLD}AGENTES CONFIGURABLES EN config/agentes.yaml:{RESET}
  mini_tavily, mini_academico, mini_scraper, descargador, fusionador_extractor,
  mini_suelo, mini_cultivo, mini_siap, mini_inegi_agro, mini_calculadora,
  fusionador_agronomo, mini_flora_nativa, mini_polinizadores, mini_catalogo_local,
  mini_gbif, mini_simbiosis, fusionador_ecologico,
  fusionador_3d, estructurador, validador_3d, supervisor
{CYAN}{BOLD}========================================================================{RESET}
""")


def mostrar_estado_rag():
    """Muestra el conteo de documentos en las 4 carpetas de RAG."""
    estado = obtener_estado_rag()
    print(f"\n{MAGENTA}{BOLD}[O_O] [RAG] Estado de la Base de Conocimientos:{RESET}")
    total_docs = 0
    for col, info in estado.items():
        cant = info["cantidad_archivos"]
        total_docs += cant
        color = GREEN if cant > 0 else DIM
        print(f"  {color}* {col:<15}{RESET} : {cant} archivo(s) en {info['ruta']}")
        if cant > 0 and info.get("archivos"):
            ejemplos = ", ".join(info["archivos"][:3])
            print(f"    {DIM}Ejemplos: {ejemplos}{RESET}")
    print(f"  {BOLD}Total de documentos:{RESET} {total_docs}\n")


async def ejecutar_pipeline_enjambre(region: str, state: dict, activar_3d: bool = False):
    """Ejecuta el Enjambre V3 con streaming y trazabilidad en tiempo real."""
    version = "V3 + 3D" if activar_3d else "V3"
    print(f"\n{CYAN}{BOLD}{'='*72}{RESET}")
    print(f"{CYAN}{BOLD}[>_<] [ENJAMBRE {version}] Ejecutando Enjambre Jerarquico para: {region}{RESET}")
    print(f"{CYAN}Modo: {state['mode']} | Config: config/agentes.yaml{RESET}")
    print(f"{CYAN}{BOLD}{'='*72}{RESET}\n")

    try:
        loop = asyncio.get_running_loop()
        def _stream():
            return list(run_enjambre_v3_stream(
                region=region,
                indice_degradacion_rf=0.5,
                historial_siembra=[],
                thread_id=state["thread_id"],
                flow_type=state["mode"],
                activar_3d=activar_3d,
            ))

        eventos = await loop.run_in_executor(None, _stream)

        resumen_ejecutivo = ""
        dossier_tecnico = {}
        referencias_fuentes = []
        json_threejs = {}

        for event in eventos:
            for nodo_name, nodo_data in event.items():
                label = NODO_LABELS.get(nodo_name, f"[{nodo_name}]")
                log_ok(f"Nodo {label} completado", kaomoji="(^_^)/")

                if nodo_name == "grupo_extractor":
                    ctx = nodo_data.get("contexto_extractor", "")
                    refs = nodo_data.get("referencias_fuentes", [])
                    print(f"    {DIM}Contexto web extraido: {len(ctx)} caracteres | {len(refs)} fuentes iniciales{RESET}")
                elif nodo_name == "grupo_agronomo":
                    props = nodo_data.get("propuestas_agricolas", [])
                    print(f"    {DIM}Propuestas agronomicas aprobadas: {len(props)} propuesta(s){RESET}")
                elif nodo_name == "grupo_ecologico":
                    props = nodo_data.get("propuestas_ecologicas", [])
                    print(f"    {DIM}Propuestas ecologicas aprobadas: {len(props)} propuesta(s){RESET}")
                elif nodo_name == "supervisor_validador":
                    decision = nodo_data.get("estado_final", "COMPLETADO")
                    print(f"    {DIM}Auditoria Supervisor: {decision}{RESET}")
                elif nodo_name == "agente_sintetizador":
                    resumen_ejecutivo = nodo_data.get("resumen_ejecutivo", "")
                    dossier_tecnico = nodo_data.get("dossier_tecnico", {})
                    referencias_fuentes = nodo_data.get("referencias_fuentes", [])
                elif nodo_name == "grupo_3d":
                    json_threejs = nodo_data.get("json_threejs_final", {})
                    json_path = os.path.join(
                        os.path.dirname(__file__), "..", "data",
                        f"mapa3d_{region.replace(' ', '_').lower()}.json"
                    )
                    print(f"    {GREEN}{BOLD}(^o^) [JSON 3D] Guardado en: {json_path}{RESET}")

        # Mostrar Resumen Ejecutivo y Diagnostico Integral en pantalla
        if resumen_ejecutivo:
            print(f"\n{GREEN}{BOLD}{'='*72}{RESET}")
            print(f"{GREEN}{BOLD}(^-^) [RESUMEN EJECUTIVO Y DIAGNOSTICO INTEGRAL: {region.upper()}]{RESET}")
            print(f"{GREEN}{BOLD}{'='*72}{RESET}\n")
            print(resumen_ejecutivo)
            print(f"\n{GREEN}{BOLD}{'='*72}{RESET}")
            log_ok(f"Diagnostico completado con exito para '{region}'.", kaomoji="(^o^)")
            print(f"{GREEN}{BOLD}{'='*72}{RESET}\n")
        else:
            print(f"\n{GREEN}{BOLD}{'='*72}{RESET}")
            log_ok(f"Diagnostico completado para '{region}'.", kaomoji="(^o^)")
            print(f"{GREEN}{BOLD}{'='*72}{RESET}\n")

        # Consultar interactivamente al usuario si desea conservar el dossier y fuentes localmente
        print(f"{YELLOW}{BOLD}(o.O)? [CONSERVACION LOCAL DE FUENTES Y DOSSIER]{RESET}")
        print(f"  {CYAN}Se identificaron {len(referencias_fuentes)} fuentes, normas y referencias oficiales para '{region}'.{RESET}")
        try:
            resp = input(f"  ¿Deseas guardar localmente este dossier y descargar sus fuentes para '{region}'? [S/n]: ").strip().lower()
            guardar_confirmado = resp in ("", "s", "si", "y", "yes", "1")
        except (KeyboardInterrupt, EOFError):
            guardar_confirmado = False

        if guardar_confirmado:
            await guardar_dossier_y_fuentes_localmente(region, resumen_ejecutivo, dossier_tecnico, referencias_fuentes)
        else:
            log_info("Conservacion local omitida por el usuario.", kaomoji="(o_o)")

    except Exception as e:
        log_error(f"Error en el flujo del Enjambre: {e}", kaomoji="[X_X]")


async def guardar_dossier_y_fuentes_localmente(
    region: str,
    resumen_ejecutivo: str,
    dossier_tecnico: dict,
    referencias_fuentes: list[str],
):
    """Guarda localmente el informe en Markdown, actualiza referencias.json,
    descarga fuentes en data/knowledge/descargas/ (logica base preservada)
    y ADICIONALMENTE organiza el repositorio jerarquico en regiones/<estado>/<municipio>/
    con referencias.json, datos_relevantes.json y fuentes clasificadas.
    """
    import re
    import datetime
    import json

    region_slug = re.sub(r'[^a-zA-Z0-9]+', '_', region.strip().lower()).strip('_')
    base_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
    ahora_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # =========================================================================
    # 1. LOGICA ORIGINAL CONSERVADA: Guardar Dossier en data/reportes/
    # =========================================================================
    reportes_dir = os.path.join(base_data_dir, "reportes")
    os.makedirs(reportes_dir, exist_ok=True)
    reporte_path = os.path.join(reportes_dir, f"diagnostico_{region_slug}.md")

    contenido_md = (
        f"---\n"
        f"region: \"{region}\"\n"
        f"fecha: \"{ahora_str}\"\n"
        f"generador: \"AgriPoli Enjambre V3\"\n"
        f"total_fuentes: {len(referencias_fuentes)}\n"
        f"---\n\n"
        f"{resumen_ejecutivo}\n"
    )
    try:
        with open(reporte_path, "w", encoding="utf-8") as f:
            f.write(contenido_md)
        log_ok(f"Dossier Markdown guardado en: {reporte_path}", kaomoji="(^_^)/")
    except Exception as e:
        log_error(f"Error al escribir dossier Markdown: {e}", kaomoji="[X_X]")

    # =========================================================================
    # 2. LOGICA ORIGINAL CONSERVADA: Guardar o actualizar data/referencias.json
    # =========================================================================
    referencias_path = os.path.join(base_data_dir, "referencias.json")
    registro = {
        "region": region,
        "slug": region_slug,
        "fecha": ahora_str,
        "total_fuentes": len(referencias_fuentes),
        "fuentes": referencias_fuentes,
    }
    try:
        historial_ref = []
        if os.path.exists(referencias_path):
            with open(referencias_path, "r", encoding="utf-8") as f:
                try:
                    contenido_json = json.load(f)
                    if isinstance(contenido_json, list):
                        historial_ref = contenido_json
                    elif isinstance(contenido_json, dict):
                        historial_ref = contenido_json.get("registros", [contenido_json])
                except Exception:
                    historial_ref = []

        historial_ref = [r for r in historial_ref if r.get("slug") != region_slug]
        historial_ref.append(registro)

        with open(referencias_path, "w", encoding="utf-8") as f:
            json.dump(historial_ref, f, ensure_ascii=False, indent=2)
        log_ok(f"Registro de fuentes actualizado en: {referencias_path}", kaomoji="(^_^)/")
    except Exception as e:
        log_error(f"Error actualizando referencias.json: {e}", kaomoji="[X_X]")

    # =========================================================================
    # 3. LOGICA ORIGINAL CONSERVADA: Descarga en data/knowledge/descargas/<region>/
    # =========================================================================
    if referencias_fuentes:
        descargas_dir = os.path.join(base_data_dir, "knowledge", "descargas", region_slug)
        os.makedirs(descargas_dir, exist_ok=True)
        log_info(f"Iniciando descarga local de fuentes en: {descargas_dir}...", kaomoji="[~_~]")

        try:
            from tools.descargador_masivo import DescargadorMasivoAsync
            import aiohttp

            descargador = DescargadorMasivoAsync(max_concurrencia=3, delay_segundos=0.3)
            urls_candidatas = [u for u in referencias_fuentes if not u.endswith((".png", ".jpg", ".svg", ".ico"))]

            async with aiohttp.ClientSession() as session:
                descargas_ok = 0
                for idx, url in enumerate(urls_candidatas[:8]):
                    nombre_base = f"fuente_{idx + 1}"
                    if ".pdf" in url.lower():
                        nombre_base += ".pdf"
                    else:
                        nombre_base += ".html"
                    dest_file = os.path.join(descargas_dir, nombre_base)
                    exito = await descargador.download_file(session, url, dest_file, desc=f"Fuente [{idx + 1}]")
                    if exito:
                        descargas_ok += 1

            log_ok(f"Descarga masiva completada: {descargas_ok} archivo(s) guardado(s) para consulta offline.", kaomoji="(^o^)")
        except Exception as e:
            log_error(f"Aviso durante la descarga masiva de fuentes: {e}", kaomoji="[o_o]")

    # =========================================================================
    # 4. ADICIONAL: ALMACENAMIENTO JERARQUICO REGIONAL (regiones/<estado>/<municipio>/)
    # =========================================================================
    from tools.gestor_regiones import guardar_dossier_regional, parsear_region_jerarquica

    estado, mun, ruta_rel = parsear_region_jerarquica(region)
    print(f"\n{CYAN}{BOLD}[O_O] [ALMACENAMIENTO REGIONAL ADICIONAL]{RESET} Sincronizando repositorio: {BOLD}{ruta_rel}/{RESET}")

    try:
        res = await guardar_dossier_regional(
            region=region,
            resumen_ejecutivo=resumen_ejecutivo,
            dossier_tecnico=dossier_tecnico,
            referencias_fuentes=referencias_fuentes,
        )

        print(f"\n{GREEN}{BOLD}(^-^)/ [REPOSITORIO REGIONAL ADICIONAL ACTUALIZADO]{RESET}")
        print(f"  {BOLD}Directorio base:{RESET}     {ruta_rel}/")
        print(f"  * {BOLD}Dossier regional:{RESET} {res['diagnostico_path']}")
        print(f"  * {BOLD}Indice fuentes:{RESET}    {res['referencias_path']}")
        print(f"  * {BOLD}Datos relevantes:{RESET}  {res['datos_relevantes_path']}")
        d = res.get("descargas", {})
        total_arch = d.get("pdf", 0) + d.get("html", 0) + d.get("csv", 0) + d.get("json", 0)
        print(f"  * {BOLD}Fuentes en disco:{RESET}  Total: {total_arch} (PDF: {d.get('pdf', 0)} | HTML/MD: {d.get('html', 0)} | CSV/JSON: {d.get('csv', 0) + d.get('json', 0)})")
        print(f"  {DIM}Archivos disponibles tanto en data/ como en la estructura regional {ruta_rel}/.{RESET}\n")

    except Exception as e:
        log_error(f"Aviso en sincronizacion regional adicional: {e}", kaomoji="[o_o]")


async def procesar_comando(linea: str, state: dict) -> bool:
    """Procesa un comando slash (inicia con /). Retorna False si se debe salir."""
    partes = linea.strip().split(maxsplit=1)
    cmd = partes[0].lower()
    arg = partes[1].strip() if len(partes) > 1 else ""

    if cmd in ("/exit", "/quit", "/q"):
        print(f"\n{CYAN}(^-^)/ Cerrando sesion del Supervisor AgriPoli. ¡Hasta pronto!{RESET}\n")
        return False

    elif cmd in ("/help", "/ayuda", "/?"):
        mostrar_ayuda()

    elif cmd == "/config":
        print(f"\n{CYAN}{BOLD}[CONFIG] Configuracion Actual del Sistema:{RESET}")
        print(f"  * Proveedor LLM: {BOLD}{state['provider']}{RESET}")
        print(f"  * Modelo:        {BOLD}{state['model'] or 'por defecto'}{RESET}")
        print(f"  * Modo de Flujo: {BOLD}{state['mode']}{RESET}")
        print(f"  * Vectorstore:   {BOLD}{state['db_type']}{RESET}")
        print(f"  * ID de Sesion:  {BOLD}{state['thread_id']}{RESET}")
        print(f"\n  {BOLD}Estado de Credenciales (.env):{RESET}")
        print(f"  * Gemini API:   {GREEN}Activa{RESET}" if GEMINI_API_KEY else f"  * Gemini API:   {RED}No configurada{RESET}")
        print(f"  * Groq API:     {GREEN}Activa{RESET}" if GROQ_API_KEY else f"  * Groq API:     {RED}No configurada{RESET}")
        print(f"  * Cohere API:   {GREEN}Activa{RESET}" if COHERE_API_KEY else f"  * Cohere API:   {RED}No configurada{RESET}")
        print(f"  * Tavily Web:   {GREEN}Activa{RESET}" if TAVILY_API_KEY else f"  * Tavily Web:   {RED}No configurada{RESET}")
        print(f"  * Pinecone:     {GREEN}Activa{RESET}" if PINECONE_API_KEY else f"  * Pinecone:     {DIM}Opcional (usando FAISS local){RESET}")
        print(f"  * HuggingFace:  {GREEN}Activa{RESET}" if HF_TOKEN else f"  * HuggingFace:  {DIM}No configurada{RESET}")
        print(f"  * INEGI Token:  {GREEN}Activa{RESET}\n" if INEGI_API_TOKEN else f"  * INEGI Token:  {DIM}No configurado (usando respaldo){RESET}\n")

    elif cmd == "/provider":
        disponibles = get_available_providers()
        if not arg:
            print(f"\nProveedores disponibles: {', '.join(disponibles)}")
            print(f"Uso: /provider <{' | '.join(disponibles)}>\n")
        else:
            match = [p for p in disponibles if p.lower() == arg.lower()]
            if match:
                state["provider"] = match[0]
                state["supervisor"] = crear_supervisor(provider=state["provider"])
                log_ok(f"Proveedor actualizado a: {state['provider']}", kaomoji="(^_^)/")
                modelos = obtener_modelos_disponibles(state["provider"])
                if modelos:
                    state["model"] = modelos[0]
                    print(f"  {CYAN}Modelos disponibles ({state['provider']}):{RESET}")
                    for m in modelos[:8]:
                        print(f"    * {m}")
                    if len(modelos) > 8:
                        print(f"    {DIM}... y {len(modelos)-8} modelos mas (usa /model para verlos todos){RESET}")
                    print(f"  {GREEN}Modelo activo:{RESET} {BOLD}{state['model']}{RESET}\n")
                else:
                    print("")
            else:
                log_error(f"Proveedor '{arg}' no reconocido. Opciones: {', '.join(disponibles)}", kaomoji="[X_X]")

    elif cmd == "/model":
        if not arg or arg.lower() in ("list", "ls", "help"):
            log_info(f"Consultando modelos en vivo para {state['provider']} (models_*)...", kaomoji="(o_o)")
            modelos = obtener_modelos_disponibles(state["provider"])
            print(f"\nModelos disponibles para {BOLD}{state['provider']}{RESET}:")
            for m in modelos:
                prefijo = f"  {GREEN}(^_^)/ [ACTIVO] {BOLD}" if m == state.get("model") else "  * "
                sufijo = f"{RESET}" if m == state.get("model") else ""
                print(f"{prefijo}{m}{sufijo}")
            print(f"\nPara cambiar de modelo usa: {GREEN}/model <nombre_modelo>{RESET}\n")
        else:
            state["model"] = arg
            log_ok(f"Modelo actualizado a: {arg}", kaomoji="(^_^)/")

    elif cmd in ("/diagrama", "/diagram", "/arquitectura", "/diagramas"):
        log_info("Exportando diagramas de arquitectura en alta resolucion (Enjambre + Subgrafos)...", kaomoji="(o_o)")
        if generar_diagrama_arquitectura_v3:
            rutas = generar_diagrama_arquitectura_v3()
            if rutas:
                for r in rutas:
                    log_ok(f"Diagrama guardado: {r}", kaomoji="(^o^)")
            else:
                log_error("No fue posible generar los diagramas V3.", kaomoji="[X_X]")
        elif generar_diagrama_arquitectura:
            ruta = generar_diagrama_arquitectura()
            if ruta:
                log_ok(f"Diagrama V2 guardado en: {ruta}", kaomoji="(^o^)")
            else:
                log_error("No fue posible generar el diagrama.", kaomoji="[X_X]")
        else:
            log_error("Generador de diagramas no disponible.", kaomoji="[X_X]")

    elif cmd in ("/agente", "/agente-model"):
        # /agente <nombre_agente> <modelo>
        partes_cmd = arg.split(maxsplit=1)
        if len(partes_cmd) < 2:
            print(f"\nUso: /agente <nombre_agente> <modelo>")
            print(f"Ejemplo: /agente fusionador_agronomo llama3-70b-8192\n")
        else:
            nombre, nuevo_modelo = partes_cmd[0], partes_cmd[1]
            ok = actualizar_config_agente(nombre, modelo=nuevo_modelo)
            if ok:
                log_ok(f"Modelo del agente '{nombre}' actualizado a: {nuevo_modelo}", kaomoji="(^_^)/")
                log_info("Diagramas de arquitectura actualizados en segundo plano en docs/.", kaomoji="[._.]")
            else:
                log_error(f"No se pudo actualizar el agente '{nombre}'.", kaomoji="[X_X]")

    elif cmd == "/agente-provider":
        partes_cmd = arg.split(maxsplit=1)
        if len(partes_cmd) < 2:
            print(f"\nUso: /agente-provider <nombre_agente> <proveedor>")
            print(f"Ejemplo: /agente-provider mini_scraper Groq\n")
        else:
            nombre, nuevo_prov = partes_cmd[0], partes_cmd[1]
            ok = actualizar_config_agente(nombre, proveedor=nuevo_prov)
            if ok:
                log_ok(f"Proveedor del agente '{nombre}' actualizado a: {nuevo_prov}", kaomoji="(^_^)/")
                log_info("Diagramas de arquitectura actualizados en segundo plano en docs/.", kaomoji="[._.]")
            else:
                log_error(f"No se pudo actualizar el proveedor del agente '{nombre}'.", kaomoji="[X_X]")

    elif cmd == "/config-agentes":
        cfg = cargar_config_agentes()
        modelos = cfg.get("modelos", {})
        config_general = cfg.get("configuracion", {})
        print(f"\n{MAGENTA}{BOLD}[CONFIG: AGENTES] config/agentes.yaml{RESET}")
        print(f"\n{BOLD}Configuracion general:{RESET}")
        for k, v in config_general.items():
            print(f"  * {k}: {v}")
        print(f"\n{BOLD}Modelos por agente:{RESET}")
        for nombre, info in modelos.items():
            prov = info.get('proveedor', '?')
            mod  = info.get('modelo', '?')
            temp = info.get('temperatura', '?')
            print(f"  {CYAN}{nombre:<28}{RESET} {GREEN}{prov:<10}{RESET} {mod} (T={temp})")
        print(f"\n{DIM}Edita config/agentes.yaml para cambiar manualmente. Usa /agente para cambiar en caliente.{RESET}\n")

    elif cmd in ("/biodiversidad", "/bio", "/especies"):
        if not arg:
            print(f"\nUso: /biodiversidad <nombre comun o cientifico> (ej. /biodiversidad Garambullo)\n")
        else:
            log_info(f"Buscando '{arg}' en el catalogo local de descargas masivas...", kaomoji="(O_O)")
            reporte = consultar_catalogo_biodiversidad_local.invoke({"consulta": arg})
            print(f"\n{reporte}\n")

    elif cmd == "/mode":
        opciones = {"hibrido": "Hibrido", "local": "Solo Local", "solo local": "Solo Local", "web": "Solo Web", "solo web": "Solo Web"}
        if arg.lower() in opciones:
            state["mode"] = opciones[arg.lower()]
            log_ok(f"Modo de investigacion cambiado a: {state['mode']}", kaomoji="(^_^)/")
        else:
            print(f"\nUso: /mode <hibrido | local | web>\n")

    elif cmd == "/rag":
        if arg.lower() == "rebuild":
            log_info("Reconstruyendo indices vectoriales locales FAISS...", kaomoji="[O_O]")
            for col in COLLECTIONS.keys():
                build_vectorstore(collection_name=col, provider=state["provider"], db_type="FAISS", force_rebuild=True)
            log_ok("Indices reconstruidos exitosamente.", kaomoji="(^_^)/")
        else:
            mostrar_estado_rag()

    elif cmd == "/run":
        region = arg
        if not region:
            try:
                region = input("Nombre de la region a diagnosticar (Enjambre V3): ").strip()
            except (KeyboardInterrupt, EOFError):
                return True
        if region:
            await ejecutar_pipeline_enjambre(region, state, activar_3d=False)

    elif cmd == "/run3d":
        region = arg
        if not region:
            try:
                region = input("Nombre de la region para diagnostico + modelo 3D: ").strip()
            except (KeyboardInterrupt, EOFError):
                return True
        if region:
            await ejecutar_pipeline_enjambre(region, state, activar_3d=True)

    elif cmd in ("/clear", "/reset"):
        state["chat_history"] = []
        state["thread_id"] = str(uuid.uuid4())[:8]
        log_ok(f"Historial de conversacion reiniciado. Nueva sesion: {state['thread_id']}", kaomoji="(^_^)/")

    else:
        log_error(f"Comando no reconocido: '{cmd}'. Escribe /help para ver opciones.", kaomoji="[X_X]")

    return True


async def main():
    # Estado inicial de la sesion
    state = {
        "provider": "Gemini",
        "model": GEMINI_FLASH,
        "mode": "Hibrido",
        "db_type": "FAISS",
        "thread_id": str(uuid.uuid4())[:8],
        "chat_history": [],
    }

    try:
        # Usar Supervisor V2 como principal (usa config/agentes.yaml)
        state["supervisor"] = crear_supervisor_v2(provider=state["provider"])
        log_ok("Supervisor V2 inicializado con config/agentes.yaml.", kaomoji="(^_^)/")
    except Exception as e:
        log_error(f"Error inicializando Supervisor V2, intentando V1: {e}", kaomoji="[X_X]")
        try:
            state["supervisor"] = crear_supervisor(provider=state["provider"])
            log_ok("Supervisor V1 (fallback) inicializado.", kaomoji="(^_^)/")
        except Exception as e2:
            log_error(f"Error critico inicializando supervisor: {e2}", kaomoji="[X_X]")
            return

    try:
        from config.models import iniciar_vigilante_agentes
        iniciar_vigilante_agentes(intervalo_segundos=2.0)
    except Exception:
        pass

    mostrar_banner(state)

    while True:
        try:
            prompt_str = f"{GREEN}{BOLD}AgriPoli{RESET} ({CYAN}{state['provider']}{RESET}) > "
            user_input = input(prompt_str).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n\n{CYAN}(^-^)/ Sesion finalizada. ¡Hasta pronto!{RESET}\n")
            break

        if not user_input:
            continue

        # Procesar comandos slash
        if user_input.startswith("/"):
            continuar = await procesar_comando(user_input, state)
            if not continuar:
                break
            continue

        # Interacción conversacional natural con trazabilidad de flujo en tiempo real
        state["chat_history"].append(HumanMessage(content=user_input))
        log_flujo("usuario", "supervisor", "Consulta recibida en chat", kaomoji="[>_<]")
        log_agente("SUPERVISOR", f"Evaluando intencion y herramientas requeridas [{state['provider']}]...", kaomoji="(o_o)")

        try:
            respuesta_final = ""
            # Consumir el flujo de actualización de LangGraph paso a paso
            async for step in state["supervisor"].astream({"messages": state["chat_history"]}, stream_mode="updates"):
                for nodo_key, nodo_val in step.items():
                    mensajes = nodo_val.get("messages", [])
                    for msg in mensajes:
                        # 1. Llamadas a herramientas emitidas por el supervisor
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                tool_name = tc.get("name", "herramienta")
                                tool_args = str(tc.get("args", {}))
                                log_flujo("supervisor", f"herramienta:{tool_name}", "Invocacion de sub-agente/herramienta", kaomoji="[>_<]")
                                log_herramienta(tool_name, f"Parametros: {tool_args[:100]}", kaomoji="[>_<]")
                        # 2. Retorno de datos de la herramienta hacia el supervisor
                        elif hasattr(msg, "name") and msg.name:
                            log_flujo(f"herramienta:{msg.name}", "supervisor", "Retorno de datos", kaomoji="(^-^)/")
                            preview_res = extraer_texto_mensaje(msg.content)[:140].replace('\n', ' ')
                            log_herramienta(msg.name, f"Datos obtenidos: {preview_res}...", kaomoji="(^_^)/")
                        # 3. Respuesta final de texto
                        elif hasattr(msg, "content") and msg.content:
                            texto = extraer_texto_mensaje(msg.content)
                            if texto and not (hasattr(msg, "tool_calls") and msg.tool_calls):
                                respuesta_final = texto

            if respuesta_final:
                print(f"\n{CYAN}(^-^) [SUPERVISOR]{RESET}\n{respuesta_final}\n")
                state["chat_history"].append(AIMessage(content=respuesta_final))
            else:
                log_info("El supervisor concluyo la operacion.", kaomoji="(o_o)")

            # Limitar historial para prevenir desborde de tokens
            if len(state["chat_history"]) > 20:
                state["chat_history"] = state["chat_history"][-20:]

        except Exception as e:
            log_error(f"Error procesando consulta: {e}", kaomoji="[X_X]")


if __name__ == "__main__":
    asyncio.run(main())
