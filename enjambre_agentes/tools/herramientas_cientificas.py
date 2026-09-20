"""
Herramientas científicas para el Sistema Multiagente AgriPoli.

Adapta las herramientas de investigación de OptiAgent al dominio
agrícola-ecológico mexicano. Incluye:
  - Búsqueda académica (arXiv, SciELO, Semantic Scholar)
  - Enciclopedia rápida (Wikipedia ES)
  - Scraping profundo con Selenium como respaldo a Playwright
  - Cálculos agronómicos con SymPy
  - Formateador de citas científicas
"""
from __future__ import annotations

import requests
import sympy as sp
from sympy.parsing.sympy_parser import parse_expr
from langchain_core.tools import tool

from config.keys import TAVILY_API_KEY


# ─── Wikipedia ────────────────────────────────────────────────────────────────

@tool
def buscar_wikipedia_mx(query: str) -> str:
    """Busca definiciones, biografías o datos en Wikipedia en español.
    Ideal para flora, fauna, geografía y conceptos agronómicos de México.
    """
    try:
        import wikipedia
        wikipedia.set_lang("es")
        try:
            resumen = wikipedia.summary(query, sentences=4)
            return resumen
        except wikipedia.exceptions.DisambiguationError as e:
            # Si hay ambigüedad, intentar con la primera opción
            if e.options:
                resumen = wikipedia.summary(e.options[0], sentences=4)
                return f"(Resultado para '{e.options[0]}'):\n{resumen}"
            return f"Termino ambiguo. Opciones: {e.options[:5]}"
        except wikipedia.exceptions.PageError:
            return f"No se encontro '{query}' en Wikipedia en espanol."
    except Exception as e:
        return f"Error consultando Wikipedia: {e}"


# ─── arXiv / SciELO ──────────────────────────────────────────────────────────

@tool
def buscar_arxiv_agricola(query: str) -> str:
    """Busca papers académicos en arXiv sobre agricultura regenerativa,
    ecología de polinizadores, degradación de suelos o botánica aplicada.
    Devuelve títulos, resúmenes y URLs PDF.
    """
    try:
        import arxiv
        cliente = arxiv.Client()
        busqueda = arxiv.Search(
            query=query,
            max_results=4,
            sort_by=arxiv.SortCriterion.Relevance
        )
        resultados = []
        for paper in cliente.results(busqueda):
            resultados.append(
                f"Titulo: {paper.title}\n"
                f"Resumen: {paper.summary[:500]}...\n"
                f"PDF: {paper.pdf_url}\n"
            )
        return "\n---\n".join(resultados) if resultados else "Sin resultados en arXiv para esta consulta."
    except Exception as e:
        return f"Error consultando arXiv: {e}"


# ─── Semantic Scholar ─────────────────────────────────────────────────────────

@tool
def buscar_semantic_scholar_agricola(query: str) -> str:
    """Busca papers interdisciplinarios en Semantic Scholar cruzando
    agricultura, ecología, biología de polinizadores y ciencias del suelo.
    """
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={query}&limit=4&fields=title,authors,abstract,url,year"
    )
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            papers = data.get("data", [])
            if not papers:
                return "Sin papers en Semantic Scholar para esta consulta."
            resultados = []
            for p in papers:
                autores = ", ".join([a["name"] for a in p.get("authors", [])[:3]])
                resultados.append(
                    f"Titulo: {p.get('title', 'N/A')} ({p.get('year', '?')})\n"
                    f"Autores: {autores}\n"
                    f"Resumen: {str(p.get('abstract', 'Sin abstract.'))[:400]}...\n"
                    f"URL: {p.get('url', 'N/A')}"
                )
            return "\n---\n".join(resultados)
        return f"Error HTTP {response.status_code} en Semantic Scholar."
    except Exception as e:
        return f"Error de red en Semantic Scholar: {e}"


# ─── Selenium (respaldo a Playwright) ─────────────────────────────────────────

@tool
def lector_web_selenium(url: str) -> str:
    """Abre un navegador Chromium headless con Selenium para extraer el texto
    completo de una página web, incluyendo contenido renderizado con JavaScript.
    Usar como respaldo cuando Playwright no esté disponible o falle.
    """
    if not url or not url.startswith(("http://", "https://")):
        return "Error: URL invalida."
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        from bs4 import BeautifulSoup

        opciones = webdriver.ChromeOptions()
        opciones.add_argument("--headless")
        opciones.add_argument("--no-sandbox")
        opciones.add_argument("--disable-gpu")
        opciones.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )
        servicio = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=servicio, options=opciones)
        driver.set_page_load_timeout(30)
        driver.get(url)
        driver.implicitly_wait(5)
        html = driver.page_source
        driver.quit()

        sopa = BeautifulSoup(html, "html.parser")
        for tag in sopa(["script", "style", "noscript", "meta", "link", "header", "footer", "nav"]):
            tag.decompose()
        texto = sopa.get_text(separator=" ", strip=True)
        return texto[:15000]
    except Exception as e:
        return f"Error en Selenium scraping de {url}: {e}"


# ─── Cálculos Agronómicos (SymPy) ─────────────────────────────────────────────

@tool
def calcular_agronomia(expresion: str) -> str:
    """Evalúa y simplifica expresiones matemáticas agronómicas usando SymPy.
    Útil para: índice de cosecha, densidad de siembra, balance hídrico,
    necesidades de nitrógeno, ratio superficie/rendimiento.

    Ejemplo: 'rendimiento / (superficie * factor_conversion)'
    La entrada debe ser una expresión en sintaxis Python (usa ** para potencias).
    """
    try:
        expr = parse_expr(expresion)
        simplificada = sp.simplify(expr)
        latex_str = sp.latex(simplificada)
        return (
            f"Expresion original: {expresion}\n"
            f"Resultado simplificado: {simplificada}\n"
            f"LaTeX: $${latex_str}$$"
        )
    except Exception as e:
        return f"Error procesando la expresion '{expresion}': {e}. Usa sintaxis Python valida."


# ─── Formateador de Citas Científicas ────────────────────────────────────────

@tool
def formateador_citas_agricola(autor: str, titulo: str, anio: str, url: str, fuente: str = "") -> str:
    """Formatea una cita bibliográfica en norma APA/IEEE para documentos
    y reportes del Sistema Multiagente AgriPoli.

    Args:
        autor:  Nombre(s) del autor o institución.
        titulo: Título del documento, paper o dataset.
        anio:   Año de publicación.
        url:    URL o DOI del recurso.
        fuente: Nombre de la publicación/institución (opcional).
    """
    if fuente:
        cita_apa = f"{autor} ({anio}). {titulo}. {fuente}. Recuperado de: {url}"
    else:
        cita_apa = f"{autor} ({anio}). {titulo}. Recuperado de: {url}"
    cita_ieee = f'{autor}, "{titulo}," {anio}. [Online]. Disponible en: {url}'
    return f"APA:  {cita_apa}\nIEEE: {cita_ieee}"
