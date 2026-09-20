import json
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from config.models import get_llm
from tools.search import buscar_tavily_mexico, buscar_conabio, explorador_enciclovida, buscar_datos_unam
from tools.scraper import lector_web_playwright, lector_pdf_web, lector_json_api

@tool
def extraer_datos_clima_nasa(region: str) -> str:
    """
    Busca datos climáticos en tiempo real y alertas de sequía.
    Simula o busca consultas a APIs meteorológicas o NASA Power.
    """
    res = buscar_tavily_mexico.invoke(f"clima actual y alertas de sequía CONAGUA NASA en {region}")
    return res

@tool
def extraer_topografia_soilgrids(region: str) -> str:
    """
    Simula la extracción de parámetros de suelo desde la API de SoilGrids (ISRIC).
    """
    return f"Simulación SoilGrids para {region}: Suelo predominantemente franco-arcilloso. pH promedio 6.5. Contenido de carbono orgánico: 1.2%."

def crear_agente_extractor(provider="Gemini"):
    """
    Crea el Agente Extractor (El Investigador de Tiempo Real).
    Misión: Recopilar contexto espacial y climático usando herramientas de búsqueda y scraping profundo.
    """
    llm = get_llm(provider=provider, temperature=0.1)
    
    tools = [
        extraer_datos_clima_nasa, 
        extraer_topografia_soilgrids,
        buscar_conabio,
        explorador_enciclovida,
        buscar_datos_unam,
        lector_web_playwright,
        lector_pdf_web,
        lector_json_api
    ]
    
    system_prompt = (
        "Eres el Agente Extractor (Jefe del Grupo Investigador) del Sistema Multiagente AgriPoli. "
        "Tu misión es recopilar información dinámica, ecológica y geoespacial que los modelos matemáticos no tienen almacenada. "
        "Delega tareas a tus mini-agentes (herramientas) para obtener el clima actual y composición del suelo para una región específica. "
        "ADEMÁS, debes usar tus capacidades de Scraper e Investigador Profundo: "
        "Usa 'buscar_conabio' o 'explorador_enciclovida' para rastrear URLs relevantes, y luego usa 'lector_web_playwright' "
        "o 'lector_pdf_web' para extraer el texto directamente de las páginas gubernamentales o artículos científicos encontrados. "
        "Tu salida debe ser un resumen denso y técnico con puros datos crudos para que los siguientes agentes (Agrícola y Ecológico) puedan tomar decisiones."
    )
    
    agent = create_react_agent(llm, tools=tools, prompt=system_prompt)
    return agent
