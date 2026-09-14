"""
Herramientas de scraping web y extracción de PDFs para el Enjambre de Agentes.

- lector_web_playwright: Renderiza páginas con JS usando Playwright headless.
- lector_pdf_web: Descarga y extrae texto de PDFs gubernamentales/científicos.

Inspirado en OptiAgent/herramientas_optica.py:lector_web_profundo,
pero usando Playwright en lugar de Selenium para mejor estabilidad.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import json
import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool


@tool
def lector_web_playwright(url: str) -> str:
    """Extrae el contenido de texto completo de una página web usando Playwright headless.
    
    Renderiza JavaScript, espera a que cargue el DOM dinámico, y devuelve
    el texto limpio sin scripts, estilos ni elementos de navegación.
    Ideal para sitios gubernamentales mexicanos con mucho JS (CONABIO, SADER).
    
    Args:
        url: URL completa de la página a scrapear.
        
    Returns:
        Texto limpio extraído de la página (máximo 15,000 caracteres).
    """
    if not url or not url.startswith(("http://", "https://")):
        return "Error: URL inválida. Debe comenzar con http:// o https://."
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu"],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                )
            )
            page = context.new_page()
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # Esperar un poco para contenido dinámico
            page.wait_for_timeout(3000)
            
            html_crudo = page.content()
            browser.close()
        
        # Limpiar HTML con BeautifulSoup
        sopa = BeautifulSoup(html_crudo, "html.parser")
        for elemento in sopa(["script", "style", "noscript", "meta", "link", "header", "footer", "nav", "iframe"]):
            elemento.decompose()
        
        texto = sopa.get_text(separator=" ", strip=True)
        
        if not texto.strip():
            return f"La página {url} no contenía texto extraíble tras renderizar."
        
        return texto[:15000]
    
    except ImportError:
        return (
            "Error: Playwright no está instalado. "
            "Ejecuta: pip install playwright && playwright install chromium"
        )
    except Exception as e:
        return f"Error al scrapear {url} con Playwright: {e}"


@tool
def lector_pdf_web(url: str) -> str:
    """Descarga y extrae el texto de un PDF disponible en la web.
    
    Diseñado para documentos gubernamentales (SADER, INIFAP, CONABIO)
    y artículos científicos en formato PDF.
    
    Args:
        url: URL directa al archivo PDF.
        
    Returns:
        Texto extraído del PDF (máximo 20,000 caracteres).
    """
    if not url or not url.startswith(("http://", "https://")):
        return "Error: URL inválida. Debe comenzar con http:// o https://."
    
    try:
        # Descargar el PDF a un archivo temporal
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # Verificar que es un PDF
        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
            return f"Advertencia: El contenido de {url} no parece ser PDF (Content-Type: {content_type}). Intentando procesar de todos modos."
        
        # Guardar en archivo temporal y procesar
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            for chunk in response.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp_path = tmp.name
        
        try:
            from pypdf import PdfReader
            
            reader = PdfReader(tmp_path)
            texto_completo = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    texto_completo += page_text + "\n\n"
            
            if not texto_completo.strip():
                return f"El PDF de {url} no contenía texto extraíble (puede ser un PDF escaneado)."
            
            return texto_completo[:20000]
        
        finally:
            # Limpiar archivo temporal
            Path(tmp_path).unlink(missing_ok=True)
    
    except requests.RequestException as e:
        return f"Error al descargar PDF de {url}: {e}"
    except Exception as e:
        return f"Error al procesar PDF de {url}: {e}"


@tool
def lector_json_api(url: str) -> str:
    """Extrae datos de un endpoint JSON (ej. API de EncicloVida o iNaturalist).
    
    A diferencia de Playwright, esta herramienta hace una petición rápida
    y formatea el JSON resultante en texto plano legible para el LLM.
    Si el JSON es muy grande (ej. miles de observaciones), extrae un resumen.
    
    Args:
        url: URL del endpoint JSON.
        
    Returns:
        Resumen en texto plano de los datos JSON (máximo 15,000 caracteres).
    """
    if not url or not url.startswith(("http://", "https://")):
        return "Error: URL inválida."
        
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        datos = response.json()
        
        # Formatear el JSON a un string legible
        json_str = json.dumps(datos, indent=2, ensure_ascii=False)
        
        # Limitar para no saturar el contexto
        if len(json_str) > 15000:
            return f"Extracto del JSON ({len(json_str)} bytes total):\n{json_str[:15000]}...\n[JSON TRUNCADO]"
            
        return f"Datos JSON:\n{json_str}"
        
    except json.JSONDecodeError:
        return f"Error: La respuesta de {url} no es un JSON válido."
    except Exception as e:
        return f"Error al extraer JSON de {url}: {e}"


def detectar_tipo_contenido(url: str) -> str:
    """Detecta si una URL apunta a un PDF, JSON o HTML mediante HEAD request.
    
    Args:
        url: URL a inspeccionar.
        
    Returns:
        'pdf', 'json' o 'html'.
    """
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            )
        }
        resp = requests.head(url, headers=headers, timeout=10, allow_redirects=True)
        content_type = resp.headers.get("Content-Type", "").lower()
        
        if "pdf" in content_type or url.lower().split("?")[0].endswith(".pdf"):
            return "pdf"
        elif "json" in content_type or url.lower().split("?")[0].endswith(".json"):
            return "json"
        return "html"
    except Exception:
        # Si falla el HEAD, inferimos por extensión ignorando query params
        url_base = url.lower().split("?")[0]
        if url_base.endswith(".pdf"):
            return "pdf"
        elif url_base.endswith(".json"):
            return "json"
        return "html"
