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
1. Una ISLA POLINIZADORA circular (santuario de biodiversidad).
2. Un RECUADRO DE TERRENO AGRÍCOLA (parcela productiva delimitada).

Región objetivo: "{region_nombre}".

--- DATOS DE LA ISLA POLINIZADORA ---
- Dosel arbóreo: {props_isla.get('dosel', '')}
- Sotobosque floral: {props_isla.get('sotobosque', '')}
- Cobertura de suelo: {props_isla.get('cobertura', '')}
- Polinizadores activos: {props_isla.get('polinizadores', '')}
- Insectos benéficos auxiliares: {props_isla.get('insectos_auxiliares', '')}
- Infraestructura ecológica: {props_isla.get('infraestructura', '')}

--- DATOS DE LA PARCELA AGRÍCOLA ---
- Cultivo principal: {props_cultivo.get('cultivo_principal', '')}
- Cultivo asociado complementario: {props_cultivo.get('cultivo_asociado', '')}
- Cobertura vegetal viva: {props_cultivo.get('cobertura_suelo', '')}
- Bordes de lindero: {props_cultivo.get('cultivo_borde', '')}
- Patrón de siembra y surcos: {props_cultivo.get('patron_siembra', '')}
- Suelo edafológico: {props_cultivo.get('suelo_textura', '')}
- Manejo hídrico: {props_cultivo.get('manejo_hidrico', '')}
- Delimitación perimetral: {props_cultivo.get('delimitacion', '')}

--- HORIZONTE Y LUZ ---
{props_isla.get('horizonte', '')} | {props_cultivo.get('iluminacion', '')}

INSTRUCCIONES DE DISEÑO VISUAL:
- La composición debe mostrar un recuadro de parcela agrícola completo y bien delimitado, que alberga en su centro neurálgico la Isla Polinizadora circular viva.
- Debe apreciarse la interacción viva y sinergia: las abejas y polinizadores saliendo de la isla hacia las flores de los cultivos agrícolas circundantes, y las mariquitas/crisopas patrullando los surcos.
- Los surcos y camas de cultivo rodean orgánicamente la isla polinizadora, interconectados por senderos limpios de tierra compactada.
- Debe redactarse de forma descriptiva, hiperrealista, fotográfica, sin elementos fantásticos ni texto flotante.

Debes responder ÚNICAMENTE con un objeto JSON con dos claves:
{{
  "prompt_espanol_extenso": "Texto del prompt completo en español, muy detallado y estructurado por párrafos o secciones temáticas, listo para DALL-E 3 o concept art.",
  "prompt_ingles_extenso": "Texto del prompt completo en inglés optimizado con descriptores fotográficos cinematográficos, relación de aspecto --ar 16:9 --v 6.1 listo para Midjourney v6 o Flux.1."
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
        # Ensamblado determinista si el LLM falla
        prompt_es_extenso = (
            f"Fotografía panorámica aérea y perspectiva en ángulo de 45 grados de un paisaje agroecológico de precisión "
            f"en {region_nombre}. En el centro de un recuadro de terreno agrícola perfectamente delimitado, se ubica una "
            f"vibrante Isla Polinizadora circular de conservación biológica, rodeada armónicamente por cuatro sectores de cultivo.\n\n"
            f"1. NÚCLEO ECOLÓGICO (Isla Polinizadora Circular):\n"
            f"La isla circular destaca con su estratificación vegetal completa: un dosel de árboles medianos ({props_isla.get('dosel', '')}), "
            f"un denso sotobosque floral ({props_isla.get('sotobosque', '')}) y una alfombra vegetal de cobertura ({props_isla.get('cobertura', '')}). "
            f"En su interior se aprecia infraestructura ecológica integrada: {props_isla.get('infraestructura', '')}.\n\n"
            f"2. PARCELA AGRÍCOLA CIRCUNDANTE (Recuadro Productivo):\n"
            f"Rodeando el santuario circular se despliegan cuatro parcelas cultivadas en surcos limpios ({props_cultivo.get('patron_siembra', '')}) "
            f"con {props_cultivo.get('cultivo_principal', '')} asociado con {props_cultivo.get('cultivo_asociado', '')} y cobertura viva de {props_cultivo.get('cobertura_suelo', '')}. "
            f"En las orillas y cabeceras del terreno destacan barreras perimetrales de {props_cultivo.get('cultivo_borde', '')}.\n\n"
            f"3. SINERGIA BIOLÓGICA Y EDÁFICA EN ACCIÓN:\n"
            f"Se observan en pleno vuelo y pecoreo {props_isla.get('polinizadores', '')}, transitando activamente entre el corazón de la isla "
            f"y las flores abiertas de los cultivos agrícolas. En las hojas de los surcos se aprecian {props_isla.get('insectos_auxiliares', '')} "
            f"actuando como control biológico natural. El suelo muestra su textura y color característico ({props_cultivo.get('suelo_textura', '')}) "
            f"con {props_cultivo.get('manejo_hidrico', '')}.\n\n"
            f"4. DELIMITACIÓN Y HORIZONTE:\n"
            f"{props_cultivo.get('delimitacion', '')}. Al fondo se contempla {props_isla.get('horizonte', '')}, bañado por {props_cultivo.get('iluminacion', '')}. "
            f"Fotografía agronómica profesional hiperrealista de alta resolución, nitidez botánica absoluta, sin elementos fantásticos, "
            f"lista como referencia integral para modelado 3D de fincas regenerativas."
        )

        prompt_en_extenso = (
            f"Hyperrealistic wide-angle elevated 45-degree aerial photograph of a holistic regenerative agroecological farm "
            f"in {region_nombre}. At the core of a sharply defined rectangular crop plot rests a vibrant circular Pollinator Island "
            f"surrounded by organized agricultural sectors in active symbiosis.\n\n"
            f"The circular pollinator sanctuary features a rich multi-layered native canopy ({props_isla.get('dosel', '')}), "
            f"understory shrubs ({props_isla.get('sotobosque', '')}), and flowering ground cover ({props_isla.get('cobertura', '')}), "
            f"equipped with {props_isla.get('infraestructura', '')}.\n\n"
            f"Flanking the sanctuary are the four agricultural companion quadrants with {props_cultivo.get('cultivo_principal', '')} "
            f"intercropped with {props_cultivo.get('cultivo_asociado', '')} along {props_cultivo.get('patron_siembra', '')} "
            f"on {props_cultivo.get('suelo_textura', '')} with {props_cultivo.get('manejo_hidrico', '')}.\n\n"
            f"Visible ecological synergy: {props_isla.get('polinizadores', '')} flying between the wild sanctuary and the blooming crop furrows, "
            f"with beneficial insects ({props_isla.get('insectos_auxiliares', '')}) patrolling leaves. Clean earthen border paths "
            f"({props_cultivo.get('delimitacion', '')}). Background landscape: {props_isla.get('horizonte', '')} under natural daylight, "
            f"sharp depth of field, 8k resolution, cinematic lighting, ready as a 3D terrain and farm simulation concept --ar 16:9 --v 6.1"
        )

    resultado = {
        "region": region,
        "estado": estado,
        "municipio": municipio,
        "prompt_espanol_extenso": prompt_es_extenso,
        "prompt_ingles_extenso": prompt_en_extenso,
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
                f"PROMPT MAESTRO AGROECOLÓGICO: ISLA POLINIZADORA + PARCELA DE CULTIVOS\n"
                f"Región: {region_nombre.upper()}\n"
                f"Generado por: AgriPoli V3 (Agente Fusionador de Prompts)\n"
                f"========================================================================\n\n"
                f"--- [OPCIÓN 1: PROMPT EN ESPAÑOL EXTENSO (DALL-E 3 / BING / CONCEPT ART)] ---\n\n"
                f"{prompt_es_extenso}\n\n"
                f"------------------------------------------------------------------------\n"
                f"--- [OPCIÓN 2: PROMPT EN INGLÉS EXTENSO (MIDJOURNEY V6 / FLUX.1 / 3D RENDER)] ---\n\n"
                f"{prompt_en_extenso}\n\n"
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
            log_error(f"Error guardando prompt maestro: {e}", kaomoji="[X_X]")

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
