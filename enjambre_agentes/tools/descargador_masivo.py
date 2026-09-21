"""
Motor asincrono de descarga y clasificacion masiva de fuentes para AgriPoli V3.

Clasifica y organiza automaticamente archivos descargados:
  - PDFs oficiales -> fuentes/pdf/
  - Tablas y datos CSV/JSON -> fuentes/csv/
  - Paginas web HTML y version Markdown limpia -> fuentes/html/
"""
from __future__ import annotations

import os
import re
import aiohttp
import aiofiles
import asyncio
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from tools.gestor_regiones import deducir_institucion_url


class SimpleHTMLToMarkdown(HTMLParser):
    """Extractor ligero sin dependencias externas para convertir HTML a Markdown limpio."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_ignored = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "header", "footer", "noscript", "svg"):
            self.in_ignored = True
        elif tag in ("h1", "h2"):
            self.text_parts.append("\n\n## ")
        elif tag in ("h3", "h4"):
            self.text_parts.append("\n\n### ")
        elif tag in ("p", "div", "section", "article"):
            self.text_parts.append("\n\n")
        elif tag in ("br", "li"):
            self.text_parts.append("\n* ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "header", "footer", "noscript", "svg"):
            self.in_ignored = False
        elif tag in ("p", "div", "h1", "h2", "h3", "h4"):
            self.text_parts.append("\n")

    def handle_data(self, data):
        if not self.in_ignored:
            self.text_parts.append(data)

    def get_markdown(self) -> str:
        raw = "".join(self.text_parts)
        # Limpiar saltos de linea excesivos
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


class DescargadorMasivoAsync:
    """
    Motor generico para descargas masivas asincronas con semaforo de concurrencia,
    clasificacion regional automatica por extension y extraccion de texto.
    """
    def __init__(self, max_concurrencia: int = 4, delay_segundos: float = 0.3):
        self.semaphore = asyncio.Semaphore(max_concurrencia)
        self.delay = delay_segundos

    async def fetch_html(self, session: aiohttp.ClientSession, url: str) -> str:
        """Obtiene el texto HTML de una URL."""
        async with self.semaphore:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                response.raise_for_status()
                html = await response.text()
            await asyncio.sleep(self.delay)
            return html

    async def fetch_json(self, session: aiohttp.ClientSession, url: str) -> dict:
        """Obtiene el JSON de una URL."""
        async with self.semaphore:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as response:
                response.raise_for_status()
                data = await response.json()
            await asyncio.sleep(self.delay)
            return data

    def _obtener_nombre_archivo(self, url: str, content_type: str, indice: int) -> tuple[str, str]:
        """Deduce un nombre de archivo descriptivo y el tipo (pdf, csv, html, json)."""
        from tools.gestor_regiones import slugify
        parsed = urlparse(url)
        path = parsed.path.rstrip("/")
        nombre_crudo = os.path.basename(path) if path else ""

        inst_slug = slugify(deducir_institucion_url(url))
        nombre_limpio = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", nombre_crudo).strip("_")

        if ".pdf" in url.lower() or "application/pdf" in content_type:
            tipo = "pdf"
            base = nombre_limpio if nombre_limpio and nombre_limpio.lower() not in ("content", "pdf", "descarga") else f"documento_tecnico_{indice}"
            if not base.lower().endswith(".pdf"):
                base = f"{base}.pdf"
            if inst_slug and not base.lower().startswith(inst_slug):
                base = f"{inst_slug}_{base}"
            nombre_final = base

        elif ".csv" in url.lower() or "text/csv" in content_type:
            tipo = "csv"
            base = nombre_limpio if nombre_limpio else f"datos_{indice}"
            if not base.lower().endswith(".csv"):
                base = f"{base}.csv"
            if inst_slug and not base.lower().startswith(inst_slug):
                base = f"{inst_slug}_{base}"
            nombre_final = base

        elif ".json" in url.lower() or "application/json" in content_type:
            tipo = "json"
            base = nombre_limpio if nombre_limpio else f"datos_{indice}"
            if not base.lower().endswith(".json"):
                base = f"{base}.json"
            if inst_slug and not base.lower().startswith(inst_slug):
                base = f"{inst_slug}_{base}"
            nombre_final = base

        else:
            tipo = "html"
            domain = parsed.netloc.replace("www.", "").split(".")[0]
            prefix = inst_slug or domain
            if not nombre_limpio or nombre_limpio.endswith((".html", ".htm", ".php")):
                base = f"{prefix}_fuente_{indice}"
            else:
                base = nombre_limpio
                if prefix and not base.lower().startswith(prefix):
                    base = f"{prefix}_{base}"
            if not base.lower().endswith(".html"):
                base = f"{base}.html"
            nombre_final = base

        return nombre_final, tipo

    async def descargar_fuente_regional(
        self,
        session: aiohttp.ClientSession,
        url: str,
        rutas_carpetas: dict[str, Path],
        indice: int = 1,
    ) -> dict:
        """
        Descarga y clasifica una fuente de internet hacia la estructura regional:
          - pdf -> fuentes/pdf/
          - csv/json -> fuentes/csv/
          - html -> fuentes/html/ (+ archivo .md limpio)
        """
        project_root = rutas_carpetas.get("project_root", Path.cwd())
        institucion = deducir_institucion_url(url)
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgriPoli/3.0"}

        meta = {
            "id": f"fuente_{indice}",
            "url": url,
            "institucion": institucion,
            "tipo": "desconocido",
            "archivo_local": None,
            "archivo_markdown": None,
            "tamano_bytes": 0,
            "estado_descarga": "pendiente",
        }

        async with self.semaphore:
            try:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20), ssl=False) as response:
                    if response.status != 200:
                        meta["estado_descarga"] = f"error_http_{response.status}"
                        return meta

                    content_type = response.headers.get("Content-Type", "").lower()
                    nombre_archivo, tipo = self._obtener_nombre_archivo(url, content_type, indice)
                    meta["tipo"] = tipo

                    if tipo == "pdf":
                        dest_path = rutas_carpetas["pdf_dir"] / nombre_archivo
                    elif tipo in ("csv", "json"):
                        dest_path = rutas_carpetas["csv_dir"] / nombre_archivo
                    else:
                        dest_path = rutas_carpetas["html_dir"] / nombre_archivo

                    content_bytes = await response.read()
                    async with aiofiles.open(dest_path, "wb") as f:
                        await f.write(content_bytes)

                    tamano = len(content_bytes)
                    meta["tamano_bytes"] = tamano
                    meta["archivo_local"] = str(dest_path.relative_to(project_root))
                    meta["estado_descarga"] = "completado"

                    # Si es HTML, generar version limpia en Markdown para alimentar el RAG
                    if tipo == "html":
                        try:
                            html_text = content_bytes.decode("utf-8", errors="ignore")
                            parser = SimpleHTMLToMarkdown()
                            parser.feed(html_text)
                            md_content = parser.get_markdown()
                            if md_content:
                                md_name = dest_path.stem + ".md"
                                md_path = rutas_carpetas["html_dir"] / md_name
                                encendido_md = (
                                    f"---\n"
                                    f"fuente_url: \"{url}\"\n"
                                    f"institucion: \"{institucion}\"\n"
                                    f"archivo_original: \"{dest_path.name}\"\n"
                                    f"---\n\n"
                                    f"{md_content}\n"
                                )
                                async with aiofiles.open(md_path, "w", encoding="utf-8") as f_md:
                                    await f_md.write(encendido_md)
                                meta["archivo_markdown"] = str(md_path.relative_to(project_root))
                        except Exception:
                            pass

                    print(f"  [OK] Fuente [{indice}] ({tipo.upper()}) -> {dest_path.name}")
                    return meta

            except Exception as e:
                meta["estado_descarga"] = f"error_{type(e).__name__}"
                return meta
            finally:
                await asyncio.sleep(self.delay)

    async def download_file(self, session: aiohttp.ClientSession, url: str, dest_path: str, desc: str = "Archivo") -> bool:
        """Compatibilidad con descargas directas a rutas arbitrarias."""
        if os.path.exists(dest_path):
            return True
        async with self.semaphore:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgriPoli/3.0"}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20), ssl=False) as response:
                    if response.status == 200:
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        async with aiofiles.open(dest_path, "wb") as f:
                            while True:
                                chunk = await response.content.read(8192)
                                if not chunk:
                                    break
                                await f.write(chunk)
                        return True
                    return False
            except Exception:
                return False
            finally:
                await asyncio.sleep(self.delay)
