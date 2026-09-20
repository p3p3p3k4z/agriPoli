import json
from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from config.models import get_llm
from schemas.threejs_schema import Mapa3D

def crear_agente_estructurador(provider="Gemini"):
    """
    Crea el Agente Estructurador (El Traductor Visual).
    Misión: Traducir propuestas narrativas en JSON estructurado para Three.js.
    Este agente NO usa herramientas (tools).
    Usa el motor de Salidas Estructuradas (Structured Outputs) de LangChain/Pydantic.
    """
    # Usamos temperatura 0 para máxima precisión de formato
    llm = get_llm(provider=provider, temperature=0.0)
    
    # Configuramos el LLM para forzar la salida según el esquema Pydantic Mapa3D
    estructurador_llm = llm.with_structured_output(Mapa3D)
    
    system_prompt = (
        "Eres el Agente Estructurador (Traductor Visual 3D) del Sistema Multiagente AgriPoli. "
        "Tu misión es tomar las propuestas agrícolas y ecológicas narrativas "
        "y convertirlas rígidamente en un formato JSON estructurado válido. "
        "Calcula coordenadas relativas (x,y,z) lógicas para organizar los cultivos y las barreras vivas. "
        "Asigna colores Hexadecimales representativos a cada especie vegetal para el motor de renderizado."
    )
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Genera el JSON final en base a esto:\n\nRegión: {region}\nDegradación: {degradacion}\nSuelo: {suelo}\n\nPropuesta Agrícola: {prop_agro}\n\nPropuesta Ecológica: {prop_eco}")
    ])
    
    chain = prompt_template | estructurador_llm
    return chain

def invocar_estructurador(region: str, degradacion: float, suelo: str, prop_agro: str, prop_eco: str) -> dict:
    """
    Función helper para invocar la cadena estructurada
    """
    chain = crear_agente_estructurador()
    resultado = chain.invoke({
        "region": region,
        "degradacion": degradacion,
        "suelo": suelo,
        "prop_agro": prop_agro,
        "prop_eco": prop_eco
    })
    # Como usamos with_structured_output, resultado es una instancia de Mapa3D
    return resultado.model_dump()
