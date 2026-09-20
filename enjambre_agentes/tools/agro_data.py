import os
import csv
import aiohttp
import asyncio
from typing import List, Dict, Any
from pathlib import Path

# Utilizamos el scraping ya existente de playwright
from tools.scraper import lector_web_playwright

class AgroDataManager:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    async def descargar_siap_csv(self, anio: int) -> str:
        """
        Descarga el Cierre Agrícola Municipal (SIAP) de un año específico desde Datos Abiertos.
        Retorna la ruta del archivo CSV descargado.
        """
        file_path = os.path.join(self.data_dir, f"cierre_agricola_{anio}.csv")
        
        # Si ya existe el archivo, no descargarlo de nuevo
        if os.path.exists(file_path):
            return file_path

        # Nota: La URL oficial de SIAP cambia frecuentemente por año en su formato. 
        # Este es el patrón general de datos abiertos para la Secretaría de Agricultura:
        url = f"http://infosiap.siap.gob.mx/gobmx/datosAbiertos/ProduccionAgricola/Cierre_agricola_mun_{anio}.csv"
        
        print(f"Descargando datos SIAP del año {anio}...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(file_path, "wb") as f:
                            f.write(content)
                        print(f"Descarga completada: {file_path}")
                        return file_path
                    else:
                        print(f"Error HTTP {response.status} al descargar {url}. El dataset podría no estar disponible.")
                        return ""
        except Exception as e:
            print(f"Error crítico conectando a SIAP: {e}")
            return ""

    def procesar_siap_csv(self, file_path: str, estado_filtro: str = None) -> List[Dict[str, Any]]:
        """
        Procesa el CSV de SIAP y lo convierte en una estructura de diccionario filtrable.
        """
        resultados = []
        if not os.path.exists(file_path):
            return resultados

        with open(file_path, "r", encoding="latin-1") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Filtrar si se solicita un estado en particular
                if estado_filtro and row.get('Nomestado', '').lower() != estado_filtro.lower():
                    continue
                    
                resultados.append({
                    "estado": row.get("Nomestado", ""),
                    "municipio": row.get("Nommunicipio", ""),
                    "cultivo": row.get("Nomcultivo", ""),
                    "ciclo": row.get("Nomciclo", ""),
                    "modalidad": row.get("Nommodalidad", ""),
                    "superficie_sembrada_ha": float(row.get("Sembrada", 0) or 0),
                    "produccion_ton": float(row.get("Volumen", 0) or 0)
                })
        return resultados

    def scraping_dinamico_sader(self, region_o_cultivo: str) -> str:
        """
        Alternativa: Usa Playwright para scrapear información agrícola de fuentes que
        no exponen un CSV (como tableros interactivos del SIACON o reportes de INEGI).
        """
        # Formato de búsqueda de un reporte agroalimentario hipotético o público
        url_reporte = f"https://www.gob.mx/busqueda?keys={region_o_cultivo.replace(' ', '+')}+agricultura+siembra"
        return lector_web_playwright.invoke(url_reporte)
