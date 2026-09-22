"""
Mini-Agente: Generador de Prompts para Islas Polinizadoras (AgriPoli V3).

Responsabilidad:
Extraer las características ecológicas, agronómicas y paisajísticas de cualquier
región de México (ej. La Mixteca, Oaxaca; Valles Centrales; Puerto Escondido; Mérida, etc.)
y ensamblar un prompt de imagen hiperrealista a nivel del suelo listo como referencia
para modelado 3D y concept art, en español (plantilla oficial) e inglés (Midjourney/Flux).
"""
from __future__ import annotations

import os
import json
import re
from pathlib import Path
from typing import Optional, Any

from config.agri_logger import log_mini_agente, log_ok, log_info, log_error
from config.models import get_llm_para_agente
from tools.gestor_regiones import parsear_region_jerarquica, asegurar_directorio_regional


# Conocimiento biogeográfico base para ecorregiones mexicanas frecuentes (fallback rápido)
CONOCIMIENTO_REGIONAL_BASE: dict[str, dict[str, Any]] = {
    "mixteca": {
        "region_nombre": "la Mixteca de Oaxaca",
        "dosel": "Tepehuaje (Lysiloma acapulcense), Mezquite (Prosopis laevigata), Guaje (Leucaena leucocephala) y Copal (Bursera)",
        "sotobosque": "Salvia mexicana, Dalia coccinea, Lantana camara y Huizache",
        "cobertura": "Cempasúchil (Tagetes erecta), Cosmos sulphureus, Albahaca silvestre y pastos nativos",
        "polinizadores": "abejas meliponas (Scaptotrigona mexicana), abejas nativas solitarias, mariposas monarca y colibrí oaxaqueño",
        "insectos_auxiliares": "mariquitas (Coccinellidae), crisopas verdes (Chrysoperla carnea) y avispas parasitoides",
        "infraestructura": "hotel de insectos hecho de troncos huecos y cañas de carrizo, bebedero de agua con piedras de apoyo, zona de compostaje y perchas de madera para aves insectívoras",
        "terrenos": "milpa tradicional (maíz y frijol), agave espadín oaxaqueño, huerto de pitaya/nopales y calabaza criolla",
        "horizonte": "las serranías y lomeríos rojizos característicos de la Mixteca Alta oaxaqueña, con luz natural dorada de atardecer, sombras suaves y cielo despejado",
    },
    "puerto_escondido": {
        "region_nombre": "la Costa de Puerto Escondido, Oaxaca",
        "dosel": "Parota (Enterolobium cyclocarpum), Primavera (Tabebuia donnell-smithii) y Guaje blanco",
        "sotobosque": "Lantana camara, Heliconias silvestres, Dalia silvestre y arbustos de Chaya",
        "cobertura": "Cempasúchil costeño, Cosmos y leguminosas rastreras fijadoras de nitrógeno",
        "polinizadores": "abejas meliponas costeñas (Melipona fasciata), mariposas tropicales, abejorros Bombus y colibríes canelos",
        "insectos_auxiliares": "mariquitas, mantis religiosas y crisopas en el follaje",
        "infraestructura": "hotel de insectos de cañas de bambú local, pileta sombreada con guijarros de río y zona de compostaje orgánico",
        "terrenos": "maíz de temporal, café bajo sombra, huerto de papayas/mangos y cultivos de ajonjolí",
        "horizonte": "la franja costera de Oaxaca con vegetación tropical caducifolia, luz solar cálida y atmósfera luminosa de costa pacífica",
    },
    "yucatan": {
        "region_nombre": "la Península de Yucatán",
        "dosel": "Balché (Lonchocarpus violaceus), Jabín (Piscidia piscipula) y Chaka (Bursera simaruba)",
        "sotobosque": "Tajonal (Viguiera dentata), flor de San Diego y Lantana silvestre",
        "cobertura": "Campanitas silvestres (Ipomoea), bejucos melíferos y leguminosas rastreras",
        "polinizadores": "abejas sagradas mayas Melipona beecheii, abejas trigonas, mariposas de selva y colibríes yucatecos",
        "insectos_auxiliares": "mariquitas locales, chinches benéficas y crisopas",
        "infraestructura": "jobones o cajas tradicionales mayas de meliponicultura, hotel de insectos rústico y bebedero con piedras planas",
        "terrenos": "milpa maya (maíz, frijol ibes y calabaza chihua), henequén, huerto de cítricos y chile habanero",
        "horizonte": "la planicie cárstica con monte bajo yucateco, piedra caliza visible y cielo azul radiante",
    }
}


def _extraer_datos_desde_archivos_locales(estado: str, municipio: str, project_root: Path) -> Optional[dict[str, Any]]:
    """Intenta leer datos previos de datos_relevantes.json o diagnostico.md si existen."""
    region_dir = project_root / "data" / "regiones" / estado / municipio
    datos_json_path = region_dir / f"datos_relevantes_{estado}_{municipio}.json"
    if not datos_json_path.exists():
        datos_json_path = region_dir / "datos_relevantes.json"

    if datos_json_path.exists():
        try:
            with open(datos_json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _generar_propiedades_con_llm(region: str, datos_previos: Optional[dict] = None) -> dict[str, str]:
    """Utiliza el LLM asignado para deducir con precisión botánica las propiedades de la región."""
    llm = get_llm_para_agente("mini_prompt_isla")

    contexto_previo = ""
    if datos_previos:
        contexto_previo = f"\nDatos ya extraídos de la región:\n{json.dumps(datos_previos, ensure_ascii=False, indent=2)[:1500]}"

    prompt_extraccion = f"""Eres el Botánico y Diseñador Agroecológico de AgriPoli especializado en Islas Polinizadoras de México.
Para la región: "{region}".
{contexto_previo}

Tu objetivo es determinar las especies nativas exactas y características paisajísticas necesarias para crear un prompt de imagen hiperrealista de una Isla Polinizadora circular ubicada en el centro de cuatro parcelas agrícolas.

Debes responder ÚNICAMENTE en formato JSON con la siguiente estructura exacta (sin explicaciones adicionales ni markdown de bloque):
{{
  "region_nombre": "Nombre descriptivo de la región y estado, México (ej. la Mixteca de Oaxaca, México)",
  "dosel": "3 o 4 árboles medianos nativos de la ecorregión (con nombre común y científico si aplica)",
  "sotobosque": "3 o 4 arbustos y flores nativas con colores vivos y texturas naturales",
  "cobertura": "3 flores rastreras o coberturas del suelo con flores claramente visibles",
  "polinizadores": "Abejas nativas específicas (ej. meliponas locales), abejorros, mariposas y colibríes de la zona",
  "insectos_auxiliares": "Mariquitas, crisopas y fauna auxiliar benéfica",
  "infraestructura": "Hotel de insectos de troncos/cañas, cisterna/bebedero con piedras de descanso, compostaje y perchas",
  "terrenos": "Los 4 terrenos agrícolas completos típicos de esa región con cultivos reales (ej. maíz, café, agave y frutales)",
  "horizonte": "Descripción del horizonte biogeográfico realista de esa región (relieve, montañas/planicies, luz natural y sombras suaves)"
}}
"""
    try:
        respuesta = llm.invoke(prompt_extraccion)
        if hasattr(respuesta, "content"):
            c = respuesta.content
            if isinstance(c, str):
                contenido = c
            elif isinstance(c, list):
                partes = []
                for p in c:
                    if isinstance(p, str):
                        partes.append(p)
                    elif isinstance(p, dict) and "text" in p:
                        partes.append(p["text"])
                    elif hasattr(p, "text"):
                        partes.append(str(p.text))
                    else:
                        partes.append(str(p))
                contenido = "\n".join(partes)
            else:
                contenido = str(c)
        else:
            contenido = str(respuesta)

        # Limpiar bloques markdown si el modelo incluyó ```json ... ```
        limpio = re.sub(r"^```(?:json)?\s*", "", contenido.strip(), flags=re.MULTILINE)
        limpio = re.sub(r"\s*```$", "", limpio.strip(), flags=re.MULTILINE)
        
        # Extraer substring JSON si hay texto adicional
        inicio_json = limpio.find("{")
        fin_json = limpio.rfind("}")
        if inicio_json != -1 and fin_json != -1 and fin_json > inicio_json:
            limpio = limpio[inicio_json:fin_json + 1]

        datos = json.loads(limpio)
        log_ok(f"Propiedades botánicas para '{region}' extraídas exitosamente con LLM.", kaomoji="(^o^)")
        return datos
    except Exception as e:
        log_error(f"Fallback a conocimiento base para '{region}': {e}", kaomoji="[~_~]")
        # Buscar en el conocimiento regional base
        reg_norm = region.lower()
        for k, v in CONOCIMIENTO_REGIONAL_BASE.items():
            if k in reg_norm:
                return v
        # Fallback genérico Oaxaca/Mixteca
        return CONOCIMIENTO_REGIONAL_BASE["mixteca"]


def generar_prompt_isla_polinizadora(
    region: str,
    base_dir: Optional[str] = None,
    guardar_en_disco: bool = True
) -> dict[str, Any]:
    """
    Función principal del mini-agente:
    1. Resuelve la región jerárquica (estado, municipio).
    2. Carga datos regionales previos o deduce propiedades botánicas con LLM.
    3. Ensambla el prompt en Español (plantilla oficial) e Inglés (Midjourney/Flux).
    4. Opcionalmente guarda los archivos en regiones/<estado>/<municipio>/.
    """
    log_mini_agente("MINI_PROMPT_ISLA", f"Generando prompt de isla polinizadora para: {region}", kaomoji="(^o^)/")

    if not base_dir:
        project_root = Path(__file__).resolve().parent.parent
    else:
        project_root = Path(base_dir).resolve()

    estado, municipio, ruta_relativa = parsear_region_jerarquica(region)
    datos_locales = _extraer_datos_desde_archivos_locales(estado, municipio, project_root)

    # Obtener propiedades de la región
    props = _generar_propiedades_con_llm(region, datos_locales)

    region_nombre = props.get("region_nombre", f"{municipio.replace('_', ' ').title()}, {estado.title()}, México")
    dosel = props.get("dosel", "Tepehuaje, Mezquite y Guaje")
    sotobosque = props.get("sotobosque", "Salvia mexicana, Dalia coccinea, Lantana camara")
    cobertura = props.get("cobertura", "Cempasúchil, Cosmos sulphureus, Albahaca silvestre")
    polinizadores = props.get("polinizadores", "abejas meliponas y europeas, mariposas monarca, colibríes")
    insectos_aux = props.get("insectos_auxiliares", "mariquitas y crisopas")
    infraestructura = props.get("infraestructura", "hotel de insectos de troncos y cañas, cisterna de agua, zona de compostaje")
    terrenos = props.get("terrenos", "maíz, café, agave y frutales")
    horizonte = props.get("horizonte", f"el horizonte realista de {region_nombre}, con luz natural, sombras suaves y colores vivos pero realistas")

    # 1. Ensamblar Prompt en Español (Plantilla exacta solicitada por el usuario)
    prompt_es = (
        f"Imagen frontal hiperrealista a nivel del suelo de una Isla Polinizadora circular en {region_nombre}, "
        f"ubicada en el centro de cuatro terrenos agrícolas. La isla está llena de vida:\n"
        f"Dosel de árboles medianos: {dosel}, con hojas verdes y flores visibles.\n"
        f"Sotobosque: arbustos y flores ({sotobosque}) con colores vivos y texturas naturales.\n"
        f"Cobertura del suelo: {cobertura}, con flores claramente visibles.\n"
        f"Polinizadores en acción: {polinizadores} volando y posándose sobre flores.\n"
        f"Insectos auxiliares: {insectos_aux} visibles en el follaje.\n"
        f"Infraestructura ecológica: {infraestructura}.\n"
        f"El círculo de la isla debe ser claramente visible desde el frente, mostrando su forma y vida interna. "
        f"Detrás y alrededor se ven los 4 terrenos agrícolas completos: {terrenos}, con caminos o bordes de parcela bien definidos.\n"
        f"El fondo muestra {horizonte}. Todos los detalles de vegetación, flores y polinizadores deben ser nítidos, "
        f"como en una fotografía profesional a nivel del suelo, lista para referencia de modelado 3D."
    )

    # 2. Ensamblar Prompt en Inglés (Optimizado para Midjourney v6, Flux.1 y DALL-E 3)
    prompt_en = (
        f"Hyperrealistic eye-level ground-level frontal photograph of a lush circular Pollinator Island in {region_nombre}, "
        f"positioned at the intersection of four agricultural fields. The circular sanctuary is teeming with biodiversity: "
        f"Medium tree canopy featuring {dosel} with dense green foliage and visible blooming flowers. "
        f"Understory filled with native flowering shrubs ({sotobosque}) displaying vibrant natural colors and rich leaf textures. "
        f"Ground cover carpeted with blooming {cobertura}. "
        f"Active pollinators in flight and perching: {polinizadores}. "
        f"Beneficial biological control insects visible: {insectos_aux}. "
        f"Ecological infrastructure clearly integrated: {infraestructura}. "
        f"The boundary of the circular pollinator island is clearly defined in the foreground. Surrounding and behind it are the 4 full agricultural plots: "
        f"{terrenos}, bordered by clean earthen access paths. "
        f"The background features {horizonte}. Crisp professional botanical photography, sharp focus on insects and petals, natural ambient daylight, "
        f"soft shadows, volumetric lighting, photorealistic 8k, ideal as an agroecological 3D modeling concept reference --ar 16:9 --v 6.1"
    )

    resultado = {
        "region": region,
        "estado": estado,
        "municipio": municipio,
        "propiedades_extraidas": props,
        "prompt_espanol": prompt_es,
        "prompt_ingles": prompt_en,
    }

    # Guardar en disco en la carpeta regional correspondiente
    if guardar_en_disco:
        try:
            carpetas = asegurar_directorio_regional(region, str(project_root))
            region_dir = carpetas["region_dir"]
            
            # 1. Guardar archivo de texto plano con los prompts
            archivo_txt_desc = region_dir / f"prompt_isla_polinizadora_{estado}_{municipio}.txt"
            archivo_txt_alias = region_dir / "prompt_isla_polinizadora.txt"
            
            contenido_txt = (
                f"========================================================================\n"
                f"PROMPT PARA GENERACIÓN DE IMÁGENES — ISLA POLINIZADORA EN {region_nombre.upper()}\n"
                f"Generado por: AgriPoli V3 (mini_prompt_isla)\n"
                f"========================================================================\n\n"
                f"--- [OPCIÓN 1: PROMPT EN ESPAÑOL (DALL-E 3 / Bing Image Creator)] ---\n\n"
                f"{prompt_es}\n\n"
                f"------------------------------------------------------------------------\n"
                f"--- [OPCIÓN 2: PROMPT EN INGLÉS (Midjourney v6 / Flux.1 / SDXL)] ---\n\n"
                f"{prompt_en}\n\n"
                f"========================================================================\n"
            )
            
            with open(archivo_txt_desc, "w", encoding="utf-8") as f:
                f.write(contenido_txt)
            with open(archivo_txt_alias, "w", encoding="utf-8") as f:
                f.write(contenido_txt)

            # 2. Guardar archivo JSON estructurado
            archivo_json_desc = region_dir / f"prompt_isla_polinizadora_{estado}_{municipio}.json"
            archivo_json_alias = region_dir / "prompt_isla_polinizadora.json"
            with open(archivo_json_desc, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)
            with open(archivo_json_alias, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)

            log_ok(f"Prompt regional guardado en: {ruta_relativa}/prompt_isla_polinizadora.txt", kaomoji="(^_^)/")
            resultado["archivo_txt"] = str(archivo_txt_desc.relative_to(project_root))
            resultado["archivo_json"] = str(archivo_json_desc.relative_to(project_root))
        except Exception as e:
            log_error(f"Error guardando archivos de prompt regional: {e}", kaomoji="[X_X]")

    return resultado


if __name__ == "__main__":
    import sys
    region_test = sys.argv[1] if len(sys.argv) > 1 else "la mixteca, oaxaca"
    res = generar_prompt_isla_polinizadora(region_test)
    print("\n" + "="*70)
    print(f"PROMPT GENERADO PARA: {res['region'].upper()}")
    print("="*70)
    print(res["prompt_espanol"])
    print("\n" + "-"*70)
    print("PROMPT EN INGLÉS (MIDJOURNEY):")
    print("-"*70)
    print(res["prompt_ingles"])
    print("="*70 + "\n")
