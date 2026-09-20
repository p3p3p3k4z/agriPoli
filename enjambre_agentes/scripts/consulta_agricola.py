import asyncio
import sys
import os

# Agregar la ruta base
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agents.agro_experto import crear_agro_experto
from config.keys import validate_keys

async def main():
    try:
        validate_keys("TAVILY_API_KEY", "GEMINI_API_KEY")
    except ValueError as e:
        print(f"Error de configuración: {e}")
        return

    print("=== Consola de Consulta Agrícola (Enjambre AniIta) ===")
    print("Este agente consultará primero los JSON locales descargados de SADER/SIAP.")
    print("Si no encuentra la información, buscará dinámicamente en internet.\n")
    
    agente = crear_agro_experto(provider="Gemini")
    
    while True:
        consulta = input("\n🌱 ¿Qué deseas saber sobre la agricultura en México? (o 'salir'): ")
        if consulta.lower() in ['salir', 'exit', 'quit']:
            break
            
        print("\n🔍 Consultando al experto agrícola...\n")
        
        try:
            respuesta = await agente.ainvoke({"input": consulta})
            print("\n" + "="*50)
            print(respuesta.get('output', 'No pude procesar la respuesta.'))
            print("="*50)
        except Exception as e:
            print(f"Error al consultar al agente: {e}")

if __name__ == "__main__":
    asyncio.run(main())
