from pydantic import BaseModel, Field
from typing import List, Optional

class Cultivo(BaseModel):
    nombre: str = Field(..., description="Nombre común del cultivo (ej. Maíz grano, Frijol).")
    ciclo: str = Field(..., description="Ciclo agrícola: 'Otoño-Invierno', 'Primavera-Verano' o 'Perennes'.")
    modalidad: str = Field(..., description="Riego o Temporal.")
    superficie_sembrada_ha: float = Field(0.0, description="Hectáreas sembradas.")
    rendimiento_ton_ha: Optional[float] = Field(None, description="Rendimiento en toneladas por hectárea.")
    produccion_ton: Optional[float] = Field(None, description="Producción total en toneladas.")

class AgroRegionData(BaseModel):
    estado: str = Field(..., description="Nombre del Estado en México.")
    municipio: str = Field(..., description="Nombre del Municipio.")
    anio_estadistico: int = Field(..., description="Año de la estadística reportada.")
    cultivos: List[Cultivo] = Field(default_factory=list, description="Lista de cultivos presentes en la región.")
    
    class Config:
        json_schema_extra = {
            "example": {
                "estado": "Jalisco",
                "municipio": "Zapopan",
                "anio_estadistico": 2023,
                "cultivos": [
                    {
                        "nombre": "Maíz grano",
                        "ciclo": "Primavera-Verano",
                        "modalidad": "Temporal",
                        "superficie_sembrada_ha": 15000.5,
                        "rendimiento_ton_ha": 6.5,
                        "produccion_ton": 97503.25
                    }
                ]
            }
        }
