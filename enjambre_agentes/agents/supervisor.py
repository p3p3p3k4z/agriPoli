import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from config.models import get_llm
from agents.graph import run_anita
from agents.agro_experto import crear_agro_experto
from tools.unam_data import UNAMDataManager
from tools.agro_data import AgroDataManager

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
AGRO_DIR = os.path.join(DATA_DIR, 'agricultura')
UNAM_DIR = os.path.join(DATA_DIR, 'unam_ibunam')
REF_FILE = os.path.join(DATA_DIR, 'referencias.json')

# Instancia del Agro Experto que usamos como "Herramienta" para el Supervisor
agro_agente = crear_agro_experto(provider="Gemini")

@tool
def delegar_investigador(region: str) -> str:
    """
    Delega al Grupo 1 (WebScrapers e Investigadores) la tarea de investigar a fondo
    una región (polinizadores, clima, flora, suelo). Úsalo cuando el usuario quiera 
    una visualización o resumen general de una zona.
    """
    try:
        # Se asume un thread_id fijo para la herramienta, pero idealmente se inyectaría
        res = run_anita(region=region, thread_id="investigador_subtask", provider="Gemini")
        # Retornamos el JSON o texto estructurado que generó el sintetizador
        return f"Investigación completada. Resumen:\n{res.get('datos_estructurados', 'Sin datos')[:2000]}..."
    except Exception as e:
        return f"Error en la investigación: {e}"

@tool
def consultar_agroexperto(consulta: str) -> str:
    """
    Delega al Grupo 2 (Agro Experto) para responder preguntas específicas sobre cultivos,
    rendimientos, o utilizar INEGIpy para indicadores. Úsalo para visualizar respuestas 
    antes de ofrecer una descarga masiva.
    """
    try:
        from langchain_core.messages import HumanMessage
        # Ejecución sincrónica del agente hijo usando el estado de LangGraph
        resultado = agro_agente.invoke({"messages": [HumanMessage(content=consulta)]})
        mensajes = resultado.get("messages", [])
        return mensajes[-1].content if mensajes else 'Sin respuesta del experto.'
    except Exception as e:
        return f"Error consultando al Agro Experto: {e}"

@tool
async def descargar_csv_agricultura(anio: int = 2022) -> str:
    """
    Petición al Grupo 3. Úsalo ÚNICAMENTE si el usuario confirmó explícitamente 
    que desea DESCARGAR y guardar el archivo masivo de Agricultura (Cierres Agrícolas SIAP)
    en su disco local.
    """
    manager = AgroDataManager(data_dir=AGRO_DIR)
    csv_path = await manager.descargar_siap_csv(anio)
    if csv_path:
        # Actualizamos referencias manualmente (el de agro no lo tenía aún en el script)
        ref_manager = UNAMDataManager(data_dir=UNAM_DIR, ref_file=REF_FILE)
        ref_manager.registrar_referencia(
            titulo=f"Cierre Agrícola SIAP {anio}",
            url=f"http://infosiap.siap.gob.mx/gobmx/datosAbiertos/ProduccionAgricola/Cierre_agricola_mun_{anio}.csv",
            descripcion="Datos de superficie sembrada y producción por municipio.",
            tipo_dato="CSV Agricultura"
        )
        return f"¡Éxito! CSV de Agricultura descargado en: {csv_path}. Referencia guardada."
    return "Falló la descarga del CSV Agrícola."

@tool
async def descargar_csv_unam(coleccion: str) -> str:
    """
    Petición al Grupo 3. Úsalo ÚNICAMENTE si el usuario confirmó explícitamente 
    que desea DESCARGAR la colección de la UNAM (opciones: 'insectos' o 'flora')
    a su disco duro.
    """
    manager = UNAMDataManager(data_dir=UNAM_DIR, ref_file=REF_FILE)
    if coleccion.lower() == 'insectos':
        ruta = await manager.descargar_dataset_csv(
            "https://datosabiertos.unam.mx/IBUNAM:CNIN:Polinizadores.csv",
            "CNIN_polinizadores.csv",
            "Colección Nacional Insectos UNAM",
            "Registros de polinizadores"
        )
    else:
        ruta = await manager.descargar_dataset_csv(
            "https://datosabiertos.unam.mx/IBUNAM:MEXU:Flora.csv",
            "MEXU_flora.csv",
            "Herbario Nacional UNAM",
            "Registros de flora nativa"
        )
    if ruta:
        return f"¡Éxito! Colección '{coleccion}' descargada en {ruta}. Referencia guardada."
    return "Falló la descarga de la colección de UNAM."

@tool
async def descargar_catalogo_polinizadores(limite_especies: int = None) -> str:
    """
    Petición al Grupo 3. Úsalo ÚNICAMENTE si el usuario confirmó que desea 
    DESCARGAR el catálogo de polinizadores (y flora melífera) de EncicloVida.
    Acepta un límite opcional si el usuario pide una muestra.
    """
    try:
        from scripts.descargar_catalogo import main as descargar_cat
        # Se ejecuta para plantas melíferas y polinizadores
        await descargar_cat(tipo="plantas_meliferas", limit=limite_especies, use_gbif=True)
        await descargar_cat(tipo="visitantes_polinizadores", limit=limite_especies, use_gbif=True)
        msg = f"¡Éxito! Catálogo descargado (límite: {limite_especies or 'Sin límite, completo'})."
        return msg
    except Exception as e:
        return f"Error descargando el catálogo: {e}"

def crear_supervisor(provider="Gemini"):
    """
    Crea el Agente Supervisor Principal (Director de Orquesta).
    """
    llm = get_llm(provider=provider, temperature=0.1)
    
    tools = [
        delegar_investigador, 
        consultar_agroexperto, 
        descargar_csv_agricultura, 
        descargar_csv_unam,
        descargar_catalogo_polinizadores
    ]
    
    system_prompt = (
        "Eres el Agente Supervisor Principal del Enjambre Ecológico (AniIta). "
        "Tu trabajo es interactuar amablemente con el usuario humano, entender qué necesita, "
        "y delegar las tareas a tus grupos de agentes a través de las herramientas. "
        "\n\nReglas Críticas:"
        "\n1. INTERACCIÓN (Human-in-the-Loop): Primero utiliza 'delegar_investigador' o 'consultar_agroexperto' para visualizar y resumir la información que el usuario pide."
        "\n2. OFRECER DESCARGA: Tras mostrarle los resultados, pregúntale si desea descargar los datos masivos CSV (Agricultura/UNAM) o los catálogos de Enciclovida/iNaturalist a su disco local. Menciónale que puede pedir descargar solo una 'muestra' para que sea más rápido."
        "\n4. REFERENCIAS: Asegúrale al usuario que cada descarga o dato mostrado guarda sus orígenes para mantener rigor científico."
        "\n5. ESTILO DE ESCRITURA: ESTÁ ESTRICTAMENTE PROHIBIDO usar Emojis gráficos (como 🙋‍♂️, 🛡️, 🤖, 🌱). En su lugar, usa ÚNICAMENTE Kaomojis ASCII (ej. (^-^), (>_<), (^_^)/) para darle personalidad al texto usando solo caracteres de texto."
    )
    
    agent = create_react_agent(llm, tools=tools, prompt=system_prompt)
    return agent
