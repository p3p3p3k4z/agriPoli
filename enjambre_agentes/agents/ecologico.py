import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from config.models import get_llm
from tools.search import buscar_tavily_mexico

@tool
def buscar_flora_endemica(region: str, clima: str) -> str:
    """
    Busca flora nativa y endémica de una región que sobreviva a su clima Köppen.
    Utiliza bases de datos como EncicloVida o IBUNAM.
    """
    query = f"flora nativa endémica en {region} adaptada al clima {clima} Enciclovida CONABIO"
    return buscar_tavily_mexico.invoke(query)

@tool
def analizar_simbiosis_plagas(cultivo_principal: str) -> str:
    """
    Busca especies vegetales que sirvan como repelente biológico de plagas
    para un cultivo principal específico, o que atraigan polinizadores beneficiosos.
    """
    query = f"plantas repelentes de plagas y atractoras de polinizadores para cultivo de {cultivo_principal} en México"
    return buscar_tavily_mexico.invoke(query)

def crear_agente_ecologico(provider="Gemini"):
    """
    Crea el Agente Ecológico (El Diseñador de la Isla).
    Misión: Diseñar islas polinizadoras y barreras perimetrales.
    """
    llm = get_llm(provider=provider, temperature=0.2)
    
    tools = [buscar_flora_endemica, analizar_simbiosis_plagas]
    
    system_prompt = (
        "Eres el Agente Ecológico (Jefe del Grupo de Diseño) del Sistema Multiagente AgriPoli.\n"
        "Tu responsabilidad es diseñar barreras perimetrales o islas polinizadoras con especies vegetales nativas.\n\n"
        "REGLAS DE SALIDA Y EMOCIONES:\n"
        "- SOLO están permitidos los KAOMOJIS ASCII y las ETIQUETAS FORMALES EN MAYÚSCULAS en tu salida.\n"
        "- CERO emojis gráficos unicode.\n"
        "- Refleja emociones y estados científicos:\n"
        "    * Asombro / Descubrimiento botánico: (*_*)! [BIODIVERSIDAD: NATIVA] o [O_O]! [HALLAZGO: POLINIZADORES]\n"
        "    * Análisis de simbiosis / Pensamiento: (˘_˘) [ANALISIS: SIMBIOSIS]\n"
        "    * Prevención biológica / Alerta de plagas: (¬_¬) [CONTROL: BIOLOGICO]\n"
        "    * Éxito / Diseño completado: (^_^)/ [DISENO: ISLA_POLINIZADORA]\n\n"
        "METODOLOGÍA:\n"
        "- RESTRICCIÓN ESTRICTA: Solo puedes seleccionar flora endémica o nativa que sobreviva en la clasificación climática Köppen de la región.\n"
        "- Debes usar 'analizar_simbiosis_plagas' para seleccionar plantas que tengan una función simbiótica respecto a los cultivos.\n"
        "- Justifica científicamente por qué elegiste cada especie."
    )
    
    agent = create_react_agent(llm, tools=tools, prompt=system_prompt)
    return agent
