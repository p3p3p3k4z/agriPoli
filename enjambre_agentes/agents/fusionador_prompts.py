"""
Agente Fusionador de Prompts Agroecológicos (AgriPoli V3).

Responsabilidad:
Reconciliar y fusionar la propuesta de la Isla Polinizadora (biodiversidad nativa, dosel,
hotel de insectos, polinizadores) con la Parcela Agrícola (recuadro de terreno, policultivos,
surcos, textura de suelo y manejo hídrico) en un PROMPT MAESTRO EXTENSO Y COHESIVO.

Muestra la convivencia y sinergia viva: polinizadores pecoreando entre la isla y las flores
de los cultivos, fauna auxiliar controlando plagas en los surcos, y continuidad espacial
del terreno delimitado bajo el horizonte biogeográfico regional.
"""
from __future__ import annotations

import os
import json
import re
from pathlib import Path
from typing import Optional, Any

from config.agri_logger import log_agente, log_ok, log_info, log_error
from config.models import get_llm_para_agente
from tools.gestor_regiones import parsear_region_jerarquica, asegurar_directorio_regional
from agents.mini_prompt_isla import generar_prompt_isla_polinizadora
from agents.mini_prompt_cultivo import generar_prompt_cultivo_terreno


def fusionar_prompts_agroecologicos(
    region: str,
    base_dir: Optional[str] = None,
    guardar_en_disco: bool = True
) -> dict[str, Any]:
    """
    Orquesta la fusión de los prompts de isla polinizadora y parcela de cultivo
    en un prompt maestro de escena integral.
    """
    log_agente("FUSIONADOR_PROMPTS", f"Fusionando Isla Polinizadora + Parcela Agrícola para: {region}", kaomoji="(^o^)/")

    if not base_dir:
        project_root = Path(__file__).resolve().parent.parent
    else:
        project_root = Path(base_dir).resolve()

    estado, municipio, ruta_relativa = parsear_region_jerarquica(region)

    # 1. Obtener componentes de ambos mini-agentes
    res_isla = generar_prompt_isla_polinizadora(region, str(project_root), guardar_en_disco=guardar_en_disco)
    res_cultivo = generar_prompt_cultivo_terreno(region, str(project_root), guardar_en_disco=guardar_en_disco)

    props_isla = res_isla.get("propiedades_extraidas", {})
    props_cultivo = res_cultivo.get("propiedades_extraidas", {})

    region_nombre = props_isla.get("region_nombre") or props_cultivo.get("region_nombre", f"{municipio.title()}, {estado.title()}, México")

    # 2. Utilizar LLM para ensamblar una narrativa visual extensa y cohesionada
    llm = get_llm_para_agente("fusionador_3d")  # o fusionador_prompts

    prompt_fusion = f"""Eres el Diseñador Visual y Arquitecto Agroecológico Maestro de AgriPoli.
Tu misión es escribir un PROMPT DE IMAGEN EXTENSO, COHESIVO E HIPERREALISTA donde convivan armónicamente:
1. Una ISLA POLINIZADORA circular viva (santuario central de biodiversidad).
2. Un RECUADRO DE TERRENO AGRÍCOLA delimitado (parcela productiva circundante).

IMPORTANTE - FORMATO, AISLAMIENTO Y SEPARACIÓN PARA CONVERSIÓN A 3D:
- El modelo debe presentarse como un gran DIORAMA AGROECOLÓGICO FLOTANTE o BLOQUE 3D recortado estilo PNG sobre fondo blanco puro de estudio.
- NO DEBE CONTENER horizonte, cielo, montañas ni paisaje exterior. Solo el bloque de cultivo y la isla perfectamente recortados con bordes limpios en el espacio.
- SEPARACIÓN ESPACIAL PARA CONVERSIÓN A 3D: Cada elemento (árboles del dosel, arbustos, flores, hotel de insectos, surcos de cultivo, plantas individuales y polinizadores en vuelo) debe mostrarse con una separación física moderada y siluetas independientes bien definidas, evitando amontonamientos o sobreposiciones confusas, de modo que los algoritmos de detección de objetos y mallas 3D (image-to-3D) puedan segmentar y reconstruir cada objeto por separado sin crear mallas fundidas.
- Debe apreciarse la interacción viva y sinergia: abejas y polinizadores saliendo del corazón de la isla hacia las flores de los cultivos agrícolas, y fauna auxiliar patrullando los surcos.

Región objetivo: "{region_nombre}".

--- DATOS DE LA ISLA POLINIZADORA CENTRAL ---
- Dosel arbóreo: {props_isla.get('dosel', '')}
- Sotobosque floral: {props_isla.get('sotobosque', '')}
- Cobertura de suelo: {props_isla.get('cobertura', '')}
- Polinizadores activos: {props_isla.get('polinizadores', '')}
- Insectos benéficos auxiliares: {props_isla.get('insectos_auxiliares', '')}
- Infraestructura ecológica: {props_isla.get('infraestructura', '')}

--- DATOS DE LA PARCELA AGRÍCOLA CIRCUNDANTE ---
- Cultivo principal: {props_cultivo.get('cultivo_principal', '')}
- Cultivo asociado complementario: {props_cultivo.get('cultivo_asociado', '')}
- Cobertura vegetal viva: {props_cultivo.get('cobertura_suelo', '')}
- Bordes de lindero: {props_cultivo.get('cultivo_borde', '')}
- Patrón de siembra y surcos: {props_cultivo.get('patron_siembra', '')}
- Suelo edafológico: {props_cultivo.get('suelo_textura', '')}
- Manejo hídrico: {props_cultivo.get('manejo_hidrico', '')}
- Delimitación perimetral: {props_cultivo.get('delimitacion', '')}

Debes responder ÚNICAMENTE con un objeto JSON con dos claves:
{{
  "prompt_espanol_extenso": "Texto del prompt principal en español, extenso, describiendo el diorama completo aislado en fondo blanco de estudio sin horizonte, con elementos ligeramente separados para segmentación 3D precisa, listo para DALL-E 3.",
  "prompt_ingles_extenso": "Texto del prompt principal en inglés con descriptores de 3D diorama asset render, isolated on pure white background, PNG cutout style, distinct spatial separation between assets for image-to-3D mesh reconstruction, --no background, sky, mountains --ar 16:9 --v 6.1 --style raw"
}}
"""
    prompt_es_extenso = ""
    prompt_en_extenso = ""

    try:
        respuesta = llm.invoke(prompt_fusion)
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

        datos_json = json.loads(limpio)
        prompt_es_extenso = datos_json.get("prompt_espanol_extenso", "")
        prompt_en_extenso = datos_json.get("prompt_ingles_extenso", "")
        log_ok("Prompt maestro agroecológico fusionado exitosamente con LLM.", kaomoji="(^w^)")
    except Exception as e:
        log_error(f"Fallback de ensamblado directo para prompt maestro: {e}", kaomoji="[~_~]")

    # Asegurar prompts principales robustos si el LLM no respondió completo
    if not prompt_es_extenso or len(prompt_es_extenso) < 100:
        prompt_es_extenso = (
            f"Render 3D fotorrealista y fotografía de estudio en ángulo isométrico a 45 grados de un gran diorama agroecológico "
            f"flotante en {region_nombre}, presentado como un bloque de terreno agrícola rectangular aislado estilo PNG sobre "
            f"fondo blanco puro de estudio sin ningún fondo exterior. En el centro exacto del bloque se sitúa una vibrante "
            f"Isla Polinizadora circular viva: dosel de {props_isla.get('dosel', '')}, sotobosque floral de {props_isla.get('sotobosque', '')}, "
            f"tapete de cobertura de {props_isla.get('cobertura', '')} e infraestructura ecológica ({props_isla.get('infraestructura', '')}). "
            f"Rodeando armoniosamente la isla circular se extienden las parcelas agrícolas cultivadas en {props_cultivo.get('patron_siembra', '')} "
            f"con {props_cultivo.get('cultivo_principal', '')} asociado con {props_cultivo.get('cultivo_asociado', '')}, cobertura viva de {props_cultivo.get('cobertura_suelo', '')}, "
            f"y bordes perimetrales de {props_cultivo.get('cultivo_borde', '')}.\n"
            f"Separación espacial y segmentación 3D: Los componentes del santuario (árboles, arbustos, flores, bebedero) y los cultivos "
            f"circundantes están distribuidos con una separación física moderada y márgenes limpios entre sí, con siluetas despegadas "
            f"y contornos individuales definidos sin apiñamientos densos, permitiendo que los algoritmos de escaneo e image-to-3D detecten y generen mallas 3D separadas de cada objeto con total nitidez.\n"
            f"Se observa una intensa sinergia biológica en pleno vuelo: {props_isla.get('polinizadores', '')} transitando con trayectorias despejadas desde el santuario hacia las flores de los cultivos, y "
            f"{props_isla.get('insectos_auxiliares', '')} patrullando el follaje. Textura edafológica fértil ({props_cultivo.get('suelo_textura', '')}) "
            f"con {props_cultivo.get('manejo_hidrico', '')}. Bordes laterales rectos ({props_cultivo.get('delimitacion', '')}) cortados con precisión limpia. "
            f"Iluminación suave de estudio fotográfico con sombra de contacto inferior, fondo blanco puro sólido sin cielo, sin horizonte ni paisaje exterior."
        )

    if not prompt_en_extenso or len(prompt_en_extenso) < 100:
        prompt_en_extenso = (
            f"Photorealistic 3D asset render and studio photograph at a 45-degree isometric angle of a holistic agroecological "
            f"floating diorama in {region_nombre}, presented as an isolated rectangular agricultural plot block on a solid pure "
            f"white background, clean PNG cutout style. At the core of the block sits a thriving circular Pollinator Island sanctuary: "
            f"native canopy of {props_isla.get('dosel', '')}, flowering understory of {props_isla.get('sotobosque', '')}, ground cover of "
            f"{props_isla.get('cobertura', '')}, and {props_isla.get('infraestructura', '')}. Encircling the circular island organically "
            f"are the agricultural crop rows ({props_cultivo.get('patron_siembra', '')}) featuring {props_cultivo.get('cultivo_principal', '')} "
            f"intercropped with {props_cultivo.get('cultivo_asociado', '')}, living soil cover ({props_cultivo.get('cobertura_suelo', '')}), "
            f"and perimeter buffer edges ({props_cultivo.get('cultivo_borde', '')}).\n"
            f"3D Object Separation & Mesh Isolation: Individual sanctuary trees, flowering shrubs, crop stalks, companion legumes, "
            f"ecological infrastructure, and hovering pollinators are arranged with distinct spatial clearance and clean spacing between assets, "
            f"exhibiting crisp non-overlapping contours and clear negative space specifically engineered for automated multi-object 3D mesh detection and neural reconstruction without fused meshes.\n"
            f"Active biological symbiosis in flight: {props_isla.get('polinizadores', '')} foraging along clear flight paths between island blossoms and companion crop flowers, while {props_isla.get('insectos_auxiliares', '')} patrol stems. "
            f"Rich edaphic soil texture ({props_cultivo.get('suelo_textura', '')}) with irrigation ({props_cultivo.get('manejo_hidrico', '')}). "
            f"Crisp straight boundary edges ({props_cultivo.get('delimitacion', '')}) cleanly cut in 3D space. Soft studio lighting casting subtle "
            f"contact shadows underneath, solid pure white background void, no background scenery, no sky, no horizon --no background, sky, mountains, landscape --ar 16:9 --v 6.1 --style raw"
        )

    # 3 Perspectivas de Ajuste del Prompt Maestro
    # A. Cenital 90° Top-Down
    persp_cenital_es = (
        f"Fotografía cenital ortogonal a 90 grados perpendicular directa desde arriba del diorama agroecológico maestro de {region_nombre}, "
        f"aislado estilo PNG sobre fondo blanco puro de estudio. Se aprecia con precisión de plano arquitectónico la relación concéntrica y el espaciado ordenado: "
        f"en el centro la Isla Polinizadora circular ({props_isla.get('dosel', '')}, {props_isla.get('sotobosque', '')}, {props_isla.get('cobertura', '')}), "
        f"rodeada por los cuadrantes de cultivo en surcos ({props_cultivo.get('cultivo_principal', '')} y {props_cultivo.get('cultivo_asociado', '')}) con pasillos libres entre hileras, "
        f"y los senderos perimetrales limpios ({props_cultivo.get('delimitacion', '')}). Márgenes nítidos entre objetos para segmentación cartográfica 3D. "
        f"Fondo blanco sólido sin paisaje ambiental, iluminación cenital uniforme."
    )
    persp_cenital_en = (
        f"Top-down orthographic 90-degree zenithal photograph directly from above of the master agroecological diorama in {region_nombre}, "
        f"isolated as a clean PNG cutout asset on a solid pure white studio background. Architectural layout clearly showing the concentric circular "
        f"pollinator sanctuary at the core surrounded by symmetrical crop quadrants ({props_cultivo.get('cultivo_principal', '')} and {props_cultivo.get('cultivo_asociado', '')}) "
        f"with distinct spatial clearance between rows and plant clusters, and crisp perimeter paths ({props_cultivo.get('delimitacion', '')}). "
        f"Clean negative space tailored for 3D layout segmentation. Completely isolated on solid white void, flat even overhead lighting, no outdoor scenery --no background, sky, horizon --ar 1:1 --v 6.1 --style raw"
    )

    # B. Ras de Suelo / Transición Ecológica en Acción
    persp_suelo_es = (
        f"Fotografía frontal a ras de suelo y nivel de ojo capturando la zona de transición donde termina el borde de la Isla Polinizadora "
        f"circular y comienzan los surcos de cultivo en {region_nombre}, aislada sobre fondo blanco de estudio estilo PNG sin paisaje exterior. "
        f"En primer plano hipernítido se observan abejas y colibríes ({props_isla.get('polinizadores', '')}) cruzando en vuelo directo entre "
        f"las flores de la isla ({props_isla.get('cobertura', '')}) y las flores de {props_cultivo.get('cultivo_principal', '')}, con siluetas despegadas "
        f"y espacio libre entre tallos para permitir la detección precisa de profundidad e individualización de mallas 3D. "
        f"Textura de tierra húmeda y mantillo orgánico en la base, iluminación de estudio suave con recorte perfecto hacia fondo blanco."
    )
    persp_suelo_en = (
        f"Eye-level frontal ground-level photograph capturing the ecological transition threshold between the circular Pollinator Island edge "
        f"and the agricultural crop rows in {region_nombre}, isolated against a solid pure white studio background, clean PNG cutout style with no outdoor scenery. "
        f"Foreground focus captures native pollinators ({props_isla.get('polinizadores', '')}) in active flight transitioning between island blossoms "
        f"and companion crop flowers ({props_cultivo.get('cultivo_principal', '')}), showing clean clearance and non-overlapping silhouettes between stems for reliable 3D depth-mesh extraction. "
        f"Crisp botanical textures, shallow depth of field isolated against white void, soft studio lighting --no background, sky, horizon --ar 16:9 --v 6.1 --style raw"
    )

    # C. Axonométrica 3/4 en Corte Transversal de Terreno
    persp_corte_es = (
        f"Render 3D axonométrico en perspectiva 3/4 de un gran bloque de terreno agroecológico en {region_nombre} con corte transversal vertical "
        f"del suelo, aislado estilo PNG sobre fondo blanco puro. En la superficie se visualiza la integración de la Isla Polinizadora circular dentro "
        f"de los surcos de cultivo ({props_cultivo.get('cultivo_principal', '')} y {props_cultivo.get('cultivo_asociado', '')}) con elementos botánicos separados y definidos individualmente. "
        f"En las caras laterales cortadas del bloque se aprecian los estratos del perfil del suelo edafológico ({props_cultivo.get('suelo_textura', '')}), raíces profundas y líneas de infiltración hídrica. "
        f"Optimizado para software CAD y motores 3D sin mallas pegadas, sin fondo ambiental, iluminación de estudio 3D de 3 puntos."
    )
    persp_corte_en = (
        f"High-end 3/4 axometric 3D cross-section render of an integrated agroecological farm block in {region_nombre}, isolated PNG cutout asset on "
        f"solid pure white background. The top surface displays the circular Pollinator Island integrated into the surrounding crop rows "
        f"({props_cultivo.get('cultivo_principal', '')} and {props_cultivo.get('cultivo_asociado', '')}) with distinctly separated botanical assets. "
        f"The cut vertical faces reveal the subterranean soil profile ({props_cultivo.get('suelo_textura', '')}), deep root development, and water infiltration pathways. "
        f"Geometrically optimized for CAD/game-engine 3D mesh reconstruction with non-overlapping boundaries. Clean architectural farm block diorama, "
        f"3-point studio lighting with soft contact ambient occlusion, no background scenery --no background, sky, mountains --ar 16:9 --v 6.1 --style raw"
    )

    perspectivas_maestro = {
        "cenital_90deg": {
            "nombre": "Vista Cenital / Top-Down (Plano Maestro Ortogonal 90°)",
            "prompt_es": persp_cenital_es,
            "prompt_en": persp_cenital_en,
        },
        "ras_suelo_transicion": {
            "nombre": "Vista Frontal a Ras de Suelo / Transición Ecológica en Acción",
            "prompt_es": persp_suelo_es,
            "prompt_en": persp_suelo_en,
        },
        "corte_transversal_3d": {
            "nombre": "Vista Axonométrica 3/4 en Corte Transversal de Terreno (Cross-Section Diorama)",
            "prompt_es": persp_corte_es,
            "prompt_en": persp_corte_en,
        },
    }

    resultado = {
        "region": region,
        "estado": estado,
        "municipio": municipio,
        "prompt_espanol_extenso": prompt_es_extenso,
        "prompt_ingles_extenso": prompt_en_extenso,
        "perspectivas": perspectivas_maestro,
        "componentes_isla": props_isla,
        "componentes_cultivo": props_cultivo,
    }

    # Guardar en disco en la carpeta regional
    if guardar_en_disco:
        try:
            carpetas = asegurar_directorio_regional(region, str(project_root))
            region_dir = carpetas["region_dir"]

            archivo_txt_desc = region_dir / f"prompt_agroecologico_maestro_{estado}_{municipio}.txt"
            archivo_txt_alias = region_dir / "prompt_agroecologico_maestro.txt"

            contenido_txt = (
                f"========================================================================\n"
                f"PROMPTS DE IMAGEN: ESCENA MAESTRA AGROECOLÓGICA EN {region_nombre.upper()}\n"
                f"Isla Polinizadora Circular + Parcela Agrícola en Convivencia Viva\n"
                f"Generado por: AgriPoli V3 (fusionador_prompts)\n"
                f"Formato: Gran Diorama 3D / PNG Cutout Aislado en Fondo Blanco (Sin Fondo Exterior)\n"
                f"========================================================================\n\n"
                f"------------------------------------------------------------------------\n"
                f"1. PROMPT PRINCIPAL (Gran Diorama Agroecológico 3D a 45° — Aislado PNG)\n"
                f"------------------------------------------------------------------------\n\n"
                f"[ESPAÑOL EXTENSO]\n{prompt_es_extenso}\n\n"
                f"[INGLÉS EXTENSO (Midjourney v6.1 / Flux.1)]\n{prompt_en_extenso}\n\n"
                f"------------------------------------------------------------------------\n"
                f"2. PERSPECTIVAS Y AJUSTES DE CÁMARA JUGANDO CON LA MISMA ESCENA\n"
                f"------------------------------------------------------------------------\n\n"
                f"▶ PERSPECTIVA A: {perspectivas_maestro['cenital_90deg']['nombre']}\n"
                f"[ESPAÑOL]\n{persp_cenital_es}\n\n"
                f"[INGLÉS]\n{persp_cenital_en}\n\n"
                f"------------------------------------------------------------------------\n"
                f"▶ PERSPECTIVA B: {perspectivas_maestro['ras_suelo_transicion']['nombre']}\n"
                f"[ESPAÑOL]\n{persp_suelo_es}\n\n"
                f"[INGLÉS]\n{persp_suelo_en}\n\n"
                f"------------------------------------------------------------------------\n"
                f"▶ PERSPECTIVA C: {perspectivas_maestro['corte_transversal_3d']['nombre']}\n"
                f"[ESPAÑOL]\n{persp_corte_es}\n\n"
                f"[INGLÉS]\n{persp_corte_en}\n\n"
                f"========================================================================\n"
            )

            with open(archivo_txt_desc, "w", encoding="utf-8") as f:
                f.write(contenido_txt)
            with open(archivo_txt_alias, "w", encoding="utf-8") as f:
                f.write(contenido_txt)

            archivo_json_desc = region_dir / f"prompt_agroecologico_maestro_{estado}_{municipio}.json"
            archivo_json_alias = region_dir / "prompt_agroecologico_maestro.json"
            with open(archivo_json_desc, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)
            with open(archivo_json_alias, "w", encoding="utf-8") as f:
                json.dump(resultado, f, ensure_ascii=False, indent=2)

            log_ok(f"Prompt maestro guardado en: {ruta_relativa}/prompt_agroecologico_maestro.txt", kaomoji="(^_^)/")
            resultado["archivo_txt"] = str(archivo_txt_desc.relative_to(project_root))
            resultado["archivo_json"] = str(archivo_json_desc.relative_to(project_root))
        except Exception as e:
            log_error(f"Error guardando prompt maestro fusionado: {e}", kaomoji="[X_X]")

    return resultado


if __name__ == "__main__":
    import sys
    region_test = sys.argv[1] if len(sys.argv) > 1 else "la mixteca, oaxaca"
    res = fusionar_prompts_agroecologicos(region_test)
    print("\n" + "="*75)
    print(f"PROMPT MAESTRO FUSIONADO: {res['region'].upper()}")
    print("="*75)
    print(res["prompt_espanol_extenso"])
    print("\n" + "-"*75)
    print("PROMPT MAESTRO EN INGLÉS (MIDJOURNEY / FLUX):")
    print("-"*75)
    print(res["prompt_ingles_extenso"])
    print("="*75 + "\n")
