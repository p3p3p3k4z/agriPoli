#!/usr/bin/env uv run python
import os
import json
import asyncio
import sys

# Agregar la ruta base
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.agro_data import AgroDataManager
from schemas.agriculture import AgroRegionData, Cultivo

async def main():
    print("=== Iniciando Descarga Masiva Agrícola (SIAP) ===")
    
    # Configuramos el directorio para datos de agricultura
    agro_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'agricultura'))
    manager = AgroDataManager(data_dir=agro_dir)
    
    # Definimos el año a extraer (SIAP Cierre agrícola municipal más reciente estable)
    anio = 2022 
    csv_path = await manager.descargar_siap_csv(anio)
    
    if not csv_path:
        print("La descarga directa de CSV falló. Pasando a scraping como fallback...")
        # Demostración del uso de playwright para fallback
        resultado_scraping = manager.scraping_dinamico_sader("Agricultura en Mexico")
        print(f"Scraping resultado:\n{resultado_scraping[:500]}...")
        return
        
    print("\nProcesando el CSV para generar la estructura JSON masiva por Estado...")
    datos_crudos = manager.procesar_siap_csv(csv_path)
    
    if not datos_crudos:
        print("No se encontraron registros en el CSV.")
        return
        
    # Agrupar datos por Estado -> Municipio
    estructurado = {}
    
    for row in datos_crudos:
        estado = row["estado"]
        municipio = row["municipio"]
        
        if estado not in estructurado:
            estructurado[estado] = {}
            
        if municipio not in estructurado[estado]:
            estructurado[estado][municipio] = AgroRegionData(
                estado=estado,
                municipio=municipio,
                anio_estadistico=anio,
                cultivos=[]
            )
            
        cultivo = Cultivo(
            nombre=row["cultivo"],
            ciclo=row["ciclo"],
            modalidad=row["modalidad"],
            superficie_sembrada_ha=row["superficie_sembrada_ha"],
            produccion_ton=row["produccion_ton"],
            rendimiento_ton_ha=row["produccion_ton"] / row["superficie_sembrada_ha"] if row["superficie_sembrada_ha"] > 0 else 0
        )
        estructurado[estado][municipio].cultivos.append(cultivo)
        
    # Guardar en JSON (Uno por Estado para no saturar memoria)
    for estado, municipios in estructurado.items():
        estado_clean = estado.replace(" ", "_").replace(".", "").lower()
        json_path = os.path.join(agro_dir, f"agricultura_{estado_clean}.json")
        
        # Serializar los modelos Pydantic
        datos_guardar = {mun: obj.model_dump() for mun, obj in municipios.items()}
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(datos_guardar, f, indent=2, ensure_ascii=False)
            
    print(f"\nDescarga y estructuración finalizada. Se generaron {len(estructurado)} archivos JSON por estado en {agro_dir}.")

if __name__ == "__main__":
    asyncio.run(main())
