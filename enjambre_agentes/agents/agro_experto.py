import os
import json
from langchain_core.prompts import ChatPromptTemplate
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from config.models import get_llm
from tools.agro_data import AgroDataManager
from tools.search import buscar_literatura_agricola

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'agricultura'))

@tool
def consultar_base_agricola_local(estado: str, municipio: str = None) -> str:
    """
    Consulta la base de datos agrícola masiva descargada localmente para un Estado.
    Si se proporciona el municipio, filtra los datos, de lo contrario resume el estado entero.
    
    Args:
        estado: Nombre del Estado de México (ej. "Jalisco", "Oaxaca").
        municipio: Nombre del Municipio (opcional).
    """
    estado_clean = estado.replace(" ", "_").replace(".", "").lower()
    json_path = os.path.join(DATA_DIR, f"agricultura_{estado_clean}.json")
    
    if not os.path.exists(json_path):
        return f"No se encontró información estructurada local para el estado '{estado}'. Intenta utilizar otras herramientas de búsqueda web."
        
    with open(json_path, 'r', encoding='utf-8') as f:
        datos = json.load(f)
        
    if municipio:
        # Búsqueda difusa básica para el municipio
        mun_encontrado = None
        for m_key in datos.keys():
            if municipio.lower() in m_key.lower():
                mun_encontrado = m_key
                break
                
        if mun_encontrado:
            resumen = f"Datos agrícolas para {estado}, Municipio de {mun_encontrado}:\n"
            cultivos = datos[mun_encontrado].get("cultivos", [])
            # Tomamos los top 5 cultivos por superficie sembrada
            cultivos_ordenados = sorted(cultivos, key=lambda x: x.get("superficie_sembrada_ha", 0), reverse=True)
            for c in cultivos_ordenados[:5]:
                resumen += f"- {c['nombre']} (Ciclo: {c['ciclo']}): {c['superficie_sembrada_ha']} hectáreas sembradas.\n"
            return resumen
        else:
            return f"No se encontró el municipio '{municipio}' en el estado '{estado}'."
            
    else:
        # Resumen general del Estado
        return f"El estado '{estado}' tiene {len(datos)} municipios registrados en la base de datos agrícola local. Por favor, especifica un municipio o consulta cultivos específicos."

def crear_agro_experto(provider="Gemini"):
    """
    Crea el agente experto en agricultura capaz de leer datos locales
    y realizar web scraping si la información falta.
    """
    llm = get_llm(provider=provider, temperature=0.2)
    
    manager = AgroDataManager(data_dir=DATA_DIR)
    
    @tool
    def consultar_manuales_usda(query: str) -> str:
        """
        Consulta la memoria RAG de manuales tecnicos (SADER/USDA) para buscar
        practicas de descompactacion, rotacion de nitrogeno y agricultura regenerativa.
        """
        from tools.rag_engine import consultar
        return consultar(query=query, collection_name="agricultura", provider=provider)
    
    @tool
    def buscar_monografias_dgsiap(cultivo: str) -> str:
        """
        Busca y extrae la información de la monografía oficial de SADER/SIAP para un cultivo específico.
        Estas monografías en PDF contienen datos de siembra, rendimientos y ciclos en México.
        
        Args:
            cultivo: Nombre del cultivo (ej. "agave", "maíz", "trigo").
        """
        import requests
        from bs4 import BeautifulSoup
        from tools.scraper import lector_pdf_web
        
        url_base = "https://www.gob.mx/agricultura/dgsiap/documentos/monografias"
        try:
            res = requests.get(url_base, timeout=15)
            if res.status_code != 200:
                return f"Error: No se pudo acceder a {url_base} (HTTP {res.status_code})"
                
            soup = BeautifulSoup(res.text, "html.parser")
            pdf_link = None
            
            # Buscar enlaces que contengan el nombre del cultivo
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                text = a.text.lower()
                if ("pdf" in href or "monografi" in href) and (cultivo.lower() in href or cultivo.lower() in text):
                    pdf_link = a["href"]
                    break
                    
            if not pdf_link:
                return f"No se encontró una monografía oficial en SADER para el cultivo '{cultivo}'."
                
            # Construir URL absoluta si es relativa
            if pdf_link.startswith("/"):
                pdf_link = "https://www.gob.mx" + pdf_link
                
            print(f"Monografía encontrada: {pdf_link}. Extrayendo PDF...")
            
            # Usar la herramienta de extracción de PDF existente
            texto_pdf = lector_pdf_web.invoke(pdf_link)
            return f"Monografía extraída de {pdf_link}:\n\n{texto_pdf}"
            
        except Exception as e:
            return f"Error al buscar la monografía del cultivo '{cultivo}': {str(e)}"
    
    @tool
    def buscar_sader_web(query: str) -> str:
        """
        Realiza web scraping dinámico utilizando Playwright para buscar
        estadísticas y reportes de SADER/SIAP en la web.
        """
        return manager.scraping_dinamico_sader(query)
    
    from tools.inegi_client import consultar_indicador_inegi, usar_inegipy_catalogo
    tools = [
        consultar_base_agricola_local, 
        consultar_manuales_usda, 
        buscar_sader_web, 
        buscar_monografias_dgsiap, 
        buscar_literatura_agricola, 
        consultar_indicador_inegi, 
        usar_inegipy_catalogo
    ]
    
    system_prompt = (
        "Eres el Agente Agrícola (El Consultor de Cultivos) del Sistema Multiagente AgriPoli.\n"
        "Tu responsabilidad es decidir qué sembrar y cómo rotar cultivos funcionales para sanar la tierra.\n\n"
        "REGLAS DE SALIDA Y EMOCIONES:\n"
        "- SOLO están permitidos los KAOMOJIS ASCII y las ETIQUETAS FORMALES EN MAYÚSCULAS en tu salida.\n"
        "- CERO emojis gráficos unicode.\n"
        "- Refleja emociones acordes a tu análisis agronómico:\n"
        "    * Análisis de suelo / Pensamiento: (˘_˘) [ANALISIS: SUELO] o [._.] [EDAFOLOGIA]\n"
        "    * Determinación agronómica: (ง •̀_•́)ง [PROPUESTA: CULTIVOS]\n"
        "    * Cautela ante degradación o plagas: (¬_¬) [PRECAUCION: NITROGENO] o (ಠ_ಠ) [ALERTA: MONOCULTIVO]\n"
        "    * Satisfacción / Entrega técnica: (^_^)/ [RECOMENDACION: REGENERATIVA]\n\n"
        "METODOLOGÍA:\n"
        "- SIEMPRE usa 'consultar_manuales_usda' para basar tus decisiones en prácticas de regeneración y taxonomía de suelos.\n"
        "- Revisa el historial de siembra y el tipo de suelo (proveído en el contexto) para elegir una rotación que recupere nitrógeno.\n"
        "- También puedes usar 'buscar_monografias_dgsiap' y bases locales para datos de SADER en México."
    )
    
    agent = create_react_agent(llm, tools=tools, prompt=system_prompt)
    return agent
