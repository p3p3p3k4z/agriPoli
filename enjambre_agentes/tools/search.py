"""
Herramientas de búsqueda web especializadas en fuentes mexicanas.

Usa TavilySearchResults con filtros de dominio para priorizar fuentes
institucionales y científicas de México: CONABIO, SADER, iNaturalist,
EncicloVida, UNAM, SciELO, INEGI, INIFAP.
"""
from __future__ import annotations

from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults

from config.keys import TAVILY_API_KEY


def _get_tavily(max_results: int = 5) -> TavilySearchResults:
    """Obtiene una instancia de TavilySearchResults configurada."""
    if not TAVILY_API_KEY:
        raise ValueError("Se requiere TAVILY_API_KEY en .env para realizar búsquedas.")
    return TavilySearchResults(max_results=max_results, tavily_api_key=TAVILY_API_KEY)


@tool
def buscar_tavily_mexico(query: str, tema: str) -> str:
    """Busca información ecológica y agrícola de México en la web usando Tavily.
    
    Prioriza fuentes institucionales mexicanas añadiendo contexto regional 
    y temático a la consulta.
    
    Args:
        query: Consulta de búsqueda (ej. 'polinizadores nativos región Mixteca').
        tema: Categoría temática, una de: 'polinizadores', 'agricultura', 'clima', 
              'flora', 'suelo', 'general'.
    """
    # Mapeo de temas a sitios prioritarios
    sitios_por_tema = {
        "polinizadores": "site:conabio.gob.mx OR site:enciclovida.mx OR site:inaturalist.org",
        "agricultura": "site:gob.mx/sader OR site:inifap.gob.mx OR site:scielo.org.mx",
        "clima": "site:smn.conagua.gob.mx OR site:inegi.org.mx OR site:gob.mx/conagua",
        "flora": "site:conabio.gob.mx OR site:enciclovida.mx OR site:biodiversidad.gob.mx",
        "suelo": "site:inegi.org.mx OR site:gob.mx/semarnat OR site:fao.org",
        "general": "site:conabio.gob.mx OR site:gob.mx OR site:unam.mx",
    }
    
    filtro_sitios = sitios_por_tema.get(tema, sitios_por_tema["general"])
    query_enriquecida = f"México {query} {filtro_sitios}"
    
    tavily = _get_tavily(max_results=5)
    try:
        resultados = tavily.invoke({"query": query_enriquecida})
        texto = ""
        for r in resultados:
            url = r.get("url", "sin URL")
            contenido = r.get("content", "sin contenido")
            texto += f"URL: {url}\nContenido: {contenido}\n\n---\n\n"
        
        if not texto.strip():
            return f"No se encontraron resultados para '{query}' con tema '{tema}'."
        return texto
    except Exception as e:
        return f"Error en búsqueda Tavily: {e}"


@tool
def buscar_conabio(query: str) -> str:
    """Búsqueda especializada en biodiversidad mexicana a través de CONABIO, 
    EncicloVida e iNaturalist México.
    
    Ideal para: polinizadores, flora nativa, fauna, especies endémicas,
    estatus de conservación NOM-059.
    
    Args:
        query: Consulta sobre biodiversidad (ej. 'abejas nativas Oaxaca').
    """
    query_enriquecida = (
        f"{query} México biodiversidad "
        f"site:conabio.gob.mx OR site:enciclovida.mx OR site:inaturalist.org OR "
        f"site:biodiversidad.gob.mx OR site:naturalista.mx"
    )
    
    tavily = _get_tavily(max_results=5)
    try:
        resultados = tavily.invoke({"query": query_enriquecida})
        texto = ""
        for r in resultados:
            url = r.get("url", "sin URL")
            contenido = r.get("content", "sin contenido")
            texto += f"[CONABIO/Biodiversidad] URL: {url}\nContenido: {contenido}\n\n---\n\n"
        
        if not texto.strip():
            return f"No se encontraron datos de biodiversidad para: '{query}'."
        return texto
    except Exception as e:
        return f"Error en búsqueda CONABIO: {e}"


@tool
def buscar_literatura_agricola(query: str) -> str:
    """Busca información agrícola en repositorios de SAGARPA/SADER, INIFAP,
    SciELO México y revistas de la UNAM.
    
    Ideal para: datos de cultivos, rendimientos, prácticas agrícolas,
    suelos, tecnificación, agroecología.
    
    Args:
        query: Consulta agrícola (ej. 'cultivos milpa Mixteca rendimiento').
    """
    query_enriquecida = (
        f"{query} México agricultura "
        f"site:gob.mx/sader OR site:inifap.gob.mx OR site:scielo.org.mx OR "
        f"site:revistas.unam.mx OR site:chapingo.mx"
    )
    
    tavily = _get_tavily(max_results=5)
    try:
        resultados = tavily.invoke({"query": query_enriquecida})
        texto = ""
        for r in resultados:
            url = r.get("url", "sin URL")
            contenido = r.get("content", "sin contenido")
            texto += f"[Agricultura MX] URL: {url}\nContenido: {contenido}\n\n---\n\n"
        
        if not texto.strip():
            return f"No se encontraron datos agrícolas para: '{query}'."
        return texto
    except Exception as e:
        return f"Error en búsqueda agrícola: {e}"


@tool
def explorador_enciclovida(query: str) -> str:
    """Busca especies por nombre común o científico directamente en la API de EncicloVida.
    
    Genera automáticamente las URLs directas a los endpoints JSON de observaciones
    y ejemplares del SNIB para que el Scraper las recoja.
    Usa esto cuando necesites datos específicos (taxonomía, observaciones) 
    de una planta, polinizador o animal.
    
    Args:
        query: Nombre común o científico (ej. 'Abeja melipona', 'Croton').
    """
    import urllib.parse
    import requests
    
    query_encoded = urllib.parse.quote(query)
    # Búsqueda rápida de EncicloVida
    api_url = f"https://enciclovida.mx/busquedas/resultados?busqueda=basica&nombre={query_encoded}&commit=Buscar&format=json"
    
    try:
        resp = requests.get(api_url, timeout=10)
        if resp.status_code != 200:
            return f"Error HTTP {resp.status_code} al buscar en Enciclovida."
            
        data = resp.json()
        
        # El JSON de búsqueda suele retornar una lista en el campo 'taxa' o array directo
        resultados = data if isinstance(data, list) else data.get('taxa', [])
        
        if not resultados:
            return f"No se encontraron resultados directos para '{query}' en Enciclovida."
            
        # Tomar el primer resultado más relevante
        especie = resultados[0]
        especie_id = especie.get('IdNombre', '')
        nombre_cientifico = especie.get('NombreCompleto', 'Desconocido')
        nombre_comun = especie.get('nombre_comun_principal', 'Desconocido')
        
        # Generar URLs estructuradas para el Scraper
        url_especie = f"https://enciclovida.mx/especies/{especie_id}"
        url_json = f"https://enciclovida.mx/especies/{especie_id}/consulta-registros.json?coleccion=naturalista&formato=json"
        
        # Generar URL del SNIB (usualmente usan un formato diferente de ID, pero el scraper lo intentará)
        # La URL general para la ficha técnica
        
        resumen = (
            f"Especie Encontrada:\n"
            f"- Nombre científico: {nombre_cientifico}\n"
            f"- Nombre común: {nombre_comun}\n"
            f"- URL Ficha (HTML): {url_especie}\n"
            f"- URL Observaciones (JSON): {url_json}\n"
        )
        return resumen
        
    except Exception as e:
        return f"Error consultando API de Enciclovida: {e}"

@tool
def buscar_datos_unam(query: str) -> str:
    """Búsqueda especializada en el Portal de Datos Abiertos de la UNAM, 
    Instituto de Biología (IBUNAM) y repositorios académicos de la UNAM.
    
    Ideal para: colecciones de insectos polinizadores, herbarios, registros 
    biológicos científicos y catálogos florísticos.
    
    Args:
        query: Consulta sobre biodiversidad (ej. 'colección nacional insectos polinizadores', 'herbario MEXU').
    """
    query_enriquecida = (
        f"{query} "
        f"site:datosabiertos.unam.mx OR site:ib.unam.mx OR site:datos.ib.unam.mx"
    )
    
    tavily = _get_tavily(max_results=5)
    try:
        resultados = tavily.invoke({"query": query_enriquecida})
        texto = ""
        for r in resultados:
            url = r.get("url", "sin URL")
            contenido = r.get("content", "sin contenido")
            texto += f"[UNAM/DatosAbiertos] URL: {url}\nContenido: {contenido}\n\n---\n\n"
        
        if not texto.strip():
            return f"No se encontraron datos en la UNAM para: '{query}'."
        return texto
    except Exception as e:
        return f"Error en búsqueda UNAM: {e}"
