import os
import aiohttp
import aiofiles
import asyncio
from typing import Optional

class DescargadorMasivoAsync:
    """
    Motor genérico para descargas masivas asíncronas.
    Soporta concurrencia limitada por semáforo y omisión de archivos existentes.
    """
    def __init__(self, max_concurrencia: int = 5, delay_segundos: float = 0.5):
        self.semaphore = asyncio.Semaphore(max_concurrencia)
        self.delay = delay_segundos

    async def fetch_html(self, session: aiohttp.ClientSession, url: str) -> str:
        """Obtiene el texto HTML de una URL."""
        async with self.semaphore:
            async with session.get(url) as response:
                response.raise_for_status()
                html = await response.text()
            await asyncio.sleep(self.delay)
            return html

    async def fetch_json(self, session: aiohttp.ClientSession, url: str) -> dict:
        """Obtiene el JSON de una URL."""
        async with self.semaphore:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
            await asyncio.sleep(self.delay)
            return data

    async def download_file(self, session: aiohttp.ClientSession, url: str, dest_path: str, desc: str = "Archivo") -> bool:
        """
        Descarga un archivo si no existe localmente.
        """
        if os.path.exists(dest_path):
            print(f"  [Skip] {desc} ya existe en {os.path.basename(dest_path)}")
            return True
            
        async with self.semaphore:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        print(f"  [Descargando] {desc} -> {os.path.basename(dest_path)}")
                        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                        async with aiofiles.open(dest_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(8192)
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
            finally:
                await asyncio.sleep(self.delay)
