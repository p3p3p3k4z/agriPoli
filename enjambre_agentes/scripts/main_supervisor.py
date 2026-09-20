#!/usr/bin/env uv run python
import asyncio
import sys
import os

# Agregar la ruta base
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config.keys import validate_keys
from agents.supervisor import crear_supervisor
from langchain_core.messages import HumanMessage, AIMessage

async def main():
    try:
        validate_keys("TAVILY_API_KEY", "GEMINI_API_KEY")
    except ValueError as e:
        print(f"Error de configuración: {e}")
        return

    print("=" * 70)
    print(" [x_x] Supervisor Multiagente AgriPoli (Human-in-the-Loop) ")
    print("=" * 70)
    print("Hola, soy tu Supervisor de Orquesta. Tengo bajo mi mando a:")
    print(" - (O_O) El Enjambre WebScraper (Investigador)")
    print(" - (^_^) El Agro Experto (Consultas e INEGIpy)")
    print(" - [>_<] El Módulo de Extracción Masiva (SIAP y UNAM)\n")
    print("Dime, ¿qué región deseas investigar o de qué cultivo/polinizador")
    print("te gustaría obtener resúmenes antes de decidir si lo descargamos?\n")
    
    supervisor = crear_supervisor(provider="Gemini")
    chat_history = []
    
    while True:
        try:
            consulta = input("(T_T) Tú: ")
        except (KeyboardInterrupt, EOFError):
            print("\nCerrando Supervisor...")
            break
            
        if consulta.lower() in ['salir', 'exit', 'quit']:
            print("Cerrando Supervisor. ¡Hasta pronto!")
            break
            
        if not consulta.strip():
            continue
            
        print("\n[>_<] Supervisor orquestando (por favor espera)...\n")
        
        try:
            # En LangGraph, el estado es una lista de mensajes
            chat_history.append(HumanMessage(content=consulta))
            
            # Invocamos al supervisor
            respuesta = await supervisor.ainvoke({
                "messages": chat_history
            })
            
            # La respuesta contiene la nueva lista de mensajes, tomamos el último
            mensajes_retornados = respuesta.get("messages", [])
            output_text = "No pude procesar la respuesta."
            if mensajes_retornados:
                ultimo_msg = mensajes_retornados[-1].content
                if isinstance(ultimo_msg, list):
                    # Gemini a veces retorna [{'type': 'text', 'text': 'Hola'}]
                    textos = [item.get("text", "") for item in ultimo_msg if isinstance(item, dict) and item.get("type") == "text"]
                    output_text = "".join(textos) if textos else str(ultimo_msg)
                else:
                    output_text = str(ultimo_msg)
            
            print("=" * 70)
            print(f"(^o^) Supervisor: {output_text}")
            print("=" * 70 + "\n")
            
            # Guardamos la respuesta del agente para mantener el contexto
            chat_history.append(AIMessage(content=output_text))
            
            # Limitar historial para no exceder tokens (ej. últimos 10 turnos = 20 mensajes)
            if len(chat_history) > 20:
                chat_history = chat_history[-20:]
                
        except Exception as e:
            print(f"[X_X] Error interno del Supervisor: {e}")

if __name__ == "__main__":
    asyncio.run(main())
