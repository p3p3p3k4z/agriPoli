"""
Herramientas de búsqueda web especializadas en fuentes mexicanas.

Usa TavilySearchResults con filtros de dominio para priorizar fuentes
institucionales y científicas de México: CONABIO, SADER, iNaturalist,
EncicloVida, UNAM, SciELO, INEGI, INIFAP.
"""
from __future__ import annotations
from typing import Any

from langchain_core.tools import tool

try:
    from langchain_tavily import TavilySearch as TavilyToolClass
except ImportError:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from langchain_community.tools.tavily_search import TavilySearchResults as TavilyToolClass

from config.keys import TAVILY_API_KEY


def _get_tavily(max_results: int = 5):
    """Obtiene una instancia de búsqueda Tavily configurada."""
    if not TAVILY_API_KEY:
        raise ValueError("Se requiere TAVILY_API_KEY en .env para realizar búsquedas.")
    return TavilyToolClass(max_results=max_results, tavily_api_key=TAVILY_API_KEY)


def _extraer_resultados_tavily(res: Any) -> list[dict]:
    """Extrae la lista de resultados tanto si Tavily devuelve dict como si devuelve list."""
    if isinstance(res, dict) and "results" in res:
        return res["results"]
    if isinstance(res, list):
        return res
    return []


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
    
    from config.agri_logger import log_flujo, log_herramienta
    log_flujo("agente", "tavily", f"Consultando Tavily Search ({tema}): {query[:50]}...", kaomoji="[>_<]")
    log_herramienta("TAVILY_SEARCH", f"Tema: {tema} | Consulta: '{query}'", kaomoji="[>_<]")
    
    filtro_sitios = sitios_por_tema.get(tema, sitios_por_tema["general"])
    query_enriquecida = f"México {query} {filtro_sitios}"
    
    tavily = _get_tavily(max_results=5)
    try:
        raw_res = tavily.invoke({"query": query_enriquecida})
        resultados = _extraer_resultados_tavily(raw_res)
        texto = ""
        urls_encontradas = []
        for r in resultados:
            url = r.get("url", "sin URL")
            contenido = r.get("content", "sin contenido")
            urls_encontradas.append(url)
            texto += f"URL: {url}\nContenido: {contenido}\n\n---\n\n"
        
        if not texto.strip():
            log_herramienta("TAVILY_SEARCH", f"Sin resultados para: '{query}'", kaomoji="(-_-;)")
            return f"No se encontraron resultados para '{query}' con tema '{tema}'."
        log_herramienta("TAVILY_SEARCH", f"Exito: {len(resultados)} fuentes encontradas ({', '.join(urls_encontradas[:2])})", kaomoji="(^_^)/")
        return texto
    except Exception as e:
        log_herramienta("TAVILY_SEARCH", f"Error de busqueda: {e}", kaomoji="[X_X]")
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
    from config.agri_logger import log_flujo, log_herramienta
    log_flujo("agente", "tavily_conabio", f"Consultando biodiversidad CONABIO: {query[:50]}...", kaomoji="[>_<]")
    log_herramienta("TAVILY_CONABIO", f"Consulta: '{query}'", kaomoji="[>_<]")

    query_enriquecida = (
        f"{query} México biodiversidad "
        f"site:conabio.gob.mx OR site:enciclovida.mx OR site:inaturalist.org OR "
        f"site:biodiversidad.gob.mx OR site:naturalista.mx"
    )
    
    tavily = _get_tavily(max_results=5)
    try:
        raw_res = tavily.invoke({"query": query_enriquecida})
        resultados = _extraer_resultados_tavily(raw_res)
        texto = ""
        urls_encontradas = []
        for r in resultados:
            url = r.get("url", "sin URL")
            contenido = r.get("content", "sin contenido")
            urls_encontradas.append(url)
            texto += f"[CONABIO/Biodiversidad] URL: {url}\nContenido: {contenido}\n\n---\n\n"
        
        if not texto.strip():
            log_herramienta("TAVILY_CONABIO", f"Sin datos para: '{query}'", kaomoji="(-_-;)")
            return f"No se encontraron datos de biodiversidad para: '{query}'."
        log_herramienta("TAVILY_CONABIO", f"Exito: {len(resultados)} registros ({', '.join(urls_encontradas[:2])})", kaomoji="(^_^)/")
        return texto
    except Exception as e:
        log_herramienta("TAVILY_CONABIO", f"Error: {e}", kaomoji="[X_X]")
        return f"Error en búsqueda CONABIO: {e}"


@tool
def buscar_literatura_agricola(query: str) -> str:
    """Busca información agrícola en repositorios oficiales de SADER/SAGARPA, INIFAP,
    SciELO México y revistas de la UNAM / Chapingo.
    
    Ideal para: datos de cultivos, rendimientos, prácticas agrícolas,
    suelos, fertilización, agroecología.
    
    Args:
        query: Consulta agrícola (ej. 'cultivos milpa Mixteca rendimiento').
    """
    from config.agri_logger import log_flujo, log_herramienta
    log_flujo("agente", "tavily_agricola", f"Buscando literatura e instituciones agricolas: {query[:50]}...", kaomoji="[>_<]")
    log_herramienta("TAVILY_AGRICOLA", f"Consulta: '{query}'", kaomoji="[>_<]")

    query_enriquecida = (
        f"{query} México agricultura "
        f"site:gob.mx/agricultura OR site:gob.mx/sader OR site:inifap.gob.mx OR "
        f"site:scielo.org.mx OR site:revistas.unam.mx OR site:chapingo.mx"
    )
    
    tavily = _get_tavily(max_results=5)
    try:
        raw_res = tavily.invoke({"query": query_enriquecida})
        resultados = _extraer_resultados_tavily(raw_res)
        texto = ""
        urls_encontradas = []
        for r in resultados:
            url = r.get("url", "sin URL")
            contenido = r.get("content", "sin contenido")
            urls_encontradas.append(url)
            texto += f"[Agricultura MX] URL: {url}\nContenido: {contenido}\n\n---\n\n"
        
        if not texto.strip():
            log_herramienta("TAVILY_AGRICOLA", f"Sin datos agricolas para: '{query}'", kaomoji="(-_-;)")
            return f"No se encontraron datos agrícolas para: '{query}'."
        log_herramienta("TAVILY_AGRICOLA", f"Exito: {len(resultados)} fuentes tecnicas ({', '.join(urls_encontradas[:2])})", kaomoji="(^_^)/")
        return texto
    except Exception as e:
        log_herramienta("TAVILY_AGRICOLA", f"Error: {e}", kaomoji="[X_X]")
        return f"Error en búsqueda agrícola: {e}"


@tool
def buscar_estudios_suelo(query: str) -> str:
    """Busca estudios de suelos, técnicas de muestreo, perfiles edafológicos,
    texturas y fertilidad directamente en fuentes oficiales de México (SADER, INIFAP, INEGI).
    
    Ideal para: requerimientos de muestreo con barrena, análisis químico NPK,
    salinidad, pH, enmiendas orgánicas y degradación del suelo.
    
    Args:
        query: Consulta edafológica (ej. 'estudios de suelos muestreo barrena SADER').
    """
    from config.agri_logger import log_flujo, log_herramienta
    log_flujo("agente", "tavily_suelo", f"Buscando estudios edafologicos: {query[:50]}...", kaomoji="[>_<]")
    log_herramienta("TAVILY_SUELO", f"Consulta: '{query}'", kaomoji="[>_<]")

    query_enriquecida = (
        f"{query} México suelo edafología "
        f"site:gob.mx/agricultura OR site:inifap.gob.mx OR site:inegi.org.mx OR site:gob.mx/semarnat"
    )
    
    tavily = _get_tavily(max_results=5)
    try:
        raw_res = tavily.invoke({"query": query_enriquecida})
        resultados = _extraer_resultados_tavily(raw_res)
        texto = ""
        urls_encontradas = []
        for r in resultados:
            url = r.get("url", "sin URL")
            contenido = r.get("content", "sin contenido")
            urls_encontradas.append(url)
            texto += f"[Suelo/Edafología MX] URL: {url}\nContenido: {contenido}\n\n---\n\n"
        
        if not texto.strip():
            log_herramienta("TAVILY_SUELO", f"Sin estudios para: '{query}'", kaomoji="(-_-;)")
            return f"No se encontraron estudios de suelo para: '{query}'."
        log_herramienta("TAVILY_SUELO", f"Exito: {len(resultados)} estudios ({', '.join(urls_encontradas[:2])})", kaomoji="(^_^)/")
        return texto
    except Exception as e:
        log_herramienta("TAVILY_SUELO", f"Error: {e}", kaomoji="[X_X]")
        return f"Error en búsqueda de suelos: {e}"


@tool
def buscar_antecedentes_cultivo(consulta: str) -> str:
    """Busca antecedentes cientificos, historicos y tecnicos de grupos de cultivos en Mexico usando Tavily.
    
    Consulta repositorios cientificos y tecnicos (INIFAP, Chapingo, UNAM, CIMMYT, SciELO Mexico)
    para validar que los grupos de cultivos (ej. milpa, maiz-frijol-calabaza, frutales y leguminosas)
    cuentan con antecedentes documentados de exito, viabilidad y beneficios.
    
    Args:
        consulta: Consulta de antecedentes (ej. 'antecedentes asociacion cultivos maiz frijol calabaza mexico').
    """
    from config.agri_logger import log_flujo, log_herramienta
    log_flujo("agente", "tavily_antecedentes", f"Investigando antecedentes cientificos en Tavily: {consulta[:50]}...", kaomoji="[>_<]")
    log_herramienta("TAVILY_ANTECEDENTES", f"Consulta: '{consulta}'", kaomoji="[>_<]")

    query_enriquecida = (
        f"{consulta} México antecedentes agronómicos investigación "
        f"site:scielo.org.mx OR site:inifap.gob.mx OR site:cimmyt.org OR site:chapingo.mx OR site:revistas.unam.mx OR site:gob.mx/agricultura"
    )

    tavily = _get_tavily(max_results=5)
    try:
        raw_res = tavily.invoke({"query": query_enriquecida})
        resultados = _extraer_resultados_tavily(raw_res)
        texto = ""
        urls_encontradas = []
        for r in resultados:
            url = r.get("url", "sin URL")
            contenido = r.get("content", "sin contenido")
            urls_encontradas.append(url)
            texto += f"[Antecedente Cientifico MX] URL: {url}\nContenido: {contenido}\n\n---\n\n"

        if not texto.strip():
            log_herramienta("TAVILY_ANTECEDENTES", f"Sin antecedentes para: '{consulta}'", kaomoji="(-_-;)")
            return f"No se encontraron antecedentes documentados para: '{consulta}'."
        log_herramienta("TAVILY_ANTECEDENTES", f"Exito: {len(resultados)} articulos/manuales ({', '.join(urls_encontradas[:2])})", kaomoji="(^_^)/")
        return texto
    except Exception as e:
        log_herramienta("TAVILY_ANTECEDENTES", f"Error: {e}", kaomoji="[X_X]")
        return f"Error en búsqueda de antecedentes: {e}"


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
        raw_res = tavily.invoke({"query": query_enriquecida})
        resultados = _extraer_resultados_tavily(raw_res)
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
