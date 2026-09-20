import os
import json
import asyncio
import aiohttp
from datetime import datetime

class UNAMDataManager:
    def __init__(self, data_dir: str, ref_file: str):
        self.data_dir = data_dir
        self.ref_file = ref_file
        os.makedirs(self.data_dir, exist_ok=True)
        self._inicializar_referencias()

    def _inicializar_referencias(self):
        if not os.path.exists(self.ref_file):
            with open(self.ref_file, "w", encoding="utf-8") as f:
                json.dump({"fuentes": []}, f, indent=2, ensure_ascii=False)

    def registrar_referencia(self, titulo: str, url: str, descripcion: str, tipo_dato: str):
        """Registra la procedencia de los datos masivos."""
        with open(self.ref_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Evitar duplicados
        if not any(f["url"] == url for f in data["fuentes"]):
            data["fuentes"].append({
                "titulo": titulo,
                "url": url,
                "descripcion": descripcion,
                "tipo_dato": tipo_dato,
                "fecha_descarga": datetime.now().isoformat()
            })
            
            with open(self.ref_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    async def descargar_dataset_csv(self, url: str, filename: str, titulo_ref: str, desc_ref: str) -> str:
        """
        Descarga un archivo masivo CSV simulando el acceso al portal de Datos Abiertos UNAM
        y registra automáticamente la referencia bibliográfica.
        """
        file_path = os.path.join(self.data_dir, filename)
        
        # Registrar de dónde viene la información
        self.registrar_referencia(
            titulo=titulo_ref,
            url=url,
            descripcion=desc_ref,
            tipo_dato="CSV Masivo (Biodiversidad)"
        )
        
        if os.path.exists(file_path):
            print(f"El archivo {filename} ya existe localmente.")
            return file_path
            
        print(f"Descargando dataset masivo de UNAM: {url}...")
        try:
            async with aiohttp.ClientSession() as session:
                # Simulamos la descarga. En un entorno real apuntaríamos al endpoint oficial de datosabiertos.unam.mx
                async with session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(file_path, "wb") as f:
                            f.write(content)
                        return file_path
                    else:
                        print(f"Error HTTP {response.status} al descargar. Archivo no disponible.")
                        return ""
        except Exception as e:
            print(f"Error en descarga de UNAM: {e}")
            return ""
