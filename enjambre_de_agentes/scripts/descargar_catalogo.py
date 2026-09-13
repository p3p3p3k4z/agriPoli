import asyncio
import aiohttp
import aiofiles
import json
import os
import re
from bs4 import BeautifulSoup
import sys

# Agregar la ruta base para poder importar gbif_client desde tools
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.gbif_client import enrich_with_gbif


# Configuracion
BASE_URL = "https://enciclovida.mx"
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'descargas_masivas'))
MAX_CONCURRENCY = 5
DELAY = 1.0 # Respeto a los servidores de CONABIO

async def fetch_html(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()

async def download_file(session, url, dest_path, desc="Archivo"):
    if os.path.exists(dest_path):
        print(f"  [Skip] {desc} ya existe en {os.path.basename(dest_path)}")
        return True
        
    try:
        async with session.get(url) as response:
            if response.status == 200:
                print(f"  [Descargando] {desc} -> {os.path.basename(dest_path)}")
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                async with aiofiles.open(dest_path, 'wb') as f:
                    while True:
                        chunk = await response.content.read(4096)
                        if not chunk:
                            break
                        await f.write(chunk)
                return True
            else:
                print(f"  [No Encontrado] {desc} (HTTP {response.status}) en {url}")
                return False
    except Exception as e:
        print(f"  [Error] Fallo al descargar {desc} de {url}: {e}")
        return False

async def obtener_catalogo(session, tipo_polinizador="plantas_meliferas"):
    url = f"{BASE_URL}/polinizadores?tipo_polinizador={tipo_polinizador}&por_pagina=5000&pagina=1"
    print(f"Obteniendo catálogo de {tipo_polinizador} desde {url}...")
    html = await fetch_html(session, url)
    soup = BeautifulSoup(html, 'html.parser')
    
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/especies/') and not '/descarga-mapa' in href:
            if href not in links:
                links.append(href)
                
    print(f"Encontradas {len(links)} especies únicas.")
    return links

async def procesar_especie(session, href, semaphore, tipo, use_gbif=False):
    match = re.search(r'/especies/(\d+)', href)
    if not match:
        return
    especie_id = match.group(1)
    
    # Clasificación inteligente por carpeta del catálogo
    especie_dir = os.path.join(DATA_DIR, tipo, especie_id)
    completado_path = os.path.join(especie_dir, 'completado.flag')
    gbif_path = os.path.join(especie_dir, 'gbif_data.json')
    
    # Si ya está completado y NO pidieron gbif, o si pidieron gbif y ya existe gbif_data, omitimos
    if os.path.exists(completado_path):
        if not use_gbif or (use_gbif and os.path.exists(gbif_path)):
            return
        # Si llega aquí, significa que ya existe completado.flag, pero falta gbif_data.json
        # Haremos una rama rápida solo para procesar GBIF y retornar temprano
        try:
            print(f"[{tipo.upper()}] Enriqueciendo ID {especie_id} con GBIF...")
            meta_path = os.path.join(especie_dir, 'metadata.json')
            scientific_name = None
            if os.path.exists(meta_path):
                async with aiofiles.open(meta_path, 'r') as f:
                    content = await f.read()
                    meta = json.loads(content)
                scientific_name = meta.get('scientific_name')
                
            if not scientific_name:
                obs_path = os.path.join(especie_dir, 'observaciones.json')
                if os.path.exists(obs_path):
                    try:
                        async with aiofiles.open(obs_path, 'r') as f:
                            obs_content = await f.read()
                            obs_data = json.loads(obs_content)
                            if obs_data and isinstance(obs_data, list) and len(obs_data) > 0:
                                scientific_name = obs_data[0].get('especievalidabusqueda')
                    except:
                        pass
                        
                if not scientific_name:
                    url_especie = f"{BASE_URL}{href}"
                    html = await fetch_html(session, url_especie)
                    soup = BeautifulSoup(html, 'html.parser')
                    # Intentar buscar el <i> principal dentro del header h1
                    h1 = soup.find('h1')
                    if h1 and h1.find('i'):
                        scientific_name = h1.find('i').text.strip()
                    else:
                        title = soup.title.string if soup.title else ""
                        match_parens = re.search(r'\((.*?)\)', title)
                        if match_parens:
                            scientific_name = match_parens.group(1)
                        else:
                            scientific_name = title.split(' - ')[0].strip()
                
                # Actualizamos metadata
                if os.path.exists(meta_path):
                    meta['scientific_name'] = scientific_name
                    async with aiofiles.open(meta_path, 'w') as f:
                        await f.write(json.dumps(meta, indent=2))
                        
            if scientific_name:
                    gbif_data = await enrich_with_gbif(session, scientific_name)
                    if gbif_data:
                        async with aiofiles.open(gbif_path, 'w') as f:
                            await f.write(json.dumps(gbif_data, indent=2))
                        print(f"  [GBIF] Enriquecimiento exitoso para {scientific_name}")
            return
        except Exception as e:
            print(f"  [GBIF Error] Fallo al enriquecer {especie_id}: {e}")
            return

        
    async with semaphore:
        url_especie = f"{BASE_URL}{href}"
        try:
            print(f"[{tipo.upper()}] Procesando ID {especie_id}...")
            html = await fetch_html(session, url_especie)
            soup = BeautifulSoup(html, 'html.parser')
            
            # JSON observaciones
            url_json = f"{BASE_URL}/especies/{especie_id}/consulta-registros.json?coleccion=naturalista&formato=json"
            await download_file(session, url_json, os.path.join(especie_dir, 'observaciones.json'), desc="JSON Observaciones")
            
            # Archivos de mapa y metadata
            snib_url = None
            for a in soup.find_all('a', href=True):
                if '/descarga-mapa/' in a['href']:
                    map_url = f"{BASE_URL}{a['href']}"
                    map_filename = a['href'].split('/')[-1] + '.zip'
                    await download_file(session, map_url, os.path.join(especie_dir, 'mapas', map_filename), desc="Mapa ZIP")
                    
                if 'snibgeoportal' in a['href']:
                    snib_url = a['href']
            
            # Guardamos la metadata (nombre, links)
            meta_path = os.path.join(especie_dir, 'metadata.json')
            os.makedirs(especie_dir, exist_ok=True)
            
            # Obtener el nombre científico probable (generalmente antes del guión en el título)
            title = soup.title.string if soup.title else ""
            scientific_name = title.split('-')[0].strip()
            
            async with aiofiles.open(meta_path, 'w') as f:
                await f.write(json.dumps({
                    'id': especie_id,
                    'scientific_name': scientific_name,
                    'url': url_especie,
                    'snib_url': snib_url
                }, indent=2))
                
            # Integración Opcional de GBIF
            if use_gbif and scientific_name:
                gbif_data = await enrich_with_gbif(session, scientific_name)
                if gbif_data:
                    gbif_path = os.path.join(especie_dir, 'gbif_data.json')
                    async with aiofiles.open(gbif_path, 'w') as f:
                        await f.write(json.dumps(gbif_data, indent=2))
                        print(f"  [GBIF] Enriquecimiento exitoso para {scientific_name}")
            
            # Marcar completado
            async with aiofiles.open(os.path.join(especie_dir, 'completado.flag'), 'w') as f:
                await f.write('ok')
                
            await asyncio.sleep(DELAY)
            
        except Exception as e:
            print(f"Fallo en {especie_id}: {e}")

async def main(tipo="plantas_meliferas", limit=None, use_gbif=False):
    os.makedirs(DATA_DIR, exist_ok=True)
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    
    async with aiohttp.ClientSession() as session:
        especies = await obtener_catalogo(session, tipo)
        
        cat_path = os.path.join(DATA_DIR, f'catalogo_{tipo}.json')
        async with aiofiles.open(cat_path, 'w') as f:
            await f.write(json.dumps(especies, indent=2))
            
        if limit:
            especies = especies[:limit]
            
        tasks = [procesar_especie(session, e, semaphore, tipo, use_gbif) for e in especies]
        await asyncio.gather(*tasks)
        
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Descarga masiva de EncicloVida')
    parser.add_argument('--tipo', default='ambos', help='Tipo de catálogo: plantas_meliferas, visitantes_polinizadores, o ambos')
    parser.add_argument('--limit', type=int, default=None, help='Limitar a N especies para pruebas')
    parser.add_argument('--use-gbif', action='store_true', help='Habilitar enriquecimiento de datos consultando la API de GBIF')
    args = parser.parse_args()
    
    tipos = ['plantas_meliferas', 'visitantes_polinizadores'] if args.tipo == 'ambos' else [args.tipo]
    
    for t in tipos:
        print(f"--- Iniciando descarga masiva de {t} ---")
        asyncio.run(main(t, args.limit, args.use_gbif))
        
    print("Descarga masiva finalizada exitosamente.")
