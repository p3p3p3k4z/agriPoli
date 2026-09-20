from typing import TypedDict, List, Dict, Any, Annotated
import operator

class EstadoEnjambreV2(TypedDict):
    """
    Estado global del Grafo para la Arquitectura Multiagente AgriPoli V2 (Soporte de Decisiones 3D).
    """
    # 1. Input Inicial (Del modelo Random Forest y Usuario)
    region: str
    indice_degradacion_rf: float
    historial_siembra: List[str]
    
    # 2. Extracciones del Agente Investigador
    datos_climaticos: Dict[str, Any]
    datos_geospatiales: Dict[str, Any]
    
    # 3. Propuestas del Agente Agrícola
    propuestas_agricolas: List[Dict[str, Any]]
    
    # 4. Propuestas del Agente Ecológico
    propuestas_ecologicas: List[Dict[str, Any]]
    
    # 5. Memoria de Evaluación del Supervisor
    # Usamos Annotated con operator.add para ir guardando el historial de revisiones
    revisiones_supervisor: Annotated[List[str], operator.add]
    estado_revision: str # "APROBADO" o "RECHAZADO"
    iteraciones_revision: int # Para prevenir deadlocks
    
    # 6. Salida Estructurada Final (Agente Estructurador)
    # Contendrá el JSON validado bajo el esquema Mapa3D
    json_threejs_final: Dict[str, Any]
