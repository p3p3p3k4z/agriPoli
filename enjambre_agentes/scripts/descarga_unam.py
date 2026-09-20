#!/usr/bin/env uv run python
import os
import sys
import asyncio

# Agregar la ruta base
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.unam_data import UNAMDataManager

async def main():
    print("=== Iniciando Extracción Masiva de Colecciones UNAM ===")
    
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'unam_ibunam'))
    ref_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'referencias.json'))
    
    manager = UNAMDataManager(data_dir=data_dir, ref_file=ref_file)
    
    # 1. Dataset Simulado/Real de Insectos Polinizadores
    # En producción apuntaríamos al zip/csv del portal SNIB o IBUNAM.
    url_coleccion_insectos = "https://datosabiertos.unam.mx/IBUNAM:CNIN:Polinizadores.csv"
    print("\nDescargando Colección Nacional de Insectos (CNIN)...")
    
    # Aquí estamos pasando las meta-etiquetas para el archivo de referencias
    ruta_insectos = await manager.descargar_dataset_csv(
        url=url_coleccion_insectos,
        filename="CNIN_polinizadores.csv",
        titulo_ref="Colección Nacional de Insectos (CNIN) - Polinizadores",
        desc_ref="Registros históricos de recolección de polinizadores nativos en territorio mexicano resguardados por el Instituto de Biología de la UNAM."
    )
    
    # 2. Dataset de Flora Nativa
    url_coleccion_herbario = "https://datosabiertos.unam.mx/IBUNAM:MEXU:Flora.csv"
    print("\nDescargando Herbario Nacional (MEXU)...")
    ruta_flora = await manager.descargar_dataset_csv(
        url=url_coleccion_herbario,
        filename="MEXU_flora_nativa.csv",
        titulo_ref="Herbario Nacional de México (MEXU)",
        desc_ref="Base de datos de especímenes botánicos recolectados en todo México. Provee información crucial para identificar plantas nativas."
    )
    
    print("\n✅ Descarga Masiva Finalizada.")
    print(f"Los datos crudos se encuentran en: {data_dir}")
    print(f"Puedes consultar el libro de referencias bibliográficas en: {ref_file}")

if __name__ == "__main__":
    asyncio.run(main())
