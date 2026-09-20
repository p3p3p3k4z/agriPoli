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
from agents.supervisor import crear_supervisor
from agents.graph_v2 import run_enjambre_stream
from tools.rag_engine import (
    COLLECTIONS, obtener_estado_rag, build_vectorstore, normalizar_coleccion
)
from tools.catalogo_biodiversidad import consultar_catalogo_biodiversidad_local
from scripts.generar_diagrama import generar_diagrama_arquitectura

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
    "rag_local":      "(O_O) RAG Local",
    "despachador":    "[>_<] Despachador Web",
    "mini_tavily":    "(O_O) Mini-Tavily/CONABIO",
    "mini_academico": "(^_~) Mini-Academico",
    "mini_scraper":   "[~_~] Mini-Scraper Profundo",
    "parseador_web":  "(^o^) Parseador Web",
    "fusionador":     "(^-^)/ Fusionador de Contexto",
    "agro":           "(^-^) Agente Agricola",
    "ecologico":      "(*_*) Agente Ecologico",
    "validador":      "[x_x] Supervisor Validador",
    "estructurador":  "(^o^) Estructurador 3D (Three.js)",
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
    """Muestra la guía completa de comandos y estructura RAG."""
    print(f"""
{CYAN}{BOLD}========================================================================{RESET}
{CYAN}{BOLD}                MANUAL DE COMANDOS — AGRIPOLI CLI                       {RESET}
{CYAN}{BOLD}========================================================================{RESET}

{BOLD}COMANDOS DISPONIBLES:{RESET}
  {GREEN}/help{RESET} o {GREEN}/ayuda{RESET}        Muestra este manual de ayuda.
  {GREEN}/config{RESET}              Muestra la configuracion activa y estado de API keys.
  {GREEN}/provider <nombre>{RESET}   Cambia el proveedor en caliente (Gemini, Groq, Cohere, Ollama, HuggingFace).
  {GREEN}/model [nombre]{RESET}      Lista modelos en vivo descubiertos por models_* o cambia el modelo activo.
  {GREEN}/diagrama{RESET}            Genera y guarda el diagrama de arquitectura en imagen (docs/arquitectura_agentes.png).
  {GREEN}/biodiversidad <esp>{RESET} Consulta el catalogo de 3,900+ flora melifera y polinizadores de Mexico.
  {GREEN}/mode <modo>{RESET}         Cambia el modo de investigacion: {YELLOW}Hibrido{RESET} | {YELLOW}Solo Local{RESET} | {YELLOW}Solo Web{RESET}.
  {GREEN}/rag [status]{RESET}        Muestra las carpetas de conocimiento y cantidad de documentos.
  {GREEN}/rag rebuild{RESET}         Reconstruye los indices vectoriales locales (FAISS).
  {GREEN}/run [region]{RESET}        Lanza el flujo completo del Enjambre multiagente con streaming.
  {GREEN}/clear{RESET} o {GREEN}/reset{RESET}       Limpia el historial de conversacion e inicia nueva sesion.
  {GREEN}/exit{RESET} o {GREEN}/quit{RESET} o {GREEN}/q{RESET}     Cierra la sesion del supervisor.

{BOLD}DONDE COLOCAR TUS DOCUMENTOS PARA RAG:{RESET}
  Los documentos se ubican en {BOLD}enjambre_agentes/data/knowledge/{RESET} separados por tema:
  
  [DIRECTORIO] {YELLOW}data/knowledge/suelo/{RESET}
     Estudios edafologicos, texturas, pH, retencion de humedad, NPK y degradacion (SADER).
  [DIRECTORIO] {YELLOW}data/knowledge/agricultura/{RESET}
     Manuales SADER/INIFAP/USDA, rotacion de cultivos, milpa, abonos y guias de siembra.
  [DIRECTORIO] {YELLOW}data/knowledge/polinizadores/{RESET}
     Catalogos CONABIO, abejas nativas/meliponas, floraciones meliferas y simbiosis.
  [DIRECTORIO] {YELLOW}data/knowledge/general/{RESET}
     Normativas SEMARNAT (NOM-059), guias agroecologicas y publicaciones mixtas.

  {DIM}Formatos compatibles: .pdf, .txt, .md, .csv{RESET}

{BOLD}COMO CONVERSAR:{RESET}
  No es necesario introducir datos tecnicos de inmediato. Puedes chatear normalmente:
  - {DIM}"Hola, ¿que polinizadores nativos son comunes en Oaxaca?"{RESET}
  - {DIM}"Tengo una milpa con suelo arcilloso y plagas de gusano cogollero, ¿que plantas me recomiendas intercalar?"{RESET}
  - {DIM}"Genera el diagnostico y modelo 3D para mi parcela en Sonora"{RESET}
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


async def ejecutar_pipeline_enjambre(region: str, state: dict):
    """Ejecuta el pipeline completo del enjambre con streaming y trazabilidad en tiempo real."""
    print(f"\n{CYAN}{BOLD}{'='*72}{RESET}")
    print(f"{CYAN}{BOLD}[>_<] [ENJAMBRE] Ejecutando Enjambre Multiagente para: {region}{RESET}")
    print(f"{CYAN}Proveedor: {state['provider']} | Modo: {state['mode']}{RESET}")
    print(f"{CYAN}{BOLD}{'='*72}{RESET}\n")

    try:
        loop = asyncio.get_running_loop()
        def _stream():
            return list(run_enjambre_stream(
                region=region,
                indice_degradacion_rf=0.5,
                historial_siembra=[],
                thread_id=state["thread_id"],
                provider=state["provider"],
                flow_type=state["mode"],
            ))

        eventos = await loop.run_in_executor(None, _stream)

        for event in eventos:
            for nodo_name, nodo_data in event.items():
                label = NODO_LABELS.get(nodo_name, f"[{nodo_name}]")
                log_ok(f"Nodo {label} completado", kaomoji="(^_^)/")

                if nodo_name == "parseador_web" and "contexto_web" in nodo_data:
                    preview = str(nodo_data["contexto_web"])[:200]
                    print(f"    {DIM}Resumen web: {preview}...{RESET}")
                elif nodo_name == "agro" and "propuestas_agricolas" in nodo_data:
                    if nodo_data["propuestas_agricolas"]:
                        p = nodo_data["propuestas_agricolas"][0].get("texto", "")[:200]
                        print(f"    {DIM}Propuesta agricola: {p}...{RESET}")
                elif nodo_name == "ecologico" and "propuestas_ecologicas" in nodo_data:
                    if nodo_data["propuestas_ecologicas"]:
                        p = nodo_data["propuestas_ecologicas"][0].get("texto", "")[:200]
                        print(f"    {DIM}Propuesta ecologica: {p}...{RESET}")
                elif nodo_name == "estructurador" and "json_threejs_final" in nodo_data:
                    import json as _json
                    json_path = os.path.join(
                        os.path.dirname(__file__), "..", "data",
                        f"mapa3d_{region.replace(' ', '_').lower()}.json"
                    )
                    os.makedirs(os.path.dirname(json_path), exist_ok=True)
                    with open(json_path, "w", encoding="utf-8") as f:
                        _json.dump(nodo_data["json_threejs_final"], f, ensure_ascii=False, indent=2)
                    print(f"    {GREEN}{BOLD}(^o^) [JSON 3D] Guardado en: {json_path}{RESET}")

        print(f"\n{GREEN}{BOLD}{'='*72}{RESET}")
        log_ok(f"Diagnostico y modelo 3D completados con exito para '{region}'.", kaomoji="(^o^)")
        print(f"{GREEN}{BOLD}{'='*72}{RESET}\n")

    except Exception as e:
        log_error(f"Error en el flujo del Enjambre: {e}", kaomoji="[X_X]")


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

    elif cmd in ("/diagrama", "/diagram", "/arquitectura"):
        log_info("Compilando arquitectura en LangGraph y exportando imagen estatica...", kaomoji="(o_o)")
        ruta = generar_diagrama_arquitectura()
        if ruta:
            log_ok(f"Imagen estatica guardada exitosamente en: {ruta}", kaomoji="(^o^)")
        else:
            log_error("No fue posible generar la imagen del diagrama.", kaomoji="[X_X]")

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
                region = input("Nombre de la region a diagnosticar: ").strip()
            except (KeyboardInterrupt, EOFError):
                return True
        if region:
            await ejecutar_pipeline_enjambre(region, state)

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
        state["supervisor"] = crear_supervisor(provider=state["provider"])
    except Exception as e:
        log_error(f"Error inicializando supervisor: {e}", kaomoji="[X_X]")
        return

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
