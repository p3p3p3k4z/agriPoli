"""
Estado compartido del Enjambre de Agentes (ScrapingState).

Define el TypedDict que sirve como memoria compartida entre todos los nodos
del grafo LangGraph. Cada nodo lee y escribe en este estado.

Inspirado en OptiAgentState de OptiAgent/agentes.py, adaptado al dominio
ecológico/agrícola de México.
"""
from __future__ import annotations

from typing import Annotated, TypedDict
from operator import add


class ScrapingState(TypedDict):
    """Estado compartido del sistema multiagente AgriPoli.
    
    Flujo de datos:
        1. Investigador escribe: urls_descubiertas
        2. Scraper lee urls_descubiertas, escribe: contenido_*
        3. Sintetizador lee contenido_*, escribe: datos_estructurados
    """
    
    # --- Historial y configuración ---
    messages: Annotated[list, add]  # Historial de mensajes (acumulativo via LangGraph)
    region: str                     # Región de búsqueda (ej. "La Mixteca, Oaxaca")
    provider: str                   # Proveedor LLM: "Gemini" | "Groq" | "Cohere"
    llm_model_name: str             # Modelo específico del proveedor
    
    # --- Nodo Investigador → URLs descubiertas ---
    # Cada campo almacena las URLs encontradas por categoría temática
    urls_polinizadores: list[str]
    urls_agricultura: list[str]
    urls_clima: list[str]
    urls_flora: list[str]
    urls_suelo: list[str]
    
    # --- Nodo Scraper → Contenido crudo extraído ---
    # Texto limpio extraído de las URLs (HTML/PDF procesado)
    contenido_polinizadores: str
    contenido_agricultura: str
    contenido_clima: str
    contenido_flora: str
    contenido_suelo: str
    contenido_rag: str  # Resultado de RAG sobre textos que excedieron el umbral
    
    # --- Nodo Sintetizador → Salida final ---
    datos_estructurados: str    # JSON string del schema DatosRegion
    errores: list[str]          # Errores no fatales durante el pipeline
