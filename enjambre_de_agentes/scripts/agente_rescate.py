import os
import json
import asyncio
import sys
from pathlib import Path

# Configurar path para importar desde el proyecto principal
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.agents import AgentExecutor, create_tool_calling_agent

# Importar configuraciones locales
from config.models import get_llm
from tools.gbif_client import enrich_with_gbif
from config.keys import TAVILY_API_KEY

import aiohttp
import aiofiles

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'descargas_masivas'))

def setup_agent(provider="Gemini"):
    """
    Configura y devuelve un AgentExecutor capaz de buscar en la web.
    """
    llm = get_llm(provider=provider, temperature=0.1)
    
    # Herramienta de búsqueda global Tavily
    # Permite a la IA buscar el nombre científico real o información faltante
    tavily_tool = TavilySearchResults(max_results=3, tavily_api_key=TAVILY_API_KEY)
    tools = [tavily_tool]
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Eres un taxónomo experto y biólogo. Tu tarea es ayudar a limpiar y encontrar nombres científicos válidos "
                   "a partir de cadenas de texto corruptas o nombres comunes mexicanos. "
                   "Debes buscar en la web (usando Tavily) para encontrar el nombre científico (género y especie) aceptado mundialmente. "
                   "Si encuentras información biológica (ej. familia, orden), tenla en cuenta. "
                   "TU ÚNICA SALIDA DEBE SER EL NOMBRE CIENTÍFICO FINAL, sin comillas ni texto adicional. "
                   "Si es absolutamente imposible encontrarlo, responde 'DESCONOCIDO'."),
        ("human", "Encuentra el nombre científico válido para: {input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    return agent_executor

async def process_missing_species(session, agent_executor):
    """
    Escanea las descargas masivas, encuentra especies sin GBIF, usa la IA para
    limpiar el nombre, y vuelve a intentar con GBIF.
    """
    print("--- Iniciando Agente de Rescate ---")
    missing_folders = []
    
    # 1. Identificar carpetas faltantes
    for root, dirs, files in os.walk(DATA_DIR):
        if 'metadata.json' in files and 'gbif_data.json' not in files:
            missing_folders.append(root)
            
    print(f"Se encontraron {len(missing_folders)} especies sin datos de GBIF.")
    
    if not missing_folders:
        print("¡Todo está completo! No hay rescates por hacer.")
        return

    # 2. Rescatar dinámicamente cada una
    for folder in missing_folders:
        meta_path = os.path.join(folder, 'metadata.json')
        with open(meta_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
            
        especie_id = meta.get('id', 'Desconocido')
        bad_name = meta.get('scientific_name', '')
        if not bad_name:
            continue
            
        print(f"\n[RESCATE] Analizando ID: {especie_id} | Nombre original: '{bad_name}'")
        
        # 3. Invocar a la IA para buscar en la web y resolver el nombre real
        try:
            print("  -> Ejecutando IA y Web Scraping semántico...")
            response = await agent_executor.ainvoke({"input": bad_name})
            clean_scientific_name = response.get('output', '').strip()
            print(f"  -> IA dedujo el nombre científico: {clean_scientific_name}")
            
            if clean_scientific_name and clean_scientific_name != "DESCONOCIDO":
                # 4. Reintentar GBIF con el nombre limpio
                gbif_data = await enrich_with_gbif(session, clean_scientific_name)
                
                if gbif_data:
                    gbif_path = os.path.join(folder, 'gbif_data.json')
                    async with aiofiles.open(gbif_path, 'w') as f:
                        await f.write(json.dumps(gbif_data, indent=2))
                    print(f"  [ÉXITO] GBIF recuperado y guardado para: {clean_scientific_name}")
                    
                    # Actualizar metadata con el nombre limpio para el futuro
                    meta['scientific_name'] = clean_scientific_name
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, indent=2)
                else:
                    print(f"  [FALLO] El nombre corregido '{clean_scientific_name}' tampoco arrojó resultados en GBIF.")
            else:
                print("  [FALLO] La IA no pudo determinar un nombre científico válido.")
                
        except Exception as e:
            print(f"  [ERROR] Falló la invocación del agente: {e}")

async def main():
    if not TAVILY_API_KEY:
        print("Error: Se requiere TAVILY_API_KEY en tu entorno (.env) para ejecutar el agente de rescate.")
        return
        
    # Puedes cambiar el provider a "Groq" o "Cohere" si lo prefieres
    agent = setup_agent(provider="Cohere")
    
    async with aiohttp.ClientSession() as session:
        await process_missing_species(session, agent)

if __name__ == "__main__":
    asyncio.run(main())
