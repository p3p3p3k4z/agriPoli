"""
Modelos Pydantic para la salida JSON estructurada del Enjambre de Agentes.

Estos schemas definen la estructura rigurosa de los datos ecológicos, geográficos
y agrícolas recolectados para cada región de México. Son consumidos por el sistema
AgriPoli para proyectar "islas de polinizadores" y recomendar cultivos.

El Nodo Sintetizador usa `with_structured_output(DatosRegion)` para forzar
que el LLM produzca JSON válido conforme a estos schemas.
"""
from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field


class Polinizador(BaseModel):
    """Especie polinizadora nativa de México."""

    nombre_comun: str = Field(
        description="Nombre común en español de la especie polinizadora"
    )
    nombre_cientifico: Optional[str] = Field(
        default=None,
        description="Nombre científico binomial (género + especie)",
    )
    familia: Optional[str] = Field(
        default=None,
        description="Familia taxonómica (ej. Apidae, Nymphalidae)",
    )
    tipo: Literal[
        "abeja",
        "mariposa",
        "colibri",
        "murcielago",
        "avispa",
        "escarabajo",
        "mosca",
        "otro",
    ] = Field(description="Tipo general de polinizador")
    estatus_conservacion: Optional[str] = Field(
        default=None,
        description="Estatus según NOM-059-SEMARNAT, Lista Roja IUCN, o CITES",
    )
    plantas_asociadas: list[str] = Field(
        default_factory=list,
        description="Lista de plantas que poliniza esta especie",
    )
    temporada_actividad: Optional[str] = Field(
        default=None,
        description="Época de mayor actividad (ej. 'marzo-septiembre', 'todo el año')",
    )
    fuente: str = Field(
        description="URL o referencia institucional de donde se obtuvo el dato"
    )


class Cultivo(BaseModel):
    """Cultivo agrícola con datos agroecológicos para una región de México."""

    nombre_comun: str = Field(
        description="Nombre común del cultivo en español"
    )
    nombre_cientifico: Optional[str] = Field(
        default=None,
        description="Nombre científico binomial del cultivo",
    )
    tipo: Literal[
        "milpa",
        "hortaliza",
        "frutal",
        "grano",
        "leguminosa",
        "forrajero",
        "industrial",
        "otro",
    ] = Field(description="Categoría agrícola del cultivo")
    ciclo_cultivo: Optional[str] = Field(
        default=None,
        description="Ciclo agrícola (ej. 'Primavera-Verano', 'Otoño-Invierno', 'Perenne')",
    )
    rango_altitud_msnm: Optional[list[int]] = Field(
        default=None,
        description="Rango de altitud óptima en metros sobre el nivel del mar [min, max]",
    )
    temperatura_optima_c: Optional[list[float]] = Field(
        default=None,
        description="Rango de temperatura óptima en °C [min, max]",
    )
    precipitacion_mm: Optional[list[int]] = Field(
        default=None,
        description="Rango de precipitación requerida en mm/año [min, max]",
    )
    tipo_suelo_preferido: Optional[list[str]] = Field(
        default=None,
        description="Tipos de suelo donde crece mejor (ej. 'franco-arcilloso', 'volcánico')",
    )
    polinizadores_clave: Optional[list[str]] = Field(
        default=None,
        description="Polinizadores principales que requiere este cultivo",
    )
    rendimiento_ton_ha: Optional[float] = Field(
        default=None,
        description="Rendimiento promedio en toneladas por hectárea",
    )
    fuente: str = Field(
        description="URL o referencia institucional de donde se obtuvo el dato"
    )


class FloraRegional(BaseModel):
    """Planta nativa o endémica relevante para la ecología de la región."""

    nombre_comun: str = Field(
        description="Nombre común en español de la planta"
    )
    nombre_cientifico: Optional[str] = Field(
        default=None,
        description="Nombre científico binomial",
    )
    tipo: Literal[
        "arbol",
        "arbusto",
        "hierba",
        "cactacea",
        "epifita",
        "trepadora",
        "otro",
    ] = Field(description="Tipo morfológico de la planta")
    uso_ecologico: Optional[str] = Field(
        default=None,
        description="Función ecológica principal (ej. 'nectarífera', 'fijadora de nitrógeno', 'cortavientos', 'melífera')",
    )
    estatus_conservacion: Optional[str] = Field(
        default=None,
        description="Estatus según NOM-059-SEMARNAT o Lista Roja IUCN",
    )
    temporada_floracion: Optional[str] = Field(
        default=None,
        description="Época de floración (ej. 'febrero-mayo', 'todo el año')",
    )
    fuente: str = Field(
        description="URL o referencia institucional de donde se obtuvo el dato"
    )


class ClimaRegional(BaseModel):
    """Datos climáticos de la región de estudio."""

    clasificacion_koppen: Optional[str] = Field(
        default=None,
        description="Clasificación climática de Köppen (ej. 'BSk', 'Cwa', 'Aw')",
    )
    temperatura_media_anual_c: Optional[float] = Field(
        default=None,
        description="Temperatura media anual en grados Celsius",
    )
    precipitacion_anual_mm: Optional[float] = Field(
        default=None,
        description="Precipitación media anual en milímetros",
    )
    temporada_lluvias: Optional[str] = Field(
        default=None,
        description="Período de lluvias (ej. 'junio-octubre')",
    )
    temporada_secas: Optional[str] = Field(
        default=None,
        description="Período seco (ej. 'noviembre-mayo')",
    )
    riesgos_climaticos: Optional[list[str]] = Field(
        default=None,
        description="Eventos climáticos de riesgo (ej. 'heladas', 'sequías', 'huracanes', 'granizo')",
    )
    fuente: str = Field(
        description="URL o referencia institucional de donde se obtuvo el dato"
    )


class SueloRegional(BaseModel):
    """Datos edafológicos de la región de estudio."""

    tipo_suelo_dominante: Optional[str] = Field(
        default=None,
        description="Tipo de suelo dominante según clasificación WRB/FAO (ej. 'Leptosol', 'Vertisol', 'Regosol')",
    )
    ph_rango: Optional[list[float]] = Field(
        default=None,
        description="Rango de pH del suelo [min, max]",
    )
    materia_organica_pct: Optional[float] = Field(
        default=None,
        description="Porcentaje de materia orgánica en el suelo",
    )
    profundidad_util_cm: Optional[float] = Field(
        default=None,
        description="Profundidad útil del suelo en centímetros",
    )
    problematica: Optional[list[str]] = Field(
        default=None,
        description="Problemas edafológicos (ej. 'erosión hídrica', 'salinización', 'compactación')",
    )
    fuente: str = Field(
        description="URL o referencia institucional de donde se obtuvo el dato"
    )


class DatosRegion(BaseModel):
    """Schema raíz: Datos ecológicos, agrícolas y geográficos completos de una región de México.
    
    Este modelo es el output final del Enjambre de Agentes y es consumido
    directamente por el sistema AgriPoli para modelado 3D y análisis predictivo.
    """

    region: str = Field(
        description="Nombre completo de la región (ej. 'La Mixteca, Oaxaca')"
    )
    estado: str = Field(
        description="Estado de la República Mexicana"
    )
    coordenadas_aprox: Optional[list[float]] = Field(
        default=None,
        description="Coordenadas aproximadas del centro de la región [latitud, longitud]",
    )
    altitud_media_msnm: Optional[int] = Field(
        default=None,
        description="Altitud media de la región en metros sobre el nivel del mar",
    )

    # --- Datos ambientales ---
    clima: Optional[ClimaRegional] = Field(
        default=None,
        description="Datos climáticos de la región",
    )
    suelo: Optional[SueloRegional] = Field(
        default=None,
        description="Datos edafológicos de la región",
    )

    # --- Datos biológicos y agrícolas ---
    polinizadores: list[Polinizador] = Field(
        default_factory=list,
        description="Polinizadores nativos identificados en la región",
    )
    cultivos: list[Cultivo] = Field(
        default_factory=list,
        description="Cultivos agrícolas relevantes para la región",
    )
    flora_nativa: list[FloraRegional] = Field(
        default_factory=list,
        description="Flora nativa o endémica relevante para la ecología regional",
    )

    # --- Análisis ---
    problematicas_ecologicas: Optional[list[str]] = Field(
        default=None,
        description="Problemáticas ecológicas identificadas (ej. 'deforestación', 'pérdida de polinizadores', 'monocultivo')",
    )
    recomendaciones_preliminares: Optional[list[str]] = Field(
        default=None,
        description="Recomendaciones iniciales de cultivos, restauración ecológica o islas de polinizadores",
    )

    # --- Metadatos ---
    fuentes_consultadas: list[str] = Field(
        default_factory=list,
        description="Todas las URLs y referencias institucionales consultadas durante la extracción",
    )
    fecha_extraccion: str = Field(
        description="Fecha de la extracción en formato ISO 8601 (ej. '2026-09-11')",
    )
