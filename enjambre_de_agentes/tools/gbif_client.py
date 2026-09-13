import aiohttp
import json

GBIF_BASE_URL = "https://api.gbif.org/v1"

async def fetch_gbif_species(session, scientific_name):
    """
    Realiza un 'match' en la API de GBIF para obtener el usageKey 
    y la jerarquía taxonómica de una especie.
    """
    url = f"{GBIF_BASE_URL}/species/match?name={scientific_name}"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                # Verificar si encontró un match exacto o al menos confianza alta
                if data.get('matchType') in ('EXACT', 'FUZZY', 'HIGHERRANK'):
                    return data
            return None
    except Exception as e:
        print(f"Error consultando GBIF para {scientific_name}: {e}")
        return None

async def fetch_gbif_vernacular(session, usage_key):
    """
    Obtiene nombres comunes/vernáculos adicionales usando el usageKey de GBIF.
    """
    url = f"{GBIF_BASE_URL}/species/{usage_key}/vernacularNames"
    try:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('results', [])
            return []
    except Exception as e:
        print(f"Error obteniendo nombres vernáculos de GBIF para {usage_key}: {e}")
        return []

async def enrich_with_gbif(session, scientific_name):
    """
    Función combinada que consulta GBIF por especie y por nombres comunes.
    Retorna un diccionario estructurado listo para ser guardado.
    """
    species_data = await fetch_gbif_species(session, scientific_name)
    
    if not species_data or 'usageKey' not in species_data:
        return None
        
    usage_key = species_data['usageKey']
    vernacular_names = await fetch_gbif_vernacular(session, usage_key)
    
    # Ensamblar resultados combinados
    return {
        "gbif_match": species_data,
        "gbif_vernacular": vernacular_names,
        "maps_api_example": f"https://api.gbif.org/v2/map/occurrence/density/{{z}}/{{x}}/{{y}}@1x.png?taxonKey={usage_key}&style=classic.poly"
    }
