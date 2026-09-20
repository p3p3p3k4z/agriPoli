#!/usr/bin/env uv run python
"""
Generador del Diagrama Estático de Arquitectura para el Sistema Multiagente AgriPoli.
Compila el StateGraph de LangGraph V2 y guarda la imagen estática en docs/arquitectura_agentes.png.
"""
import os
import sys

# Asegurar silenciamiento de warnings y paths limpios
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config.silenciador
from config.agri_logger import log_info, log_ok, log_error
from agents.graph_v2 import crear_grafo_v2

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS_DIR = os.path.join(BASE_DIR, "docs")
OUT_FILE = os.path.join(DOCS_DIR, "arquitectura_agentes.png")


def generar_diagrama_arquitectura(salida_png: str = OUT_FILE) -> str | None:
    """Genera y guarda el diagrama estático en imagen PNG de la arquitectura de agentes."""
    os.makedirs(os.path.dirname(salida_png), exist_ok=True)
    log_info(f"Compilando grafo de LangGraph para generar diagrama...", kaomoji="(o_o)")

    try:
        grafo = crear_grafo_v2(provider="Gemini")
        g = grafo.get_graph()

        if hasattr(g, "draw_mermaid_png"):
            png_bytes = g.draw_mermaid_png()
            with open(salida_png, "wb") as f:
                f.write(png_bytes)
            log_ok(f"Diagrama de arquitectura guardado estáticamente en: {salida_png} ({len(png_bytes):,} bytes)", kaomoji="(^_^)/")
            return salida_png
        else:
            log_error("El grafo de LangGraph no soporta draw_mermaid_png.", kaomoji="[X_X]")
            return None
    except Exception as e:
        log_error(f"Error generando imagen de arquitectura: {e}", kaomoji="[X_X]")
        return None


if __name__ == "__main__":
    generar_diagrama_arquitectura()
