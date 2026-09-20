"""
Nodo Sintetizador Estructurado — El "cerebro" del enjambre.

Procesa todo el contexto recuperado por los nodos Investigador y Scraper,
y fuerza la salida como JSON estructurado usando with_structured_output(DatosRegion).

Este es el nodo que diferencia a AgriPoli de OptiAgent: en lugar de generar
texto libre (como scientific_writer_node en OptiAgent), produce un JSON
riguroso conforme al schema Pydantic DatosRegion.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage

from agents.state import ScrapingState
from config.models import get_llm
from schemas.ecology import DatosRegion


# --- Prompt del Sintetizador ---

PROMPT_SISTEMA = """Eres un ecólogo, agrónomo y biólogo experto en México, con conocimiento profundo 
de la biodiversidad, agricultura y geografía del país. Tu tarea es sintetizar datos 
recopilados de múltiples fuentes web en un JSON estructurado y riguroso.

ERES PARTE DEL SISTEMA INTERACTIVO INTELIGENTE PARA EL MANEJO AGRÍCOLA Y PRESERVACIÓN DE POLINIZADORES (AGRIPOLI) QUE PROYECTA "ISLAS DE POLINIZADORES" Y RECOMIENDA CULTIVOS.

REGLAS ESTRICTAS:
1. Solo incluye datos que estén RESPALDADOS por el contenido proporcionado.
2. Si no hay información para un campo, usa null en lugar de inventar datos.
3. Los nombres científicos deben seguir la nomenclatura binomial correcta (Género especie).
4. Prioriza información de fuentes institucionales: CONABIO, SADER, INIFAP, INEGI, UNAM.
5. El campo "fuente" de cada elemento DEBE contener la URL real de donde se extrajo el dato.
6. Para estatus de conservación, usa las categorías de NOM-059-SEMARNAT o Lista Roja IUCN.
7. Los rangos numéricos deben ser listas de 2 elementos [min, max].
8. Las coordenadas deben ser [latitud, longitud] en formato decimal.
9. Incluye en "fuentes_consultadas" TODAS las URLs que aparecen en los contenidos.
10. En "recomendaciones_preliminares", sugiere cultivos y acciones basadas en los datos.
"""

PROMPT_USUARIO = """Sintetiza los siguientes datos recopilados sobre la región "{region}" de México
en el formato JSON estructurado solicitado.

Fecha de extracción: {fecha}

=== DATOS DE POLINIZADORES ===
{contenido_polinizadores}

=== DATOS DE AGRICULTURA ===
{contenido_agricultura}

=== DATOS CLIMÁTICOS ===
{contenido_clima}

=== DATOS DE FLORA NATIVA ===
{contenido_flora}

=== DATOS DE SUELO ===
{contenido_suelo}

=== CONTEXTO ADICIONAL (RAG) ===
{contenido_rag}
"""


def sintetizador_node(state: ScrapingState) -> dict[str, Any]:
    """Nodo Sintetizador: convierte todo el contexto en JSON estructurado DatosRegion.
    
    Usa with_structured_output(DatosRegion) para forzar que el LLM produzca
    un JSON válido conforme al schema Pydantic. Si el structured output falla,
    hace un fallback a generación de texto + parsing manual.
    """
    region = state["region"]
    provider = state["provider"]
    model_name = state.get("llm_model_name")
    
    print(f"\n{'='*60}")
    print(f"(˘_˘) [AGENTE: SINTETIZADOR] Procesando datos para: {region}")
    print(f"(˘_˘) [AGENTE: SINTETIZADOR] Generando JSON estructurado con {provider}...")
    print(f"{'='*60}")
    
    llm = get_llm(provider, model_name, temperature=0.1)
    errores = list(state.get("errores", []))
    fecha_hoy = date.today().isoformat()
    
    # Construir el prompt con todo el contenido recopilado
    prompt_usuario = PROMPT_USUARIO.format(
        region=region,
        fecha=fecha_hoy,
        contenido_polinizadores=state.get("contenido_polinizadores", "Sin datos"),
        contenido_agricultura=state.get("contenido_agricultura", "Sin datos"),
        contenido_clima=state.get("contenido_clima", "Sin datos"),
        contenido_flora=state.get("contenido_flora", "Sin datos"),
        contenido_suelo=state.get("contenido_suelo", "Sin datos"),
        contenido_rag=state.get("contenido_rag", "Sin datos adicionales"),
    )
    
    messages = [
        SystemMessage(content=PROMPT_SISTEMA),
        HumanMessage(content=prompt_usuario),
    ]
    
    # --- Intento 1: with_structured_output ---
    try:
        print("[._.] [AGENTE: SINTETIZADOR] Intentando with_structured_output(DatosRegion)...")
        structured_llm = llm.with_structured_output(DatosRegion)
        resultado: DatosRegion = structured_llm.invoke(messages)
        
        # Asegurar que la fecha está presente
        if not resultado.fecha_extraccion:
            resultado.fecha_extraccion = fecha_hoy
        
        json_str = resultado.model_dump_json(indent=2, exclude_none=False)
        
        # Contar datos extraídos para el log
        n_polinizadores = len(resultado.polinizadores)
        n_cultivos = len(resultado.cultivos)
        n_flora = len(resultado.flora_nativa)
        n_fuentes = len(resultado.fuentes_consultadas)
        
        print(f"\n(^_^) [OK] [SINTETIZADOR] JSON generado exitosamente:")
        print(f"  * Polinizadores: {n_polinizadores}")
        print(f"  * Cultivos: {n_cultivos}")
        print(f"  * Flora nativa: {n_flora}")
        print(f"  * Fuentes: {n_fuentes}")
        print(f"  * Tamaño JSON: {len(json_str):,} bytes")
        
        return {
            "datos_estructurados": json_str,
            "errores": errores,
        }
        
    except Exception as e:
        error_msg = f"Sintetizador: Error en structured_output: {e}"
        print(f"(¬_¬) [ALERTA: SINTETIZADOR] {error_msg}")
        errores.append(error_msg)
    
    # --- Intento 2: Fallback a generación de texto + parsing ---
    try:
        print("[._.] [AGENTE: SINTETIZADOR] Fallback: generando texto + parsing manual...")
        
        fallback_prompt = prompt_usuario + (
            "\n\nIMPORTANTE: Responde ÚNICAMENTE con el objeto JSON válido que cumpla con el schema DatosRegion. "
            "No incluyas markdown, ni bloques ```json, ni explicaciones adicionales. Solo el JSON crudo."
        )
        
        response = llm.invoke([
            SystemMessage(content=PROMPT_SISTEMA),
            HumanMessage(content=fallback_prompt),
        ])
        
        # Limpiar posibles bloques markdown si el modelo los incluyó
        texto = response.content.strip()
        if texto.startswith("```json"):
            texto = texto[7:]
        elif texto.startswith("```"):
            texto = texto[3:]
        if texto.endswith("```"):
            texto = texto[:-3]
        texto = texto.strip()
        
        # Validar con Pydantic
        parsed = json.loads(texto)
        resultado = DatosRegion(**parsed)
        
        if not resultado.fecha_extraccion:
            resultado.fecha_extraccion = fecha_hoy
            
        json_str = resultado.model_dump_json(indent=2, exclude_none=False)
        
        print(f"(^_^) [OK] [SINTETIZADOR] JSON generado via fallback ({len(json_str):,} bytes)")
        
        return {
            "datos_estructurados": json_str,
            "errores": errores,
        }
        
    except Exception as e2:
        error_msg2 = f"Sintetizador: Error en fallback: {e2}"
        print(f"[X_X] [ERROR: SINTETIZADOR] {error_msg2}")
        errores.append(error_msg2)
        
        # Generar un JSON mínimo de emergencia
        minimal = DatosRegion(
            region=region,
            estado=region.split(",")[-1].strip() if "," in region else "México",
            fecha_extraccion=fecha_hoy,
            fuentes_consultadas=[],
        )
        
        return {
            "datos_estructurados": minimal.model_dump_json(indent=2),
            "errores": errores,
        }
