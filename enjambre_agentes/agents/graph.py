"""
Ensamblaje del Grafo LangGraph — Orquestación del Sistema Multiagente AgriPoli.

Conecta los 3 nodos (Investigador → Scraper → Sintetizador) en un flujo
lineal usando StateGraph de LangGraph con checkpointing de memoria.

Inspirado en el ensamblaje de OptiAgent/agentes.py (L342-L406),
simplificado a un pipeline lineal en lugar del fan-out paralelo.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.state import ScrapingState
from agents.investigador import investigador_node
from agents.scraper import scraper_node
from agents.sintetizador import sintetizador_node


def build_graph() -> StateGraph:
    """Construye y compila el grafo del sistema multiagente AgriPoli.
    
    Flujo:
        START → investigador → scraper → sintetizador → END
        
    Returns:
        Grafo compilado listo para invocar con .invoke() o .stream().
    """
    builder = StateGraph(ScrapingState)
    
    # --- Registrar nodos ---
    builder.add_node("investigador", investigador_node)
    builder.add_node("scraper", scraper_node)
    builder.add_node("sintetizador", sintetizador_node)
    
    # --- Definir flujo ---
    # Flujo lineal: Investigar URLs → Scrapear contenido → Sintetizar JSON
    builder.add_edge(START, "investigador")
    builder.add_edge("investigador", "scraper")
    builder.add_edge("scraper", "sintetizador")
    builder.add_edge("sintetizador", END)
    
    # Checkpointer para memoria de sesión
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)
    
    return graph


# --- Instancia global del grafo (singleton) ---
agripoli_graph = build_graph()
anita_graph = agripoli_graph  # Retrocompatibilidad


def run_agripoli_stream(
    region: str,
    thread_id: str,
    provider: str = "Gemini",
    llm_model_name: str | None = None,
) -> Any:
    """Ejecuta el sistema multiagente con streaming para monitoreo en tiempo real.
    
    Args:
        region: Región de México a investigar (ej. "La Mixteca, Oaxaca").
        thread_id: ID de hilo único para la memoria del grafo.
        provider: Proveedor LLM ("Gemini", "Groq", "Cohere").
        llm_model_name: Modelo específico (None = default del proveedor).
        
    Yields:
        Eventos del grafo con el estado actualizado de cada nodo.
    """
    initial_state: ScrapingState = {
        "messages": [],
        "region": region,
        "provider": provider,
        "llm_model_name": llm_model_name or "",
        "urls_polinizadores": [],
        "urls_agricultura": [],
        "urls_clima": [],
        "urls_flora": [],
        "urls_suelo": [],
        "contenido_polinizadores": "",
        "contenido_agricultura": "",
        "contenido_clima": "",
        "contenido_flora": "",
        "contenido_suelo": "",
        "contenido_rag": "",
        "datos_estructurados": "",
        "errores": [],
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    
    for event in agripoli_graph.stream(initial_state, config=config):
        yield event


run_anita_stream = run_agripoli_stream  # Retrocompatibilidad


def run_agripoli(
    region: str,
    thread_id: str,
    provider: str = "Gemini",
    llm_model_name: str | None = None,
) -> dict:
    """Ejecuta el enjambre de agentes de forma síncrona.
    
    Args:
        region: Región de México a investigar (ej. "La Mixteca, Oaxaca").
        thread_id: ID de hilo único para la memoria del grafo.
        provider: Proveedor LLM ("Gemini", "Groq", "Cohere").
        llm_model_name: Modelo específico (None = default del proveedor).
        
    Returns:
        Estado final del grafo con datos_estructurados (JSON).
    """
    initial_state: ScrapingState = {
        "messages": [],
        "region": region,
        "provider": provider,
        "llm_model_name": llm_model_name or "",
        "urls_polinizadores": [],
        "urls_agricultura": [],
        "urls_clima": [],
        "urls_flora": [],
        "urls_suelo": [],
        "contenido_polinizadores": "",
        "contenido_agricultura": "",
        "contenido_clima": "",
        "contenido_flora": "",
        "contenido_suelo": "",
        "contenido_rag": "",
        "datos_estructurados": "",
        "errores": [],
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    
    result = agripoli_graph.invoke(initial_state, config=config)
    return result


run_anita = run_agripoli  # Retrocompatibilidad
