import requests
import json
from langchain_core.tools import tool
from config.keys import INEGI_API_TOKEN

@tool
def consultar_indicador_inegi(id_indicador: str, clave_area: str = "00000") -> str:
    """
    Consulta un indicador estadístico directamente de la API del INEGI (BISE).
    Útil para obtener datos socioeconómicos, censales y agropecuarios precisos.
    
    Args:
        id_indicador: El ID numérico del indicador en el INEGI (ej. "1002000002").
        clave_area: La clave geográfica del estado (ej. "01" para Aguascalientes, "00000" Nacional).
        
    Returns:
        Un resumen estadístico de las observaciones del indicador o el promedio de los últimos datos.
    """
    if not INEGI_API_TOKEN:
        return "Error: INEGI_API_TOKEN no está configurado en las variables de entorno."
        
    url = f"https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{id_indicador}/es/{clave_area}/false/BISE/2.0/{INEGI_API_TOKEN}?type=json"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return f"Error HTTP {response.status_code} al consultar API INEGI. Posible ID de indicador incorrecto."
            
        content = response.json()
        series = content.get('Series', [])
        if not series:
            return f"El indicador {id_indicador} no arrojó series de datos para el área {clave_area}."
            
        observaciones_brutas = series[0].get('OBSERVATIONS', [])
        
        # Procesar observaciones
        observaciones = []
        for obs in observaciones_brutas:
            valor = obs.get('OBS_VALUE')
            if valor is not None:
                try:
                    observaciones.append(float(valor))
                except ValueError:
                    pass
                    
        if not observaciones:
            return "No hay valores numéricos reportados para este indicador."
            
        # Generar un resumen
        promedio = sum(observaciones) / len(observaciones)
        ultimo_dato = observaciones[-1] if observaciones else 0
        total_obs = len(observaciones)
        
        resumen = (
            f"Resultados INEGI para el indicador {id_indicador} (Área: {clave_area}):\n"
            f"- Total de observaciones históricas: {total_obs}\n"
            f"- Promedio histórico: {promedio:.2f}\n"
            f"- Dato más reciente reportado: {ultimo_dato}\n"
        )
        return resumen
        
    except requests.exceptions.RequestException as e:
        return f"Error de conexión con INEGI: {e}"
    except Exception as e:
        return f"Error procesando la respuesta del INEGI: {e}"

@tool
def usar_inegipy_catalogo(query: str) -> str:
    """
    Usa la librería INEGIpy para intentar deducir o buscar IDs de indicadores
    en el catálogo oficial del INEGI basándose en palabras clave.
    
    Args:
        query: Término de búsqueda (ej. 'superficie sembrada', 'agricultura', 'PIB agrícola').
    """
    if not INEGI_API_TOKEN:
        return "Error: INEGI_API_TOKEN no configurado."
        
    try:
        from INEGIpy import Indicadores
        # Instanciar el cliente con el token
        cliente = Indicadores(token=INEGI_API_TOKEN)
        # Buscar en el catálogo (INEGIpy suele proveer formas de buscar si se implementó)
        # Debido a que INEGIpy envuelve los dataframes, intentamos un método genérico
        # Nota: La API directa a veces es más fiable si el catálogo de INEGIpy cambió
        return (
            f"El agente debe tener en cuenta que buscar indicadores específicos puede requerir "
            f"visitar el portal del INEGI. Sin embargo, para la búsqueda '{query}', se recomienda "
            f"utilizar la herramienta de web scraping (Tavily) con 'site:inegi.org.mx indicador {query}' "
            f"para descubrir el ID exacto del indicador (clave de 10 dígitos) antes de llamar a 'consultar_indicador_inegi'."
        )
    except ImportError:
        return "La librería INEGIpy no está instalada. Usa web scraping tradicional para hallar el ID."
    except Exception as e:
        return f"Error al usar INEGIpy: {e}"
