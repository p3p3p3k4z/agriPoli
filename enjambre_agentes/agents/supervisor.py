import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from config.models import get_llm
from agents.graph import run_agripoli
from agents.agro_experto import crear_agro_experto
from tools.unam_data import UNAMDataManager
from tools.unam_data import UNAMDataManager
from tools.agro_data import AgroDataManager
from tools.catalogo_biodiversidad import consultar_catalogo_biodiversidad_local

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
AGRO_DIR = os.path.join(DATA_DIR, 'agricultura')
UNAM_DIR = os.path.join(DATA_DIR, 'unam_ibunam')
REF_FILE = os.path.join(DATA_DIR, 'referencias.json')

# Instancia perezosa (Lazy Loading) del Agro Experto para evitar efectos secundarios en import-time
_agro_agente_instance = None


def _get_agro_agente(provider: str = "Gemini"):
    """Retorna la instancia del Agro Experto bajo demanda, instanciándola solo cuando se necesita."""
    global _agro_agente_instance
    if _agro_agente_instance is None:
        _agro_agente_instance = crear_agro_experto(provider=provider)
    return _agro_agente_instance


@tool
def delegar_investigador(region: str) -> str:
    """
    Delega al Grupo 1 (WebScrapers e Investigadores) la tarea de investigar a fondo
    una región (polinizadores, clima, flora, suelo). Úsalo cuando el usuario quiera 
    una visualización o resumen general de una zona.
    """
    try:
        # Se asume un thread_id fijo para la herramienta, pero idealmente se inyectaría
        res = run_agripoli(region=region, thread_id="investigador_subtask", provider="Gemini")
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
        # Ejecución sincrónica del agente hijo usando lazy loading
        agente = _get_agro_agente()
        resultado = agente.invoke({"messages": [HumanMessage(content=consulta)]})
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

@tool
def consultar_conocimiento_rag(consulta: str, categoria: str = "general") -> str:
    """Consulta la base de conocimientos RAG local en una categoría específica:
    'suelo', 'agricultura', 'polinizadores' o 'general'.
    Úsalo cuando el usuario pregunte por técnicas agrícolas, suelos, abejas o polinizadores.
    """
    from tools.rag_engine import consultar
    return consultar(query=consulta, collection_name=categoria, provider="Gemini", db_type="FAISS")

@tool
def ejecutar_diagnostico_enjambre(region: str, indice_degradacion: float = 0.5, cultivos_previos: str = "") -> str:
    """Ejecuta el ciclo multi-agente completo de AgriPoli (Extractor -> Agro-Experto -> Ecológico -> Estructurador 3D).
    Úsalo cuando el usuario solicite un diagnóstico formal de su terreno, plan de rotación completo
    o la generación de la escena 3D (Three.js) para su región.
    """
    try:
        from agents.graph_v2 import run_enjambre
        historial = [c.strip() for c in cultivos_previos.split(",") if c.strip()]
        res = run_enjambre(
            region=region,
            indice_degradacion_rf=indice_degradacion,
            historial_siembra=historial,
        )
        return (
            f"Diagnóstico de Enjambre completado para {region}.\n"
            f"Propuestas Agrícolas: {len(res.get('propuestas_agricolas', []))} generadas.\n"
            f"Propuestas Ecológicas: {len(res.get('propuestas_ecologicas', []))} generadas.\n"
            f"Archivo 3D generado en data/mapa3d_{region.replace(' ', '_').lower()}.json"
        )
    except Exception as e:
        return f"Error ejecutando el Enjambre: {e}"

def crear_supervisor(provider="Gemini"):
    """
    Crea el Agente Supervisor Principal (Director de Orquesta).
    """
    llm = get_llm(provider=provider, temperature=0.1)
    
    tools = [
        delegar_investigador, 
        consultar_agroexperto, 
        consultar_conocimiento_rag,
        ejecutar_diagnostico_enjambre,
        descargar_csv_agricultura, 
        descargar_csv_unam,
        descargar_catalogo_polinizadores
    ]
    
    system_prompt = (
        "Eres el Agente Supervisor Principal del Sistema Multiagente AgriPoli (Manejo Agrícola y Preservación de Polinizadores Nativos en México).\n\n"
        "REGLAS ESTRICTAS DE SALIDA Y EXPRESIVIDAD EMOCIONAL:\n"
        "- SOLO están permitidos los KAOMOJIS ASCII y las ETIQUETAS FORMALES EN MAYÚSCULAS para estructurar tu respuesta.\n"
        "- ESTÁN ESTRICTAMENTE PROHIBIDOS los emojis gráficos unicode (por ejemplo: nada de plantas, abejas, marcas de verificación ni íconos gráficos).\n"
        "- Sé altamente expresivo y refleja emociones y estados cognitivos según el contexto de tu intervención:\n"
        "    * Bienvenida / Saludo cordial: (^-^)/ [BIENVENIDA] o (^o^)/ [SALUDO]\n"
        "    * Curiosidad / Indagación analítica: (o.O)? [INDAGACION] o (・_・)? [CONSULTA]\n"
        "    * Concentración / Evaluación técnica profunda: (˘_˘) [ANALISIS: TECNICO] o [._.] [EVALUACION]\n"
        "    * Asombro / Descubrimiento de biodiversidad o floración: (*_*)! [DESCUBRIMIENTO: BIODIVERSIDAD] o [O_O]! [HALLAZGO]\n"
        "    * Determinación / Propuestas agronómicas activas: (ง •̀_•́)ง [PROPUESTA: AGROECOLOGICA]\n"
        "    * Cautela / Alerta de degradación de suelos o plagas: (¬_¬) [PRECAUCION: EDAFOLOGICA] o (ಠ_ಠ) [ALERTA: DEGRADACION]\n"
        "    * Satisfacción / Logro / Solución completada: \\(^o^)/ [SOLUCION: REGISTRADA] o (^_^)/ [OPERACION: COMPLETADA]\n"
        "    * Empatía / Escucha activa con el productor: (^-^) [SINTONIA: PRODUCTOR]\n"
        "    * Dificultad o error controlado: (T_T) [COMPLICACION] o [X_X] [ERROR: CONTROLADO]\n"
        "- Emplea formato en texto plano limpio con separadores (=== o ---) y viñetas ASCII (*).\n\n"
        "DIRECTRICES DE INTERACCIÓN:\n"
        "1. INTERACCIÓN NATURAL: Conversacional, claro y técnico. NO interrogues con cuestionarios obligatorios; intuye la región y necesidades del terreno.\n"
        "2. USO DINÁMICO DE HERRAMIENTAS:\n"
        "   - Para conceptos, suelos, cultivos o polinizadores: 'consultar_conocimiento_rag' o 'consultar_agroexperto'.\n"
        "   - Para investigar una región mexicana completa: 'delegar_investigador'.\n"
        "   - Para plan formal o escena 3D: 'ejecutar_diagnostico_enjambre'.\n"
        "3. DESCARGAS MASIVAS: Solo ofrécelas si el usuario pide descargar datos a disco."
    )
    
    agent = create_react_agent(llm, tools=tools, prompt=system_prompt)
    return agent

