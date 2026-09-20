"""
Nodo Investigador — El "explorador" del enjambre.

Recibe la región de México y realiza múltiples consultas de búsqueda temáticas
(polinizadores, agricultura, clima, flora, suelo) usando Tavily para recopilar
URLs relevantes de fuentes institucionales mexicanas.

Inspirado en web_tavily_node de OptiAgent/agentes.py, pero con consultas
multi-temáticas generadas dinámicamente por el LLM.
"""
from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import ScrapingState
from config.models import get_llm
from tools.search import buscar_tavily_mexico, buscar_conabio, buscar_literatura_agricola, explorador_enciclovida, buscar_datos_unam


# --- Schema para generar consultas de búsqueda optimizadas ---

class ConsultasBusqueda(BaseModel):
    """Consultas de búsqueda optimizadas generadas por el LLM para cada categoría temática."""
    queries_polinizadores: list[str] = Field(
        description="2-3 consultas de búsqueda sobre polinizadores nativos de la región"
    )
    queries_agricultura: list[str] = Field(
        description="2-3 consultas sobre agricultura, cultivos y rendimientos de la región"
    )
    queries_clima: list[str] = Field(
        description="2-3 consultas sobre clima, precipitación y temperatura de la región"
    )
    queries_flora: list[str] = Field(
        description="2-3 consultas sobre flora nativa, vegetación endémica de la región"
    )
    queries_suelo: list[str] = Field(
        description="2-3 consultas sobre tipo de suelo, edafología de la región"
    )
    especies_clave: list[str] = Field(
        description="2-3 nombres de especies clave (comunes o científicos) de polinizadores o flora nativa de esta región para buscar en Enciclovida",
        default_factory=list
    )


# --- Prompts del investigador ---

PROMPT_GENERAR_QUERIES = """Eres un investigador ecológico experto en México.

Dada la región "{region}", genera consultas de búsqueda web optimizadas para encontrar
información científica y gubernamental sobre los siguientes temas:

1. **Polinizadores**: Abejas, mariposas, colibríes, murciélagos nativos de la región.
   Prioriza términos como "polinizadores nativos", "abejas meliponas", "NOM-059".
   Asegúrate de incluir al menos una consulta con la palabra "UNAM" o "IBUNAM" (ej. "polinizadores UNAM").
   
2. **Agricultura**: Cultivos tradicionales y comerciales, rendimientos, ciclos agrícolas.
   Prioriza términos como "milpa", "cultivos temporalidad", "SAGARPA", "INIFAP", "INEGI".
   
3. **Clima**: Clasificación climática, precipitación, temperatura, riesgos.
   Prioriza términos como "clima Köppen", "precipitación anual", "SMN CONAGUA".
   
4. **Flora**: Vegetación nativa, especies endémicas, plantas nectaríferas y melíferas.
   Prioriza términos como "flora endémica", "vegetación", "CONABIO".
   Asegúrate de incluir al menos una consulta con la palabra "UNAM" o "IBUNAM" (ej. "flora nativa IBUNAM").
   
5. **Suelo**: Tipos de suelo, pH, materia orgánica, problemas edafológicos.
   Prioriza términos como "edafología", "tipo suelo", "INEGI carta edafológica".

Además, identifica 2-3 especies clave (nombres comunes o científicos de plantas 
o polinizadores emblemáticos de la región) y colócalos en `especies_clave`.

Las consultas deben ser en ESPAÑOL y específicas para México.
Incluye el nombre de la región en cada consulta.
"""

PROMPT_INVESTIGADOR = """Eres el Agente Investigador del enjambre AniIta.
Tu tarea es buscar URLs relevantes sobre la región "{region}" de México.

Usa las herramientas de búsqueda disponibles para encontrar información de fuentes
institucionales mexicanas (CONABIO, SADER, INIFAP, iNaturalist, UNAM, INEGI).

Para CADA categoría temática, realiza las búsquedas proporcionadas y recopila
todas las URLs encontradas. Prioriza fuentes .gob.mx, .org.mx, .edu.mx.
"""


def _extraer_urls(texto: str) -> list[str]:
    """Extrae URLs únicas de un bloque de texto."""
    patron = r'https?://[^\s<>"\')\],]+'
    urls = re.findall(patron, texto)
    # Limpiar y deduplicar
    urls_limpias = []
    seen = set()
    for url in urls:
        # Remover caracteres finales que no son parte de la URL
        url = url.rstrip(".,;:!?)")
        if url not in seen:
            seen.add(url)
            urls_limpias.append(url)
    return urls_limpias


def investigador_node(state: ScrapingState) -> dict[str, Any]:
    """Nodo Investigador: busca URLs relevantes para la región especificada.
    
    Flujo:
    1. El LLM genera consultas de búsqueda optimizadas por categoría (with_structured_output).
    2. Para cada categoría, ejecuta las consultas con las herramientas Tavily.
    3. Extrae y clasifica las URLs descubiertas por categoría temática.
    """
    region = state["region"]
    provider = state["provider"]
    model_name = state.get("llm_model_name")
    
    print(f"\n{'='*60}")
    print(f"[🔍 Investigador] Iniciando investigación para: {region}")
    print(f"[🔍 Investigador] Proveedor LLM: {provider}")
    print(f"{'='*60}")
    
    llm = get_llm(provider, model_name)
    errores = []
    
    # --- Paso 1: Generar consultas optimizadas con structured output ---
    print("[🔍 Investigador] Generando consultas de búsqueda optimizadas...")
    
    try:
        llm_structured = llm.with_structured_output(ConsultasBusqueda)
        consultas = llm_structured.invoke(
            PROMPT_GENERAR_QUERIES.format(region=region)
        )
    except Exception as e:
        print(f"[🔍 Investigador] Error en structured output: {e}. Usando queries por defecto.")
        errores.append(f"Investigador: Error generando queries dinámicas: {e}")
        consultas = ConsultasBusqueda(
            queries_polinizadores=[
                f"polinizadores nativos {region} México CONABIO",
                f"abejas mariposas colibríes {region}",
            ],
            queries_agricultura=[
                f"cultivos agricultura {region} México SAGARPA INIFAP",
                f"rendimiento agrícola {region} hectárea",
            ],
            queries_clima=[
                f"clima precipitación temperatura {region} México",
                f"clasificación climática Köppen {region}",
            ],
            queries_flora=[
                f"flora nativa vegetación endémica {region} México",
                f"plantas nectaríferas melíferas {region} CONABIO",
            ],
            queries_suelo=[
                f"tipo suelo edafología {region} México INEGI",
                f"erosión materia orgánica suelo {region}",
            ],
            especies_clave=["Abeja melipona", "Maíz criollo"]
        )
    
    # --- Paso 1.5: Explorar especies clave en Enciclovida ---
    urls_enciclovida = []
    if consultas.especies_clave:
        print(f"\n[🔍 Investigador] Explorando {len(consultas.especies_clave)} especies clave en Enciclovida...")
        for especie in consultas.especies_clave:
            print(f"  → Buscando: '{especie}'")
            try:
                res_enciclovida = explorador_enciclovida.invoke({"query": especie})
                urls_extraidas = _extraer_urls(res_enciclovida)
                urls_enciclovida.extend(urls_extraidas)
                print(f"  ✓ {len(urls_extraidas)} URLs de API encontradas")
            except Exception as e:
                print(f"  ✗ Error buscando especie '{especie}': {e}")
                errores.append(f"Investigador/Especie: Error en '{especie}': {e}")
    
    # --- Paso 2: Ejecutar búsquedas por categoría ---
    categorias = {
        "polinizadores": (consultas.queries_polinizadores, "polinizadores"),
        "agricultura": (consultas.queries_agricultura, "agricultura"),
        "clima": (consultas.queries_clima, "clima"),
        "flora": (consultas.queries_flora, "flora"),
        "suelo": (consultas.queries_suelo, "suelo"),
    }
    
    resultados_urls: dict[str, list[str]] = {k: [] for k in categorias}
    
    for categoria, (queries, tema) in categorias.items():
        print(f"\n[🔍 Investigador] Buscando: {categoria.upper()}")
        
        for query in queries:
            print(f"  → Query: '{query}'")
            try:
                # Usar herramienta especializada según categoría
                if categoria == "polinizadores" or categoria == "flora":
                    # Alternamos entre CONABIO y UNAM para más riqueza
                    if "UNAM" in query.upper() or "IBUNAM" in query.upper():
                        resultado = buscar_datos_unam.invoke({"query": query})
                    else:
                        resultado = buscar_conabio.invoke({"query": query})
                elif categoria == "agricultura":
                    resultado = buscar_literatura_agricola.invoke({"query": query})
                else:
                    resultado = buscar_tavily_mexico.invoke({"query": query, "tema": tema})
                
                # Extraer URLs del resultado
                urls = _extraer_urls(resultado)
                resultados_urls[categoria].extend(urls)
                print(f"  ✓ Encontradas {len(urls)} URLs")
                
            except Exception as e:
                error_msg = f"Error buscando '{query}': {e}"
                print(f"  ✗ {error_msg}")
                errores.append(f"Investigador/{categoria}: {error_msg}")
                
        # Agregar URLs de Enciclovida a las categorías correspondientes
        if categoria in ["polinizadores", "flora"] and urls_enciclovida:
            resultados_urls[categoria].extend(urls_enciclovida)
    
    # Deduplicar URLs por categoría
    for cat in resultados_urls:
        resultados_urls[cat] = list(dict.fromkeys(resultados_urls[cat]))
    
    total_urls = sum(len(v) for v in resultados_urls.values())
    print(f"\n[🔍 Investigador] Total URLs descubiertas: {total_urls}")
    for cat, urls in resultados_urls.items():
        print(f"  {cat}: {len(urls)} URLs")
    
    return {
        "urls_polinizadores": resultados_urls["polinizadores"],
        "urls_agricultura": resultados_urls["agricultura"],
        "urls_clima": resultados_urls["clima"],
        "urls_flora": resultados_urls["flora"],
        "urls_suelo": resultados_urls["suelo"],
        "errores": errores,
    }
