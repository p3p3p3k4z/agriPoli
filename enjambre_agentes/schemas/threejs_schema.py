from pydantic import BaseModel, Field
from typing import List, Optional

class Coordenadas3D(BaseModel):
    x: float = Field(description="Posición en el eje X (plano del terreno)")
    y: float = Field(default=0.0, description="Posición en el eje Y (altura sobre el terreno, generalmente 0)")
    z: float = Field(description="Posición en el eje Z (profundidad en el plano del terreno)")

class Dimensiones(BaseModel):
    radio: Optional[float] = Field(default=None, description="Radio de siembra si es una planta individual o zona circular")
    largo: Optional[float] = Field(default=None, description="Largo de la parcela o barrera")
    ancho: Optional[float] = Field(default=None, description="Ancho de la parcela o barrera")

class PlantaEstructurada(BaseModel):
    id_planta: str = Field(description="Identificador único (ej. 'maiz_01')")
    nombre_cientifico: str = Field(description="Nombre taxonómico")
    nombre_comun: str = Field(description="Nombre coloquial")
    tipo: str = Field(description="Clasificación: 'cultivo_principal', 'cultivo_rotacion', 'barrera_viva', 'isla_polinizadora', 'repelente_plagas'")
    color_hex: str = Field(description="Color representativo en formato Hexadecimal (ej. #2ecc71) para el renderizado 3D")
    coordenadas: Coordenadas3D = Field(description="Posición relativa central en el diseño espacial")
    dimensiones: Dimensiones = Field(description="Espacio físico que ocupará esta especie en el terreno")
    justificacion_biologica: str = Field(description="Razón breve de su ubicación (ej. 'Fija nitrógeno junto al maíz' o 'Atrae abejas meliponas')")

class CapaSuelo(BaseModel):
    tipo_suelo: str = Field(description="Tipo de suelo según clasificación taxonómica")
    humedad_objetivo_porcentaje: float = Field(description="Meta de humedad a retener gracias al diseño")
    color_terreno_hex: str = Field(default="#8B4513", description="Color del terreno base para renderizar")

class Mapa3D(BaseModel):
    """
    Estructura final que el Agente Estructurador generará.
    Esta estructura está diseñada para ser leída directamente por un motor Three.js.
    """
    region_nombre: str = Field(description="Nombre de la zona o parcela (ej. 'Milpa Regenerativa Oaxaca')")
    terreno: CapaSuelo = Field(description="Propiedades base del suelo sobre el que se dibuja el mapa")
    elementos_botanicos: List[PlantaEstructurada] = Field(description="Lista de todas las plantas y cultivos con sus coordenadas")
    indicador_degradacion_inicial: float = Field(description="Índice de degradación original (input del modelo Random Forest)")
    notas_agronomicas: List[str] = Field(description="Instrucciones breves de manejo para la interfaz de usuario")
