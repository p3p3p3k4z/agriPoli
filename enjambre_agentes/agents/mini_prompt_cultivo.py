"""
Mini-Agente: Generador de Prompts Agrícolas de Terreno (AgriPoli V3).

Responsabilidad:
Extraer las características agronómicas, edafológicas y de asociación de cultivos
de cualquier región de México (ej. La Mixteca, Oaxaca; Costa; Valles Centrales; Yucatán, etc.)
y ensamblar un prompt de imagen hiperrealista enfocado en un RECUADRO DE TERRENO AGRÍCOLA
bien delimitado con el grupo de cultivos asociados, patrones de siembra y textura de suelo,
listo como referencia de concept art y textura para modelado 3D.
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


# Conocimiento agronómico base para ecorregiones mexicanas frecuentes (fallback rápido)
CONOCIMIENTO_AGRO_BASE: dict[str, dict[str, Any]] = {
    "mixteca": {
        "region_nombre": "la Mixteca Alta, Oaxaca, México",
        "cultivo_principal": "Maíz criollo amarillo y azul de temporal (Zea mays) en cañas vigorosas con espigas y mazorcas en desarrollo",
        "cultivo_asociado": "Frijol trepador negro criollo (Phaseolus vulgaris) enroscándose firmemente en los tallos de maíz",
        "cobertura_suelo": "Calabaza tamalayota o criolla (Cucurbita argyrosperma) con amplias hojas aterciopeladas y flores amarillas cubriendo el suelo",
        "cultivo_borde": "Hileras de maguey espadín (Agave angustifolia) en los linderos y cabeceras de la parcela",
        "patron_siembra": "Surcos tradicionales en curvas de nivel adaptados a la pendiente, con espaciamiento de 80 cm entre hileras",
        "suelo_textura": "Suelo Luvisol rojizo arcilloso y franco-arcilloso con fragmentos de roca caliza y una ligera capa de rastrojo picado como acolchado",
        "manejo_hidrico": "Zanjas de infiltración en contorno con pequeñas microcuencas de retención de humedad de lluvia",
        "delimitacion": "Recuadro de parcela rectangular bien delimitado por caminos de tierra compactada rojiza y bordes de piedra rústica",
        "iluminacion": "Luz solar cálida de media mañana con sombras suaves proyectadas entre las hileras de cultivo, revelando la textura del follaje y el relieve de la tierra",
    },
    "puerto_escondido": {
        "region_nombre": "la Costa de Puerto Escondido, Oaxaca, México",
        "cultivo_principal": "Plantación de Papaya Maradol y plátano macho intercalado con hileras de ajonjolí blanco",
        "cultivo_asociado": "Leguminosa Canavalia ensiformis como abono verde y fijador de nitrógeno entre las calles",
        "cobertura_suelo": "Manto vivo de leguminosas rastreras y trébol tropical que mantiene la frescura del suelo",
        "cultivo_borde": "Barrera viva perimetral de arbustos de Crotalaria y pasto vetiver en las cabeceras",
        "patron_siembra": "Camas de siembra ligeramente elevadas en hileras rectas de 2 metros de separación",
        "suelo_textura": "Suelo aluvial franco-arenoso fértil de color marrón oscuro, rico en materia orgánica superficial y compost visible",
        "manejo_hidrico": "Líneas de manguera de riego por goteo negro mate extendidas ordenadamente a lo largo de cada hilera",
        "delimitacion": "Recuadro de lote agrícola cuadrado delimitado por acequias limpias de drenaje y franjas de tierra limpia",
        "iluminacion": "Luz tropical brillante de mañana con atmósfera limpia y sombras suaves sobre el follaje lustroso",
    },
    "yucatan": {
        "region_nombre": "la Península de Yucatán, México",
        "cultivo_principal": "Milpa maya tradicional (Ich kool) con maíz criollo nal-tel y plantas de chile habanero naranja y verde",
        "cultivo_asociado": "Frijol ibes trepador y frijol xpelón fijando nitrógeno en el suelo cárstico",
        "cobertura_suelo": "Calabaza chihua rastrera con guías robustas y flores abiertas cubriendo los espacios entre rocas",
        "cultivo_borde": "Hileras de henequén (Agave fourcroydes) y plantas aromáticas de orégano de monte en las orillas del recuadro",
        "patron_siembra": "Policultivo en matas agrupadas sobre montículos de suelo fértil entre afloramientos de piedra caliza",
        "suelo_textura": "Suelo Tzek'el pedregoso y Kankab rojizo rico en carbonatos de calcio y hojarasca descompuesta",
        "manejo_hidrico": "Microaspersores rústicos o captación de humedad en pequeñas hondonadas naturales de roca",
        "delimitacion": "Recuadro agrícola rectangular enmarcado por albarradas bajas de piedra caliza blanca-grisácea",
        "iluminacion": "Intensa luz solar caribeña matutina que resalta el contraste entre las rocas calizas y el verdor de las hojas",
    }
}


def _extraer_datos_locales_agricolas(estado: str, municipio: str, project_root: Path) -> Optional[dict[str, Any]]:
    """Lee datos_relevantes.json para obtener los cultivos y suelo de la región."""
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


def _generar_propiedades_agricolas_con_llm(region: str, datos_previos: Optional[dict] = None) -> dict[str, str]:
    """Utiliza el LLM asignado para deducir las propiedades de cultivo y suelo para el recuadro."""
    llm = get_llm_para_agente("mini_prompt_cultivo")

    contexto_previo = ""
    if datos_previos:
        contexto_previo = f"\nDatos ya extraídos de la región:\n{json.dumps(datos_previos, ensure_ascii=False, indent=2)[:1500]}"

    prompt_extraccion = f"""Eres el Ingeniero Agrónomo y Especialista en Agricultura Regenerativa de AgriPoli.
Para la región: "{region}".
{contexto_previo}

Tu objetivo es determinar las características de un RECUADRO O LOTE DE TERRENO AGRÍCOLA delimitado, mostrando un policultivo o asociación de cultivos representativa de esta región, patrón de siembra y textura del suelo.

Debes responder ÚNICAMENTE en formato JSON con la siguiente estructura exacta (sin texto previo ni markdown exterior):
{{
  "region_nombre": "Nombre de la región y estado, México (ej. la Mixteca de Oaxaca, México)",
  "cultivo_principal": "Cultivo dominante típico de la zona (ej. Maíz criollo, Agave espadín, Café bajo sombra, etc.) con descripción visual de follaje y frutos",
  "cultivo_asociado": "Cultivo acompañante o leguminosa fijadora de nitrógeno (ej. frijol trepador criollo, haba, etc.)",
  "cobertura_suelo": "Cultivo rastrero de cobertura (ej. calabaza criolla con grandes hojas verdes y flores amarillas, o trébol)",
  "cultivo_borde": "Cultivo de lindero o barrera perimetral en las orillas del recuadro (ej. maguey, cempasúchil, girasol, vetiver)",
  "patron_siembra": "Disposición en el terreno (ej. surcos paralelos limpios, curvas de nivel o camas biointensivas con espaciamiento exacto)",
  "suelo_textura": "Color y tipo de suelo edafológico de la región (ej. suelo rojizo arcilloso, vertisol negro o franco pedregoso con rastrojo/acolchado)",
  "manejo_hidrico": "Sistema hídrico visible (ej. mangueras de riego por goteo negro mate a lo largo de las hileras o zanjas de infiltración)",
  "delimitacion": "Bordes del recuadro de parcela (ej. senderos rectos de tierra compactada o zanjas que delimitan claramente el perímetro del lote)",
  "iluminacion": "Luz natural y ángulo de toma (ej. vista en ángulo de 45° con luz solar dorada de mañana y sombras suaves)"
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

        limpio = re.sub(r"^```(?:json)?\s*", "", contenido.strip(), flags=re.MULTILINE)
        limpio = re.sub(r"\s*```$", "", limpio.strip(), flags=re.MULTILINE)

        inicio_json = limpio.find("{")
        fin_json = limpio.rfind("}")
        if inicio_json != -1 and fin_json != -1 and fin_json > inicio_json:
            limpio = limpio[inicio_json:fin_json + 1]

        datos = json.loads(limpio)
        log_ok(f"Propiedades agrícolas de parcela para '{region}' extraídas exitosamente con LLM.", kaomoji="(^o^)")
        return datos
    except Exception as e:
        log_error(f"Fallback a conocimiento base agrícola para '{region}': {e}", kaomoji="[~_~]")
        reg_norm = region.lower()
        for k, v in CONOCIMIENTO_AGRO_BASE.items():
            if k in reg_norm:
                return v
        return CONOCIMIENTO_AGRO_BASE["mixteca"]


def generar_prompt_cultivo_terreno(
    region: str,
    base_dir: Optional[str] = None,
    guardar_en_disco: bool = True
) -> dict[str, Any]:
    """
    Función principal del mini-agente mini_prompt_cultivo:
    1. Resuelve la región jerárquica (estado, municipio).
    2. Carga datos agronómicos locales o deduce con LLM.
    3. Ensambla el prompt en Español e Inglés enfocado en un recuadro de parcela con cultivos asociados.
    4. Guarda los archivos en regiones/<estado>/<municipio>/prompt_cultivo_terreno.txt y .json.
    """
    log_mini_agente("MINI_PROMPT_CULTIVO", f"Generando prompt de parcela agrícola para: {region}", kaomoji="(^o^)/")

    if not base_dir:
        project_root = Path(__file__).resolve().parent.parent
    else:
        project_root = Path(base_dir).resolve()

    estado, municipio, ruta_relativa = parsear_region_jerarquica(region)
    datos_locales = _extraer_datos_locales_agricolas(estado, municipio, project_root)

    # Obtener propiedades agrícolas
    props = _generar_propiedades_agricolas_con_llm(region, datos_locales)

    region_nombre = props.get("region_nombre", f"{municipio.replace('_', ' ').title()}, {estado.title()}, México")
    cultivo_prin = props.get("cultivo_principal", "Maíz criollo de temporal")
    cultivo_asoc = props.get("cultivo_asociado", "Frijol trepador fijador de nitrógeno")
    cobertura = props.get("cobertura_suelo", "Calabaza rastrera con flores amarillas")
    borde = props.get("cultivo_borde", "Hileras de maguey o flores melíferas en cabeceras")
    patron = props.get("patron_siembra", "Surcos paralelos limpios y bien definidos")
    suelo = props.get("suelo_textura", "Suelo fértil con acolchado orgánico visible")
    hidrico = props.get("manejo_hidrico", "Líneas de riego por goteo negro mate a lo largo de las hileras")
    delimitacion = props.get("delimitacion", "Recuadro de parcela rectangular delimitado por senderos rectos de tierra compactada")
    iluminacion = props.get("iluminacion", "Vista en ángulo de 45° con luz solar natural de mañana y sombras suaves")

    # 1. Prompt Principal: Vista Isométrica 3D a 45° (Bloque de Parcela Aislado PNG Cutout)
    prompt_es_principal = (
        f"Render 3D fotorrealista y fotografía agronómica de estudio en ángulo isométrico a 45 grados de un "
        f"recuadro de terreno agrícola rectangular bien delimitado en {region_nombre}, presentado como un bloque o "
        f"diorama flotante aislado estilo PNG sobre fondo blanco puro de estudio sin ningún fondo exterior. "
        f"La parcela muestra un policultivo regenerativo en pleno desarrollo:\n"
        f"• Cultivo principal: {cultivo_prin}.\n"
        f"• Cultivo asociado complementario: {cultivo_asoc}.\n"
        f"• Cobertura vegetal viva del suelo: {cobertura}.\n"
        f"• Bordes perimetrales y cabeceras: {borde}.\n"
        f"• Patrón de siembra y surcos: {patron}.\n"
        f"• Textura y color del suelo: {suelo}.\n"
        f"• Sistema de riego visible: {hidrico}.\n"
        f"Separación espacial y segmentación 3D: Los surcos, las plantas individuales del cultivo principal, "
        f"las matas asociadas, los frutos y las mangueras de riego presentan un espaciamiento limpio y una separación física "
        f"moderada entre sí, con siluetas definidas y espacio libre negativo entre objetos para facilitar la segmentación "
        f"automática y reconstrucción de mallas 3D independientes sin partes fusionadas.\n"
        f"Los cuatro bordes laterales del recuadro ({delimitacion}) exhiben un corte recto y limpio de la tierra agrícola, "
        f"delimitando con precisión milimétrica el bloque en el espacio 3D. Iluminación suave de estudio fotográfico con "
        f"sombras de contacto limpias en la base, fondo blanco sólido uniforme sin horizonte, sin cielo ni paisaje exterior, "
        f"máxima fidelidad botánica, edafológica y volumétrica para modelado 3D de fincas agrícolas."
    )

    prompt_en_principal = (
        f"Photorealistic 3D asset render and agronomic studio photograph at a 45-degree isometric angle of a sharply "
        f"delimited rectangular agricultural plot in {region_nombre}, presented as a floating soil block diorama isolated "
        f"on a solid pure white background, clean PNG cutout style. The parcel displays a flourishing companion polyculture: "
        f"Primary crop: {cultivo_prin}. "
        f"Companion nitrogen-fixing crop: {cultivo_asoc}. "
        f"Living ground mulch: {cobertura}. "
        f"Perimeter buffer rows: {borde}. "
        f"Planting pattern: {patron}. "
        f"Soil edaphic texture: {suelo}. "
        f"Irrigation: {hidrico}. "
        f"3D Object Separation & Mesh Isolation: Planting rows, individual crop stalks, companion legume bunches, "
        f"fruit clusters, and irrigation lines are arranged with distinct spatial clearance and clean spacing between elements, "
        f"featuring well-defined non-overlapping contours and clear negative space around each plant asset, specifically "
        f"engineered for automated 3D mesh detection, clean instance segmentation, and neural 3D reconstruction without fused vertices. "
        f"The 4 vertical edges of the rectangular plot ({delimitacion}) feature clean, straight soil cut cross-sections "
        f"cleanly defining the parcel block in 3D space. Soft professional studio lighting with subtle contact shadows underneath, "
        f"solid pure white background, no sky, no horizon, no outdoor scenery --no background, sky, mountains, landscape, trees outside plot --ar 1:1 --v 6.1 --style raw"
    )

    # 2. Perspectiva 1: Vista Cenital / Top-Down (Planta Ortogonal a 90°)
    perspectiva_cenital_es = (
        f"Fotografía cenital ortogonal a 90 grados perpendicular directamente desde arriba de la parcela agrícola rectangular "
        f"en {region_nombre}, aislada como recorte PNG sobre fondo blanco puro de estudio. Se aprecia con nitidez milimétrica "
        f"el patrón geométrico de los surcos paralelos o curvas de nivel ({patron}), el espaciamiento regular y despejado del cultivo principal "
        f"({cultivo_prin}) intercalado con {cultivo_asoc}, el tapiz verde de cobertura ({cobertura}) entre líneas y las líneas de riego ({hidrico}). "
        f"Márgenes libres y separación clara entre hileras para escaneo topográfico y extracción de mallas 3D. "
        f"Perímetro rectangular nítido ({delimitacion}) con cortes limpios sin fondo ambiental, iluminación cenital uniforme de estudio "
        f"ideal para mapeo de texturas 2D/3D y diseño de plano agronómico."
    )
    perspectiva_cenital_en = (
        f"Top-down orthographic 90-degree zenithal photograph directly from above of the rectangular agricultural plot in {region_nombre}, "
        f"isolated as a clean PNG cutout asset on a solid pure white studio background. Geometric pattern of planting rows or contour furrows "
        f"({patron}) clearly visible, with distinct spacing and spatial clearance between individual crop stalks ({cultivo_prin}) "
        f"intercropped with {cultivo_asoc}, lush ground cover ({cobertura}), and irrigation drip lines ({hidrico}). "
        f"Clean separation between furrow rows for accurate 3D mesh boundary isolation. Sharp rectangular perimeter boundary ({delimitacion}) "
        f"with clean cut edges, flat even studio overhead lighting, no outdoor scenery --no background, sky, horizon --ar 1:1 --v 6.1 --style raw"
    )

    # 3. Perspectiva 2: Vista Frontal a Ras de Suelo / Entre Surcos (Ground-Level / Macro)
    perspectiva_ras_suelo_es = (
        f"Fotografía frontal a ras de suelo y nivel de ojo mirando por el pasillo interior entre dos surcos de cultivo en {region_nombre}, "
        f"aislada sobre fondo blanco neutro de estudio estilo PNG sin paisaje exterior. Enfoque macro hiperdetallado en el primer plano: "
        f"la textura húmeda y agregados del suelo fértil ({suelo}), las líneas de riego ({hidrico}), los brotes de {cobertura} cubriendo la tierra, "
        f"y los tallos vigorosos de {cultivo_prin} entrelazados con {cultivo_asoc} con hojas y frutos detallados. "
        f"Espacio libre en el callejón de surco con plantas despegadas entre sí para permitir detección de profundidad y mallas 3D nítidas. "
        f"Profundidad de campo fotográfica profesional con sujeto nítido y recorte perfecto hacia un fondo de estudio blanco puro sin cielo ni horizonte."
    )
    perspectiva_ras_suelo_en = (
        f"Eye-level frontal ground-level photograph looking down an interior furrow row of the agricultural plot in {region_nombre}, "
        f"isolated against a solid pure white studio background, PNG cutout style with no outdoor scenery. Macro focus on the immediate foreground: "
        f"rich moist soil crumb texture ({suelo}), precision irrigation drip lines ({hidrico}), ground mulch leaves ({cobertura}), and robust healthy "
        f"stalks of {cultivo_prin} entwined with companion {cultivo_asoc}. Clear row furrow clearance with individual plant stalks cleanly separated "
        f"for reliable depth-map estimation and independent 3D asset generation. Shallow depth of field with razor-sharp botanical textures, isolated against "
        f"a pure white void, studio softbox lighting --no background, sky, horizon --ar 16:9 --v 6.1 --style raw"
    )

    # 4. Perspectiva 3: Vista Axonométrica 3/4 con Perfil de Estratos de Suelo (Cross-Section Soil Chunk)
    perspectiva_corte_3d_es = (
        f"Render 3D axonométrico en perspectiva 3/4 mostrando un bloque volumétrico de terreno agrícola en {region_nombre} con corte "
        f"transversal vertical del suelo edafológico, aislado estilo PNG sobre fondo blanco puro. En la cara superior se aprecian los surcos "
        f"con {cultivo_prin}, {cultivo_asoc}, {cobertura} y los bordes perimetrales de {borde} dispuestos con separación ordenada. "
        f"En la cara frontal del corte vertical del bloque se observan los estratos subterráneos: la capa arable superior fértil ({suelo}), "
        f"la zona radicular densa y los canales de infiltración hídrica. Espacio y siluetas optimizadas para exportación de modelos 3D "
        f"a motores de videojuegos y software CAD sin vértices pegados. Acabado de diorama agronómico sin fondo ambiental, iluminación de estudio 3D de 3 puntos."
    )
    perspectiva_corte_3d_en = (
        f"High-end 3/4 axometric 3D render of an agricultural soil block chunk in {region_nombre} with an edaphic cross-section cut, "
        f"isolated PNG cutout asset on solid pure white background. The top surface displays flourishing crops: {cultivo_prin}, {cultivo_asoc}, "
        f"{cobertura}, and border buffers ({borde}) arranged with clean individual spacing. The cut vertical side reveals the underground root zone profile: "
        f"topsoil crumb layer ({suelo}), deep active root penetration, and moisture infiltration profile. Tailored for CAD and game engine 3D asset extraction "
        f"with distinct non-overlapping mesh geometry. Clean architectural soil chunk asset, solid white background, 3-point studio lighting with soft contact ambient occlusion --no background, sky, landscape --ar 16:9 --v 6.1 --style raw"
    )

    perspectivas = {
        "cenital_90deg": {
            "nombre": "Vista Cenital / Top-Down (Planta Ortogonal 90° de la Parcela)",
            "prompt_es": perspectiva_cenital_es,
            "prompt_en": perspectiva_cenital_en,
        },
        "ras_suelo_macro": {
            "nombre": "Vista Frontal a Ras de Suelo / Entre Surcos (Ground-Level)",
            "prompt_es": perspectiva_ras_suelo_es,
            "prompt_en": perspectiva_ras_suelo_en,
        },
        "corte_transversal_3d": {
            "nombre": "Vista Axonométrica 3/4 con Perfil de Estratos de Suelo (Cross-Section Soil Chunk)",
            "prompt_es": perspectiva_corte_3d_es,
            "prompt_en": perspectiva_corte_3d_en,
        },
    }

    resultado = {
        "region": region,
        "estado": estado,
        "municipio": municipio,
        "propiedades_extraidas": props,
        "prompt_espanol": prompt_es_principal,
        "prompt_ingles": prompt_en_principal,
        "perspectivas": perspectivas,
    }

    # Guardar en disco en la carpeta regional
    if guardar_en_disco:
        try:
            carpetas = asegurar_directorio_regional(region, str(project_root))
            region_dir = carpetas["region_dir"]

            archivo_txt_desc = region_dir / f"prompt_cultivo_terreno_{estado}_{municipio}.txt"
            archivo_txt_alias = region_dir / "prompt_cultivo_terreno.txt"

            contenido_txt = (
                f"========================================================================\n"
                f"PROMPTS DE IMAGEN: PARCELA Y RECUADRO DE CULTIVOS EN {region_nombre.upper()}\n"
                f"Generado por: AgriPoli V3 (mini_prompt_cultivo)\n"
                f"Formato: Bloque 3D / PNG Cutout Aislado en Fondo Blanco (Sin Fondo Exterior)\n"
                f"========================================================================\n\n"
                f"------------------------------------------------------------------------\n"
                f"1. PROMPT PRINCIPAL (Vista Isométrica 3D a 45° — Bloque Aislado PNG)\n"
                f"------------------------------------------------------------------------\n\n"
                f"[ESPAÑOL]\n{prompt_es_principal}\n\n"
                f"[INGLÉS (Midjourney v6.1 / Flux.1)]\n{prompt_en_principal}\n\n"
                f"------------------------------------------------------------------------\n"
                f"2. PERSPECTIVAS Y AJUSTES DE CÁMARA JUGANDO CON LA MISMA ESCENA\n"
                f"------------------------------------------------------------------------\n\n"
                f"▶ PERSPECTIVA A: {perspectivas['cenital_90deg']['nombre']}\n"
                f"[ESPAÑOL]\n{perspectiva_cenital_es}\n\n"
                f"[INGLÉS]\n{perspectiva_cenital_en}\n\n"
                f"------------------------------------------------------------------------\n"
                f"▶ PERSPECTIVA B: {perspectivas['ras_suelo_macro']['nombre']}\n"
                f"[ESPAÑOL]\n{perspectiva_ras_suelo_es}\n\n"
                f"[INGLÉS]\n{perspectiva_ras_suelo_en}\n\n"
                f"------------------------------------------------------------------------\n"
                f"▶ PERSPECTIVA C: {perspectivas['corte_transversal_3d']['nombre']}\n"
                f"[ESPAÑOL]\n{perspectiva_corte_3d_es}\n\n"
                f"[INGLÉS]\n{perspectiva_corte_3d_en}\n\n"
                f"========================================================================\n"
            )

            with open(archivo_txt_desc, "w", encoding="utf-8") as f:
                f.write(contenido_txt)
            with open(archivo_txt_alias, "w", encoding="utf-8") as f:
                f.write(contenido_txt)

            archivo_json_desc = region_dir / f"prompt_cultivo_terreno_{estado}_{municipio}.json"
            archivo_json_alias = region_dir / "prompt_cultivo_terreno.json"
            with open(archivo_json_desc, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)
            with open(archivo_json_alias, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)

            log_ok(f"Prompt de parcela guardado en: {ruta_relativa}/prompt_cultivo_terreno.txt", kaomoji="(^_^)/")
            resultado["archivo_txt"] = str(archivo_txt_desc.relative_to(project_root))
            resultado["archivo_json"] = str(archivo_json_desc.relative_to(project_root))
        except Exception as e:
            log_error(f"Error guardando archivos de prompt de cultivo: {e}", kaomoji="[X_X]")

    return resultado


if __name__ == "__main__":
    import sys
    region_test = sys.argv[1] if len(sys.argv) > 1 else "la mixteca, oaxaca"
    res = generar_prompt_cultivo_terreno(region_test)
    print("\n" + "="*70)
    print(f"PROMPT AGRÍCOLA GENERADO PARA: {res['region'].upper()}")
    print("="*70)
    print(res["prompt_espanol"])
    print("\n" + "-"*70)
    print("PROMPT EN INGLÉS (MIDJOURNEY):")
    print("-"*70)
    print(res["prompt_ingles"])
    print("="*70 + "\n")
