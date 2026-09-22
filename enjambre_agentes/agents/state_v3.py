"""
Estado jerarquico V3 del Sistema de Apoyo Multiagente AgriPoli.

Define TypedDicts independientes por grupo de agentes y el estado maestro
del Supervisor. Permite que cada sub-grafo opere con su propio contexto
sin contaminar el estado de otros grupos.
"""
from __future__ import annotations

from typing import TypedDict, Annotated
import operator
from langgraph.graph.message import add_messages


# ─────────────────────────────────────────────────────────────────────────────
# Estado Grupo Extractor
# ─────────────────────────────────────────────────────────────────────────────

class EstadoGrupoExtractor(TypedDict, total=False):
    """Estado interno del Grupo Extractor.
    Gestiona la recopilacion de informacion externa (web, academica, gubernamental).
    """
    consulta_original: str       # Peticion o tematica original del usuario
    region: str
    flow_type: str              # "Hibrido" | "Solo Local" | "Solo Web"
    # Resultados paralelos de los mini-agentes
    resultado_tavily: str
    resultado_academico: str
    resultado_scraper: str
    resultado_mini_referencias: str  # Trazabilidad y fuentes bibliograficas formateadas
    # Output del fusionador_extractor (join)
    contexto_web: str
    fuentes_web: Annotated[list[str], operator.add]
    referencias_fuentes: list[str]
    # Flag de control del nodo Descargador
    descarga_confirmada: bool   # True si el usuario confirmo la descarga


# ─────────────────────────────────────────────────────────────────────────────
# Estado Grupo Agronomo
# ─────────────────────────────────────────────────────────────────────────────

class EstadoGrupoAgronomo(TypedDict, total=False):
    """Estado interno del Grupo Agronomo.
    Gestiona propuestas de cultivos, rotaciones y analisis de suelo.
    Soporta loop de retroalimentacion interna desde el fusionador.
    """
    consulta_original: str        # Peticion original del usuario
    region: str
    contexto_extractor: str       # Input del Grupo Extractor
    contexto_rag_agro: str        # RAG local: suelo + agricultura
    indice_degradacion_rf: float  # Indice del modelo Random Forest (0-1)
    historial_siembra: list[str]  # Cultivos anteriores del productor
    # Resultados paralelos de mini-agentes
    resultado_mini_suelo: str
    resultado_mini_cultivo: str
    resultado_mini_siap: str
    resultado_mini_inegi: str
    resultado_mini_calculadora: str
    resultado_mini_rotacion: str      # Rotacion regenerativa (4 grupos funcionales)
    resultado_mini_referencias: str   # Trazabilidad, antecedentes tecnicos y fuentes Tavily
    referencias_fuentes: list[str]    # Lista consolidada de URLs y documentos citados
    # Propuestas generadas
    propuestas_agricolas: list[dict]
    prompt_cultivo_terreno: str       # Prompt hiperrealista de recuadro de cultivo / parcela (mini_prompt_cultivo)
    detalles_cultivo_terreno: dict
    # Control del loop de retroalimentacion
    anotacion_fusionador_agro: str  # Mensaje de error/correccion del fusionador
    ciclo_agronomo: int             # Contador de ciclos (max = config YAML)
    estado_fusion_agro: str         # "APROBADO" | "RECHAZADO" | "PENDIENTE"


# ─────────────────────────────────────────────────────────────────────────────
# Estado Grupo Ecologico
# ─────────────────────────────────────────────────────────────────────────────

class EstadoGrupoEcologico(TypedDict, total=False):
    """Estado interno del Grupo Ecologico.
    Gestiona el diseno de islas polinizadoras y matrices de conservacion.
    Soporta loop de retroalimentacion interna desde el fusionador.
    """
    consulta_original: str        # Peticion original del usuario
    region: str
    contexto_extractor: str       # Input del Grupo Extractor
    propuestas_agricolas: list[dict]  # Input del Grupo Agronomo (para compatibilidad)
    contexto_rag_eco: str         # RAG local: polinizadores + flora
    # Resultados paralelos de mini-agentes
    resultado_mini_flora: str
    resultado_mini_polinizadores: str
    resultado_mini_catalogo: str
    resultado_mini_gbif: str
    resultado_mini_control_biologico: str   # Depredadores e insectos beneficiosos
    resultado_mini_atractores: str          # Banda floral y corredores polinizadores
    resultado_mini_referencias: str         # Fuentes y normas ecologicas (NOM-059, CONABIO)
    referencias_fuentes: list[str]          # URLs y catalogos citados
    # Propuestas generadas
    propuestas_ecologicas: list[dict]
    # Control del loop de retroalimentacion
    anotacion_fusionador_eco: str  # Mensaje de error/correccion del fusionador
    ciclo_ecologico: int
    estado_fusion_eco: str         # "APROBADO" | "RECHAZADO" | "PENDIENTE"


# ─────────────────────────────────────────────────────────────────────────────
# Estado Grupo 3D
# ─────────────────────────────────────────────────────────────────────────────

class EstadoGrupo3D(TypedDict, total=False):
    """Estado interno del Grupo Generador 3D (Opcional).
    Traduce propuestas narrativas a JSON Three.js estructurado.
    """
    consulta_original: str                  # Peticion original del usuario
    region: str
    indice_degradacion_rf: float
    suelo_resumen: str
    propuestas_agricolas: list[dict]
    propuestas_ecologicas: list[dict]
    resultado_mini_referencias: str         # Estandares espaciales y referencias Three.js
    referencias_fuentes: list[str]
    # Output del estructurador
    json_threejs_final: dict
    validacion_3d: str            # "VALIDO" | "INVALIDO"
    ciclo_3d: int                 # Reintentos si el JSON es invalido (max 2)
    prompt_isla_polinizadora: str  # Prompt hiperrealista para modelado 3D (mini_prompt_isla)
    detalles_isla_polinizadora: dict


# ─────────────────────────────────────────────────────────────────────────────
# Estado Maestro del Supervisor V3
# ─────────────────────────────────────────────────────────────────────────────

class EstadoMaestroV3(TypedDict, total=False):
    """Estado global del Grafo Maestro V3.
    Agrega los resultados de los cuatro grupos de agentes y controla
    el flujo de orquestacion y los loops inter-grupo.
    """
    # Inputs iniciales
    region: str
    indice_degradacion_rf: float
    historial_siembra: list[str]
    # Historial de mensajes del Supervisor (conversacional)
    mensajes: Annotated[list, add_messages]
    # Resultados acumulados por grupo
    contexto_extractor: str
    propuestas_agricolas: list[dict]
    propuestas_ecologicas: list[dict]
    json_threejs_final: dict
    # Control de flujo del Supervisor
    activar_3d: bool
    notas_supervisor: Annotated[list[str], operator.add]
    iteraciones_supervisor: int   # Contador de loops inter-grupo (max = config YAML)
    estado_final: str             # "COMPLETADO" | "ERROR" | "PENDIENTE_3D"
    # Sintesis y Diagnostico Ejecutivo (Agente Sintetizador)
    resumen_ejecutivo: str        # Reporte integral y estructurado en Markdown
    dossier_tecnico: dict         # Metadatos tecnicos consolidados
    referencias_fuentes: Annotated[list[str], operator.add]  # URLs y citas acumuladas
    prompt_isla_polinizadora: str  # Prompt hiperrealista para modelado 3D de isla polinizadora
    detalles_isla_polinizadora: dict
    prompt_cultivo_terreno: str    # Prompt hiperrealista de parcela de cultivo
    detalles_cultivo_terreno: dict
    # Configuracion activa (leida del YAML al inicio)
    flow_type: str
    max_ciclos: int

