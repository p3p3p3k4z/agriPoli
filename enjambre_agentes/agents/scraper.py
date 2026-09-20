"""
Nodo Scraper & RAG — El "recolector" del enjambre.

Visita las URLs descubiertas por el Investigador, extrae el contenido
(HTML renderizado o texto de PDFs) y aplica RAG temporal si el texto
es muy extenso.

Inspirado en web_scraper_node de OptiAgent/agentes.py, pero con
Playwright en lugar de Selenium y procesamiento de PDFs.
"""
from __future__ import annotations

from typing import Any

from agents.state import ScrapingState
from tools.scraper import lector_web_playwright, lector_pdf_web, lector_json_api, detectar_tipo_contenido
from tools.rag import vectorizar_temporal, necesita_rag

# Máximo de URLs a scrapear por categoría (para controlar tiempo/costos)
MAX_URLS_POR_CATEGORIA = 4


def _scrapear_urls(urls: list[str], max_urls: int = MAX_URLS_POR_CATEGORIA) -> tuple[str, list[str]]:
    """Scrapea una lista de URLs y devuelve el contenido concatenado + errores.
    
    Args:
        urls: Lista de URLs a visitar.
        max_urls: Máximo de URLs a procesar.
        
    Returns:
        Tupla de (contenido_concatenado, lista_de_errores).
    """
    contenidos = []
    errores = []
    
    for url in urls[:max_urls]:
        try:
            # Detectar tipo de contenido
            tipo = detectar_tipo_contenido(url)
            
            if tipo == "pdf":
                print(f"    [._.] [DOC: PDF] Extrayendo PDF: {url[:80]}...")
                contenido = lector_pdf_web.invoke({"url": url})
            elif tipo == "json":
                print(f"    [._.] [DOC: JSON] Extrayendo JSON API: {url[:80]}...")
                contenido = lector_json_api.invoke({"url": url})
            else:
                print(f"    (>_<) [DOC: HTML] Scrapeando HTML: {url[:80]}...")
                contenido = lector_web_playwright.invoke({"url": url})
            
            if contenido and not contenido.startswith("Error"):
                contenidos.append(f"[Fuente: {url}]\n{contenido}")
            else:
                errores.append(f"Sin contenido útil de: {url}")
                
        except Exception as e:
            error_msg = f"Error scrapeando {url}: {e}"
            print(f"    [X_X] [ERROR] {error_msg}")
            errores.append(error_msg)
    
    return "\n\n---\n\n".join(contenidos), errores


def scraper_node(state: ScrapingState) -> dict[str, Any]:
    """Nodo Scraper & RAG: visita URLs descubiertas y extrae contenido.
    
    Flujo por categoría:
    1. Detecta tipo de contenido (HTML vs PDF) vía HEAD request.
    2. HTML → Playwright headless para renderizar y extraer texto limpio.
    3. PDF → Descarga + PyPDF para extraer texto.
    4. Si el texto concatenado > 10,000 chars → RAG temporal (FAISS en memoria).
    5. Almacena el contenido procesado en el estado compartido.
    """
    region = state["region"]
    provider = state["provider"]
    
    print(f"\n{'='*60}")
    print(f"(>_<) [AGENTE: SCRAPER & RAG] Extrayendo contenido para: {region}")
    print(f"{'='*60}")
    
    errores_totales = list(state.get("errores", []))
    
    # Categorías y sus URLs correspondientes del estado
    categorias = {
        "polinizadores": state.get("urls_polinizadores", []),
        "agricultura": state.get("urls_agricultura", []),
        "clima": state.get("urls_clima", []),
        "flora": state.get("urls_flora", []),
        "suelo": state.get("urls_suelo", []),
    }
    
    contenidos: dict[str, str] = {}
    textos_para_rag: list[str] = []
    
    for categoria, urls in categorias.items():
        print(f"\n(>_<) [AGENTE: SCRAPER] Procesando {categoria.upper()} ({len(urls)} URLs)")
        
        if not urls:
            print(f"  (¬_¬) [ALERTA] Sin URLs para {categoria}. Saltando.")
            contenidos[categoria] = f"No se encontraron URLs para {categoria} en la región {region}."
            continue
        
        # Scrapear las URLs
        contenido, errores = _scrapear_urls(urls)
        errores_totales.extend(
            [f"Scraper/{categoria}: {e}" for e in errores]
        )
        
        if contenido:
            # Verificar si necesita RAG (textos muy extensos)
            if necesita_rag(contenido):
                print(f"  [O_O] [RAG: VECTORIZADOR] Contenido extenso ({len(contenido):,} chars). Aplicando RAG...")
                query_rag = f"{categoria} {region} México datos específicos"
                contenido_comprimido = vectorizar_temporal(
                    textos=[contenido],
                    query=query_rag,
                    provider=provider,
                )
                contenidos[categoria] = contenido_comprimido
                textos_para_rag.append(contenido)
            else:
                contenidos[categoria] = contenido
        else:
            contenidos[categoria] = f"No se pudo extraer contenido útil para {categoria}."
    
    # RAG consolidado sobre todos los textos extensos
    contenido_rag = ""
    if textos_para_rag:
        print(f"\n(>_<) [AGENTE: SCRAPER] Aplicando RAG consolidado sobre {len(textos_para_rag)} textos extensos...")
        contenido_rag = vectorizar_temporal(
            textos=textos_para_rag,
            query=f"datos ecológicos agrícolas polinizadores cultivos {region} México",
            provider=provider,
        )
    
    total_chars = sum(len(v) for v in contenidos.values()) + len(contenido_rag)
    print(f"\n(^_^)/ [OK] [SCRAPER] Extracción completa. Total contenido: {total_chars:,} chars")
    
    return {
        "contenido_polinizadores": contenidos.get("polinizadores", ""),
        "contenido_agricultura": contenidos.get("agricultura", ""),
        "contenido_clima": contenidos.get("clima", ""),
        "contenido_flora": contenidos.get("flora", ""),
        "contenido_suelo": contenidos.get("suelo", ""),
        "contenido_rag": contenido_rag,
        "errores": errores_totales,
    }
