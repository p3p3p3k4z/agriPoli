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

    # 1. Prompt Principal: Vista Isométrica 3D a 45° (Diorama Aislado PNG Cutout)
    prompt_es_principal = (
        f"Render 3D fotorrealista y fotografía de estudio en ángulo isométrico a 45 grados de una Isla Polinizadora "
        f"circular en {region_nombre}, presentada como un asset de diorama flotante recortado estilo PNG sobre fondo blanco puro "
        f"de estudio sin ningún fondo ambiental. La isla circular muestra su estratificación botánica completa:\n"
        f"• Dosel de árboles medianos: {dosel}, con hojas verdes y flores visibles.\n"
        f"• Sotobosque floral: arbustos y flores ({sotobosque}) con colores vivos y texturas naturales.\n"
        f"• Cobertura del suelo: {cobertura}, con flores densamente visibles.\n"
        f"• Polinizadores en acción: {polinizadores} volando y posándose activamente sobre flores.\n"
        f"• Insectos auxiliares: {insectos_aux} visibles en el follaje.\n"
        f"• Infraestructura ecológica integrada: {infraestructura}.\n"
        f"Separación espacial y segmentación 3D: Los árboles, arbustos, flores, bebedero, hotel de insectos y polinizadores "
        f"están dispuestos con una separación física moderada y márgenes limpios entre sí, con siluetas bien definidas y sin "
        f"sobreposiciones densas o marañas confusas, permitiendo una detección y extracción precisa de objetos y mallas 3D individuales.\n"
        f"El perímetro circular de suelo fértil y piedras delimitadoras está perfectamente definido y recortado con bordes nítidos. "
        f"Iluminación suave de estudio fotográfico con sutil sombra de contacto debajo de la base, fondo blanco sólido uniforme sin cielo, "
        f"sin horizonte ni paisaje exterior, máxima fidelidad botánica y volumétrica para modelado 3D de assets independientes."
    )

    prompt_en_principal = (
        f"Photorealistic 3D asset render and studio photograph at a 45-degree isometric angle of a lush circular "
        f"Pollinator Island in {region_nombre}, presented as a floating diorama asset isolated on a solid pure white background, "
        f"clean PNG cutout style. The circular sanctuary displays complete botanical stratification: "
        f"Medium tree canopy with {dosel} with lush foliage and blooming flowers. "
        f"Understory filled with flowering shrubs ({sotobosque}) with vibrant natural colors and rich leaf textures. "
        f"Ground cover carpeted with blooming {cobertura}. "
        f"Active pollinators in flight and perching: {polinizadores}. "
        f"Beneficial biocontrol insects: {insectos_aux}. "
        f"Integrated ecological infrastructure: {infraestructura}. "
        f"3D Object Separation & Mesh Isolation: Individual trees, shrubs, flower patches, insect hotel, waterer, and hovering pollinators "
        f"are arranged with distinct spatial clearance and clean spacing between elements, showing well-defined non-overlapping silhouettes "
        f"and clear negative space around each asset, specifically optimized for automated image-to-3D mesh reconstruction and semantic object detection. "
        f"Crisp circular boundary of fertile organic soil and natural edging stones cleanly cut in 3D space. "
        f"Soft diffused studio lighting with subtle contact shadow underneath, completely isolated on pure white void, "
        f"no background scenery, no sky, no landscape, extreme botanical fidelity --no background, sky, mountains, landscape, trees outside island --ar 1:1 --v 6.1 --style raw"
    )

    # 2. Perspectiva 1: Vista Cenital / Top-Down (Planta Ortogonal a 90°)
    perspectiva_cenital_es = (
        f"Fotografía cenital ortogonal a 90 grados perpendicular directamente desde arriba de la Isla Polinizadora circular "
        f"de {region_nombre}, aislada como un asset recortado estilo PNG sobre fondo blanco puro de estudio. "
        f"Se aprecia con claridad milimétrica la geometría concéntrica del santuario con elementos ligeramente separados y organizados: "
        f"en el núcleo el dosel de {dosel}, rodeado en círculo por el sotobosque ({sotobosque}), la alfombra floral de cobertura ({cobertura}), "
        f"los bebederos y hotel de insectos ({infraestructura}), con abejas y mariposas ({polinizadores}) capturadas en vuelo con siluetas despegadas sobre las flores. "
        f"Espaciado limpio entre copas y plantas para detección de instancias 3D. Borde circular perfecto y limpio sin fondo ambiental, "
        f"iluminación cenital uniforme de estudio para plano botánico y texturizado 2D/3D."
    )
    perspectiva_cenital_en = (
        f"Top-down orthographic 90-degree zenithal photograph directly from above of the circular Pollinator Island in {region_nombre}, "
        f"isolated as a clean PNG cutout asset on a solid pure white studio background. Concentric circular layout with clear spatial clearance "
        f"between elements: tree canopy of {dosel} at the center, surrounded by flowering understory ({sotobosque}), carpeted ground cover ({cobertura}), "
        f"integrated {infraestructura}, and active pollinators ({polinizadores}) hovering with distinct separation above blossoms. "
        f"Clean negative space between individual foliage clusters for 3D instance segmentation. Perfectly sharp circular boundary, "
        f"flat even overhead studio illumination, no outdoor scenery --no background, sky, horizon --ar 1:1 --v 6.1 --style raw"
    )

    # 3. Perspectiva 2: Vista Frontal a Ras de Suelo / Nivel de Ojo (Ground-Level / Macro)
    perspectiva_ras_suelo_es = (
        f"Fotografía frontal a ras de suelo y nivel de ojo de la Isla Polinizadora en {region_nombre}, recortada sobre fondo blanco "
        f"neutro de estudio estilo PNG sin paisaje exterior. Enfoque macro hiperdetallado en el primer plano: la base de tierra fértil, "
        f"pétalos y hojas de {cobertura}, tallos de {sotobosque} y abejas nativas ({polinizadores}) pecoreando a milímetros de la cámara. "
        f"Hacia el plano medio se elevan los árboles de {dosel} y se distingue el hotel de insectos de {infraestructura}. "
        f"Siluetas de insectos y flores despegadas del fondo y con separación limpia entre ramas para segmentación de profundidad y mallas 3D. "
        f"Profundidad de campo fotográfica profesional con sujeto nítido y recorte perfecto hacia fondo blanco puro de estudio."
    )
    perspectiva_ras_suelo_en = (
        f"Eye-level frontal ground-level macro photograph of the Pollinator Island in {region_nombre}, isolated against a solid "
        f"pure white studio background, clean PNG cutout aesthetic with no outdoor background. Sharp focus on the immediate foreground: "
        f"rich soil bed, vibrant petals of {cobertura}, flowering stems of {sotobosque}, and active native pollinators ({polinizadores}) "
        f"foraging closely. Rising in midground is the canopy of {dosel} and insect hotel of {infraestructura}. "
        f"Clean separation and uncluttered spacing between foreground petals and flying insects for accurate depth map and 3D mesh isolation. "
        f"Shallow depth of field with razor-sharp macro botanical details, pure white background void, studio softbox lighting --no background, sky, horizon --ar 16:9 --v 6.1 --style raw"
    )

    # 4. Perspectiva 3: Vista Axonométrica 3/4 en Corte Transversal (Cross-Section Diorama 3D)
    perspectiva_corte_3d_es = (
        f"Render 3D de alta gama en perspectiva axonométrica 3/4 con corte transversal vertical del sustrato de la Isla Polinizadora "
        f"en {region_nombre}, aislado estilo PNG sobre fondo blanco puro. El modelo tipo diorama exhibe la vegetación superficial "
        f"({dosel}, {sotobosque}, {cobertura}, {polinizadores} y {infraestructura}) dispuesta con separación limpia de siluetas, "
        f"y una rebanada vertical limpia del perfil de suelo circular: capa de humus, tierra vegetal fértil y raíces vivas bien ramificadas. "
        f"Espacio y definición geométrica optimizados para reconstrucción de mallas 3D independientes sin mallas fundidas. "
        f"Acabado de concept art agronómico y asset para motor 3D, sin fondo ambiental, iluminación de estudio de 3 puntos con sutil oclusión ambiental en la base."
    )
    perspectiva_corte_3d_en = (
        f"High-end 3D cross-section diorama render from a 3/4 axometric perspective of the circular Pollinator Island in {region_nombre}, "
        f"isolated PNG cutout asset on a solid pure white background. The 3D model showcases both surface biodiversity "
        f"({dosel}, {sotobosque}, {cobertura}, active pollinators, and {infraestructura}) arranged with clean individual spacing, "
        f"and a clean vertical slice cut of the circular soil profile: organic mulch layer, dark crumb topsoil, and visible healthy root systems. "
        f"Clear object contours and spatial separation tailored for multi-object 3D mesh extraction and neural reconstruction without fused vertices. "
        f"Concept art diorama asset style, no environmental background, studio 3-point lighting with soft contact ambient occlusion --no background, sky, horizon --ar 16:9 --v 6.1 --style raw"
    )

    perspectivas = {
        "cenital_90deg": {
            "nombre": "Vista Cenital / Top-Down (Planta Ortogonal 90°)",
            "prompt_es": perspectiva_cenital_es,
            "prompt_en": perspectiva_cenital_en,
        },
        "ras_suelo_macro": {
            "nombre": "Vista Frontal a Ras de Suelo / Nivel de Ojo (Ground-Level)",
            "prompt_es": perspectiva_ras_suelo_es,
            "prompt_en": perspectiva_ras_suelo_en,
        },
        "corte_transversal_3d": {
            "nombre": "Vista Axonométrica 3/4 en Corte Transversal (Cross-Section Diorama)",
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

    # Guardar en disco en la carpeta regional correspondiente
    if guardar_en_disco:
        try:
            carpetas = asegurar_directorio_regional(region, str(project_root))
            region_dir = carpetas["region_dir"]
            
            # 1. Guardar archivo de texto plano con los prompts y perspectivas
            archivo_txt_desc = region_dir / f"prompt_isla_polinizadora_{estado}_{municipio}.txt"
            archivo_txt_alias = region_dir / "prompt_isla_polinizadora.txt"
            
            contenido_txt = (
                f"========================================================================\n"
                f"PROMPTS DE IMAGEN: ISLA POLINIZADORA EN {region_nombre.upper()}\n"
                f"Generado por: AgriPoli V3 (mini_prompt_isla)\n"
                f"Formato: Asset 3D / PNG Cutout Aislado en Fondo Blanco (Sin Fondo Exterior)\n"
                f"========================================================================\n\n"
                f"------------------------------------------------------------------------\n"
                f"1. PROMPT PRINCIPAL (Vista Isométrica 3D a 45° — Diorama Aislado PNG)\n"
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

