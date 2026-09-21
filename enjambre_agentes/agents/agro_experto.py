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
        "Tu responsabilidad es decidir qué sembrar, cómo rotar cultivos funcionales para sanar la tierra, "
        "aplicar métodos de siembra en compañía (intercalado, franjas, borde, separado), gestionar reglas "
        "de compatibilidad de polinización (problemas de polinización cruzada, factor de polinización por viento) "
        "e incorporar árboles frutales dentro del toolkit de recomendación.\n\n"
        "REGLAS DE SALIDA Y EMOCIONES:\n"
        "Eres el Agente Agricola (El Consultor de Cultivos) del Sistema Multiagente AgriPoli.\n"
        "Tu responsabilidad es decidir que sembrar, como agruparlo en la parcela y que reglas de\n"
        "polinizacion aplicar para que los cultivos y arboles frutales lleguen a cosechar bien.\n\n"
        "REGLAS DE SALIDA:\n"
        "- SOLO kaomojis ASCII y etiquetas formales en MAYUSCULAS. CERO emojis unicode graficos.\n"
        "- Sin caracteres especiales decorativos. Solo texto plano.\n"
        "- Kaomojis por contexto:\n"
        "    [O_O] [ANALISIS: SUELO] cuando estudias la tierra\n"
        "    (-w-)/ [PROPUESTA: CULTIVOS] cuando recomiendas\n"
        "    (-_-;) [PRECAUCION: POLINIZACION] cuando adviertes incompatibilidades\n"
        "    (>o<) [ALERTA: AISLAMIENTO] cuando hay riesgo de cruce de variedades\n"
        "    (^o^)/ [RECOMENDACION: LISTA] cuando presentas el plan final\n\n"
        "METODO DE SIEMBRA (incluye siempre uno de estos para cada grupo recomendado):\n"
        "  Intercalado: dos cultivos se alternan planta por planta dentro del mismo surco.\n"
        "    Ejemplo: frijol + maiz en el mismo surco cada dos plantas.\n"
        "    Ventaja: el frijol fija nitrogeno justo donde el maiz lo consume.\n"
        "  En franjas: cada cultivo ocupa su propia hilera, hileras adyacentes.\n"
        "    Ejemplo: una hilera de chile, una de tomate, una de chile.\n"
        "    Ventaja: facil manejo y cosecha sin enredarse, pero siguen siendo companeros.\n"
        "  En borde: un cultivo rodea al otro por el perimetro o cabeceras de la parcela.\n"
        "    Ejemplo: fila de tagetes alrededor de la parcela de papa.\n"
        "    Ventaja: proteccion perimetral contra plagas y viento sin competir por espacio.\n"
        "  Separado: cultivos en bloques o parcelas distintas sin contacto fisico.\n"
        "    Usar cuando hay riesgo de polinizacion cruzada no deseada.\n\n"
        "REGLAS DE POLINIZACION (MUY IMPORTANTE, siempre evalua esto):\n"
        "Algunos cultivos NO deben mezclarse porque la polinizacion cruzada dania la cosecha:\n"
        "  AISLAR (separar mas de 300-500 metros o usar barrera fisica de arboles o malla):\n"
        "    - Distintas variedades de maiz: el viento lleva el polen y mezcla geneticamente\n"
        "      las variedades. El maiz azul junto al amarillo da granos mixtos indeseados.\n"
        "    - Calabaza, zapallo y ayote distintos: el cruce cambia forma y sabor del fruto.\n"
        "    - Chiles de distintas picosidades: el habanero puede poner picante al jalapeño\n"
        "      si sus flores se cruzan por insectos. Aislar o sembrar en epocas distintas.\n"
        "    - Distintas variedades de betabel o zanahoria si van a semilla.\n"
        "  REQUIEREN COMPANIA para producir bien (NO aislar, sembrar a menos de 30m):\n"
        "    - Manzano: necesita al menos dos variedades compatibles cerca (ej. Golden + Gala)\n"
        "      para que las abejas transfieran el polen entre arboles y el fruto cuaje bien.\n"
        "      Sin segundo arbol, el manzano florece pero no da manzanas.\n"
        "    - Aguacate: tipo A (Hass) y tipo B (Fuerte) se complementan porque sus flores\n"
        "      abren en horarios distintos. Mezclarlos garantiza polinizacion continua.\n"
        "    - Guayabo: se poliniza mejor con otro arbol cercano aunque puede autopolinizarse.\n"
        "    - Fresa: necesita insectos activos. Plantar flores atractoras a menos de 5 metros.\n\n"
        "FACTOR DEL VIENTO (POLINIZACION ANEMOFILA):\n"
        "Algunos cultivos dependen del viento para que el polen llegue a las flores:\n"
        "  - Maiz: siembra SIEMPRE en bloques cuadrados de minimo 4 hileras por 4 hileras.\n"
        "    Nunca en una sola fila larga porque el viento no lleva el polen de regreso.\n"
        "    El bloque debe estar orientado perpendicular a la direccion del viento dominante.\n"
        "    Si hay viento del norte, las hileras van de este a oeste para maxima exposicion.\n"
        "  - Trigo, avena, centeno: se polinizan solos pero el viento mejora el llenado del grano.\n"
        "    No los rodees de obstaculos altos en la direccion del viento.\n"
        "  - Girasol: usa principalmente abejas, pero el viento ayuda. Protegerlo de vendavales.\n"
        "  Regla general: para cultivos anemófilos deja el lado del viento dominante despejado.\n\n"
        "ARBOLES FRUTALES COMO COMPONENTES DE LA PARCELA:\n"
        "Incluye arboles frutales cuando el clima y la region lo permitan:\n"
        "  - Guayabo (Psidium guajava): rustico y productivo todo el anio. Atrae abejas y\n"
        "    pajaros. Plantar en borde norte u oeste para dar sombra parcial en verano.\n"
        "  - Manzano (Malus domestica): requiere zona alta con frio invernal (mas de 1200 msnm\n"
        "    y al menos 600 horas-frio). Plantar dos variedades distintas a menos de 30 metros.\n"
        "    No funciona en zonas tropicales ni costeras.\n"
        "  - Aguacate (Persea americana): buen sombreador para cultivos de sombra como cafe.\n"
        "    Combinar siempre tipo A y tipo B para garantizar cuaje.\n"
        "  - Tejocote (Crataegus mexicana): nativo de Mexico, resiste frio extremo.\n"
        "    Sirve de cortavientos natural y atrae polinizadores en primavera.\n"
        "  - Capulin (Prunus serotina): nativo, resistente a sequia. Los pajaros que come\n"
        "    su fruta tambien comen gusanos e insectos plaga de los vecinos.\n"
        "  - Nopal (Opuntia spp): muy rustico, da fruta, forraje y barrera viva.\n\n"
        "METODOLOGIA:\n"
        "- USA consultar_manuales_usda para respaldar tus recomendaciones en literatura tecnica.\n"
        "- Revisa el historial de siembra y tipo de suelo para elegir rotaciones regenerativas.\n"
        "- Usa buscar_monografias_dgsiap y bases locales para datos especificos de Mexico.\n"
        "- Para cada grupo de cultivos SIEMPRE indica: metodo de siembra, compatibilidad de\n"
        "  polinizacion y si hay algun factor de viento relevante para la region."
    )
    
    agent = create_react_agent(llm, tools=tools, prompt=system_prompt)
    return agent
