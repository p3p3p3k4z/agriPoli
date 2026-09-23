"""
Script de Prueba, Validación y Exportación Masiva de Prompts Agroecológicos.

Ejecuta y audita la suite completa de generadores de prompts:
  1. mini_prompt_isla      (Santuario de biodiversidad e isla polinizadora circular)
  2. mini_prompt_cultivo   (Recuadro delimitado de parcela y asociación de cultivos)
  3. fusionador_prompts    (Escena maestra integral donde conviven ambos)

Exporta todos los prompts en formatos .md y .txt en:
  - data/output/prompts/
  - output/prompts/ (enlace directo accesible en la raíz del proyecto)
  - regiones/<estado>/<municipio>/
"""
from __future__ import annotations

import os
import sys
import json
import time
from pathlib import Path

# Asegurar path al proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.agri_logger import log_info, log_ok, log_error
from tools.gestor_regiones import slugify, parsear_region_jerarquica
from agents.mini_prompt_isla import generar_prompt_isla_polinizadora
from agents.mini_prompt_cultivo import generar_prompt_cultivo_terreno
from agents.fusionador_prompts import fusionar_prompts_agroecologicos


REGIONES_DE_PRUEBA = [
    "la mixteca, oaxaca",
    "puerto escondido, oaxaca",
    "merida, yucatan",
    "uruapan, michoacan",
]


def asegurar_carpetas_output(base_dir: Path) -> Path:
    """Crea y retorna data/output/prompts/ y enlace output/prompts/."""
    output_dir = base_dir / "data" / "output" / "prompts"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Enlace simbolico en raiz output -> data/output
    symlink_output = base_dir / "output"
    if not symlink_output.exists() and not symlink_output.is_symlink():
        try:
            symlink_output.symlink_to(Path("data") / "output", target_is_directory=True)
        except Exception:
            pass

    return output_dir


def exportar_archivos_markdown_y_texto(
    output_dir: Path,
    region: str,
    res_isla: dict,
    res_cultivo: dict,
    res_maestro: dict
) -> dict[str, str]:
    """Guarda versiones en .md y .txt individuales y consolidadas."""
    estado, municipio, _ = parsear_region_jerarquica(region)
    slug = f"{estado}_{municipio}"
    region_title = region.title()

    rutas_generadas = {}

    # 1. Guardar Isla Polinizadora (.md y .txt)
    isla_md_path = output_dir / f"prompt_isla_{slug}.md"
    isla_txt_path = output_dir / f"prompt_isla_{slug}.txt"
    persp_isla = res_isla.get("perspectivas", {})

    contenido_isla_md = f"""# Prompts: Isla Polinizadora Circular (Aislada PNG / Sin Fondo)
**Región:** {region_title}  
**Estado:** {estado.title()} | **Municipio/Localidad:** {municipio.title()}  
**Generador:** AgriPoli V3 (`mini_prompt_isla`)  
**Estilo:** Asset 3D / Diorama Flotante Aislado en Fondo Blanco Puro de Estudio (Sin Fondo Exterior / Sin Cielo)

---

## 1. Prompt Principal: Vista Isométrica 3D a 45° (Diorama Aislado PNG)

### Español (DALL-E 3 / Bing Image Creator)
```text
{res_isla.get('prompt_espanol', '')}
```

### Inglés (Midjourney v6.1 / Flux.1)
```text
{res_isla.get('prompt_ingles', '')}
```

---

## 2. Prompts de Ajuste y Perspectiva

### Perspectiva A: {persp_isla.get('cenital_90deg', {}).get('nombre', 'Vista Cenital / Top-Down 90°')}

**Español:**
```text
{persp_isla.get('cenital_90deg', {}).get('prompt_es', '')}
```

**Inglés:**
```text
{persp_isla.get('cenital_90deg', {}).get('prompt_en', '')}
```

---

### Perspectiva B: {persp_isla.get('ras_suelo_macro', {}).get('nombre', 'Vista Frontal a Ras de Suelo / Nivel de Ojo')}

**Español:**
```text
{persp_isla.get('ras_suelo_macro', {}).get('prompt_es', '')}
```

**Inglés:**
```text
{persp_isla.get('ras_suelo_macro', {}).get('prompt_en', '')}
```

---

### Perspectiva C: {persp_isla.get('corte_transversal_3d', {}).get('nombre', 'Vista Axonométrica 3/4 en Corte Transversal 3D')}

**Español:**
```text
{persp_isla.get('corte_transversal_3d', {}).get('prompt_es', '')}
```

**Inglés:**
```text
{persp_isla.get('corte_transversal_3d', {}).get('prompt_en', '')}
```

---

## Propiedades Botánicas y Ecológicas Extraídas
```json
{json.dumps(res_isla.get('propiedades_extraidas', {}), ensure_ascii=False, indent=2)}
```
"""
    contenido_isla_txt = (
        f"========================================================================\n"
        f"PROMPTS DE IMAGEN: ISLA POLINIZADORA EN {region_title.upper()}\n"
        f"Generado por: AgriPoli V3 (mini_prompt_isla)\n"
        f"Formato: Asset 3D / PNG Cutout Aislado en Fondo Blanco (Sin Fondo Exterior)\n"
        f"========================================================================\n\n"
        f"------------------------------------------------------------------------\n"
        f"1. PROMPT PRINCIPAL (Vista Isométrica 3D a 45° — Diorama Aislado PNG)\n"
        f"------------------------------------------------------------------------\n\n"
        f"[ESPAÑOL]\n{res_isla.get('prompt_espanol', '')}\n\n"
        f"[INGLÉS (Midjourney v6.1 / Flux.1)]\n{res_isla.get('prompt_ingles', '')}\n\n"
        f"------------------------------------------------------------------------\n"
        f"2. PERSPECTIVAS Y AJUSTES DE CÁMARA JUGANDO CON LA MISMA ESCENA\n"
        f"------------------------------------------------------------------------\n\n"
        f"▶ PERSPECTIVA A: {persp_isla.get('cenital_90deg', {}).get('nombre', 'Vista Cenital / Top-Down 90°')}\n"
        f"[ESPAÑOL]\n{persp_isla.get('cenital_90deg', {}).get('prompt_es', '')}\n\n"
        f"[INGLÉS]\n{persp_isla.get('cenital_90deg', {}).get('prompt_en', '')}\n\n"
        f"------------------------------------------------------------------------\n"
        f"▶ PERSPECTIVA B: {persp_isla.get('ras_suelo_macro', {}).get('nombre', 'Vista Frontal a Ras de Suelo / Nivel de Ojo')}\n"
        f"[ESPAÑOL]\n{persp_isla.get('ras_suelo_macro', {}).get('prompt_es', '')}\n\n"
        f"[INGLÉS]\n{persp_isla.get('ras_suelo_macro', {}).get('prompt_en', '')}\n\n"
        f"------------------------------------------------------------------------\n"
        f"▶ PERSPECTIVA C: {persp_isla.get('corte_transversal_3d', {}).get('nombre', 'Vista Axonométrica 3/4 en Corte Transversal')}\n"
        f"[ESPAÑOL]\n{persp_isla.get('corte_transversal_3d', {}).get('prompt_es', '')}\n\n"
        f"[INGLÉS]\n{persp_isla.get('corte_transversal_3d', {}).get('prompt_en', '')}\n\n"
        f"========================================================================\n"
    )

    with open(isla_md_path, "w", encoding="utf-8") as f:
        f.write(contenido_isla_md)
    with open(isla_txt_path, "w", encoding="utf-8") as f:
        f.write(contenido_isla_txt)
    rutas_generadas["isla_md"] = str(isla_md_path)

    # 2. Guardar Parcela Agrícola (.md y .txt)
    cultivo_md_path = output_dir / f"prompt_cultivo_{slug}.md"
    cultivo_txt_path = output_dir / f"prompt_cultivo_{slug}.txt"
    persp_cultivo = res_cultivo.get("perspectivas", {})

    contenido_cultivo_md = f"""# Prompts: Parcela Agrícola y Policultivo (Bloque Aislado PNG)
**Región:** {region_title}  
**Estado:** {estado.title()} | **Municipio/Localidad:** {municipio.title()}  
**Generador:** AgriPoli V3 (`mini_prompt_cultivo`)  
**Estilo:** Bloque 3D / Diorama de Terreno Agrícola Aislado en Fondo Blanco Puro (Sin Fondo Exterior / Sin Cielo)

---

## 1. Prompt Principal: Vista Isométrica 3D a 45° (Bloque Aislado PNG)

### Español (DALL-E 3 / Bing Image Creator)
```text
{res_cultivo.get('prompt_espanol', '')}
```

### Inglés (Midjourney v6.1 / Flux.1)
```text
{res_cultivo.get('prompt_ingles', '')}
```

---

## 2. Prompts de Ajuste y Perspectiva

### Perspectiva A: {persp_cultivo.get('cenital_90deg', {}).get('nombre', 'Vista Cenital / Top-Down 90°')}

**Español:**
```text
{persp_cultivo.get('cenital_90deg', {}).get('prompt_es', '')}
```

**Inglés:**
```text
{persp_cultivo.get('cenital_90deg', {}).get('prompt_en', '')}
```

---

### Perspectiva B: {persp_cultivo.get('ras_suelo_macro', {}).get('nombre', 'Vista Frontal a Ras de Suelo / Entre Surcos')}

**Español:**
```text
{persp_cultivo.get('ras_suelo_macro', {}).get('prompt_es', '')}
```

**Inglés:**
```text
{persp_cultivo.get('ras_suelo_macro', {}).get('prompt_en', '')}
```

---

### Perspectiva C: {persp_cultivo.get('corte_transversal_3d', {}).get('nombre', 'Vista Axonométrica 3/4 con Perfil de Estratos de Suelo')}

**Español:**
```text
{persp_cultivo.get('corte_transversal_3d', {}).get('prompt_es', '')}
```

**Inglés:**
```text
{persp_cultivo.get('corte_transversal_3d', {}).get('prompt_en', '')}
```

---

## Propiedades Agronómicas y Edafológicas Extraídas
```json
{json.dumps(res_cultivo.get('propiedades_extraidas', {}), ensure_ascii=False, indent=2)}
```
"""
    contenido_cultivo_txt = (
        f"========================================================================\n"
        f"PROMPTS DE IMAGEN: PARCELA Y RECUADRO DE CULTIVOS EN {region_title.upper()}\n"
        f"Generado por: AgriPoli V3 (mini_prompt_cultivo)\n"
        f"Formato: Bloque 3D / PNG Cutout Aislado en Fondo Blanco (Sin Fondo Exterior)\n"
        f"========================================================================\n\n"
        f"------------------------------------------------------------------------\n"
        f"1. PROMPT PRINCIPAL (Vista Isométrica 3D a 45° — Bloque Aislado PNG)\n"
        f"------------------------------------------------------------------------\n\n"
        f"[ESPAÑOL]\n{res_cultivo.get('prompt_espanol', '')}\n\n"
        f"[INGLÉS (Midjourney v6.1 / Flux.1)]\n{res_cultivo.get('prompt_ingles', '')}\n\n"
        f"------------------------------------------------------------------------\n"
        f"2. PERSPECTIVAS Y AJUSTES DE CÁMARA JUGANDO CON LA MISMA ESCENA\n"
        f"------------------------------------------------------------------------\n\n"
        f"▶ PERSPECTIVA A: {persp_cultivo.get('cenital_90deg', {}).get('nombre', 'Vista Cenital / Top-Down 90°')}\n"
        f"[ESPAÑOL]\n{persp_cultivo.get('cenital_90deg', {}).get('prompt_es', '')}\n\n"
        f"[INGLÉS]\n{persp_cultivo.get('cenital_90deg', {}).get('prompt_en', '')}\n\n"
        f"------------------------------------------------------------------------\n"
        f"▶ PERSPECTIVA B: {persp_cultivo.get('ras_suelo_macro', {}).get('nombre', 'Vista Frontal a Ras de Suelo / Entre Surcos')}\n"
        f"[ESPAÑOL]\n{persp_cultivo.get('ras_suelo_macro', {}).get('prompt_es', '')}\n\n"
        f"[INGLÉS]\n{persp_cultivo.get('ras_suelo_macro', {}).get('prompt_en', '')}\n\n"
        f"------------------------------------------------------------------------\n"
        f"▶ PERSPECTIVA C: {persp_cultivo.get('corte_transversal_3d', {}).get('nombre', 'Vista Axonométrica 3/4 con Perfil de Estratos')}\n"
        f"[ESPAÑOL]\n{persp_cultivo.get('corte_transversal_3d', {}).get('prompt_es', '')}\n\n"
        f"[INGLÉS]\n{persp_cultivo.get('corte_transversal_3d', {}).get('prompt_en', '')}\n\n"
        f"========================================================================\n"
    )

    with open(cultivo_md_path, "w", encoding="utf-8") as f:
        f.write(contenido_cultivo_md)
    with open(cultivo_txt_path, "w", encoding="utf-8") as f:
        f.write(contenido_cultivo_txt)
    rutas_generadas["cultivo_md"] = str(cultivo_md_path)

    # 3. Guardar Escena Maestra Fusionada (.md y .txt)
    maestro_md_path = output_dir / f"prompt_maestro_{slug}.md"
    maestro_txt_path = output_dir / f"prompt_maestro_{slug}.txt"
    persp_maestro = res_maestro.get("perspectivas", {})

    contenido_maestro_md = f"""# Prompt Maestro: Isla Polinizadora + Parcela Agrícola (Diorama 3D Aislado)
**Región:** {region_title}  
**Estado:** {estado.title()} | **Municipio/Localidad:** {municipio.title()}  
**Generador:** AgriPoli V3 (`fusionador_prompts`)  
**Estilo:** Gran Diorama 3D Agroecológico Aislado en Fondo Blanco Puro (Sin Fondo Exterior / Sin Cielo)

> **Concepto Visual:** Convivencia armónica de la Isla Polinizadora circular viva en el centro del bloque de terreno agrícola delimitado, mostrando en plena acción a los polinizadores y fauna auxiliar pecoreando entre el santuario y los cultivos asociados en un asset 3D completamente recortado.

---

## 1. Prompt Principal: Gran Diorama Agroecológico 3D a 45° (Aislado PNG)

### Español Extenso (DALL-E 3 / Bing / Concept Art)
```text
{res_maestro.get('prompt_espanol_extenso', '')}
```

### Inglés Extenso (Midjourney v6.1 / Flux.1 / 3D Scene Reference)
```text
{res_maestro.get('prompt_ingles_extenso', '')}
```

---

## 2. Prompts de Ajuste y Perspectiva

### Perspectiva A: {persp_maestro.get('cenital_90deg', {}).get('nombre', 'Vista Cenital / Top-Down 90°')}

**Español:**
```text
{persp_maestro.get('cenital_90deg', {}).get('prompt_es', '')}
```

**Inglés:**
```text
{persp_maestro.get('cenital_90deg', {}).get('prompt_en', '')}
```

---

### Perspectiva B: {persp_maestro.get('ras_suelo_transicion', {}).get('nombre', 'Vista Frontal a Ras de Suelo / Transición')}

**Español:**
```text
{persp_maestro.get('ras_suelo_transicion', {}).get('prompt_es', '')}
```

**Inglés:**
```text
{persp_maestro.get('ras_suelo_transicion', {}).get('prompt_en', '')}
```

---

### Perspectiva C: {persp_maestro.get('corte_transversal_3d', {}).get('nombre', 'Vista Axonométrica 3/4 en Corte Transversal')}

**Español:**
```text
{persp_maestro.get('corte_transversal_3d', {}).get('prompt_es', '')}
```

**Inglés:**
```text
{persp_maestro.get('corte_transversal_3d', {}).get('prompt_en', '')}
```
"""
    contenido_maestro_txt = (
        f"========================================================================\n"
        f"PROMPTS DE IMAGEN: ESCENA MAESTRA AGROECOLÓGICA EN {region_title.upper()}\n"
        f"Isla Polinizadora Circular + Parcela Agrícola en Convivencia Viva\n"
        f"Generado por: AgriPoli V3 (fusionador_prompts)\n"
        f"Formato: Gran Diorama 3D / PNG Cutout Aislado en Fondo Blanco (Sin Fondo Exterior)\n"
        f"========================================================================\n\n"
        f"------------------------------------------------------------------------\n"
        f"1. PROMPT PRINCIPAL (Gran Diorama Agroecológico 3D a 45° — Aislado PNG)\n"
        f"------------------------------------------------------------------------\n\n"
        f"[ESPAÑOL EXTENSO]\n{res_maestro.get('prompt_espanol_extenso', '')}\n\n"
        f"[INGLÉS EXTENSO (Midjourney v6.1 / Flux.1)]\n{res_maestro.get('prompt_ingles_extenso', '')}\n\n"
        f"------------------------------------------------------------------------\n"
        f"2. PERSPECTIVAS Y AJUSTES DE CÁMARA JUGANDO CON LA MISMA ESCENA\n"
        f"------------------------------------------------------------------------\n\n"
        f"▶ PERSPECTIVA A: {persp_maestro.get('cenital_90deg', {}).get('nombre', 'Vista Cenital / Top-Down 90°')}\n"
        f"[ESPAÑOL]\n{persp_maestro.get('cenital_90deg', {}).get('prompt_es', '')}\n\n"
        f"[INGLÉS]\n{persp_maestro.get('cenital_90deg', {}).get('prompt_en', '')}\n\n"
        f"------------------------------------------------------------------------\n"
        f"▶ PERSPECTIVA B: {persp_maestro.get('ras_suelo_transicion', {}).get('nombre', 'Vista Frontal a Ras de Suelo / Transición')}\n"
        f"[ESPAÑOL]\n{persp_maestro.get('ras_suelo_transicion', {}).get('prompt_es', '')}\n\n"
        f"[INGLÉS]\n{persp_maestro.get('ras_suelo_transicion', {}).get('prompt_en', '')}\n\n"
        f"------------------------------------------------------------------------\n"
        f"▶ PERSPECTIVA C: {persp_maestro.get('corte_transversal_3d', {}).get('nombre', 'Vista Axonométrica 3/4 en Corte Transversal')}\n"
        f"[ESPAÑOL]\n{persp_maestro.get('corte_transversal_3d', {}).get('prompt_es', '')}\n\n"
        f"[INGLÉS]\n{persp_maestro.get('corte_transversal_3d', {}).get('prompt_en', '')}\n\n"
        f"========================================================================\n"
    )

    with open(maestro_md_path, "w", encoding="utf-8") as f:
        f.write(contenido_maestro_md)
    with open(maestro_txt_path, "w", encoding="utf-8") as f:
        f.write(contenido_maestro_txt)
    rutas_generadas["maestro_md"] = str(maestro_md_path)

    return rutas_generadas


def generar_indice_general(output_dir: Path, resumen_regiones: list[dict]):
    """Genera un archivo INDICE_PROMPTS.md central con todos los prompts y accesos rápidos."""
    indice_path = output_dir / "INDICE_PROMPTS.md"
    lineas = [
        "# Catálogo Maestro de Prompts de Imagen Agroecológicos — AgriPoli V3",
        "",
        "Prompts generados para referencia de modelado 3D, concept art e infografías agrícolas.",
        "",
        "| Región Evaluada | Isla Polinizadora | Parcela Agrícola | Escena Maestra Fusionada |",
        "| :--- | :--- | :--- | :--- |",
    ]

    for item in resumen_regiones:
        reg = item["region"].title()
        slug = item["slug"]
        lineas.append(
            f"| **{reg}** | [`isla_{slug}.md`](file://{item['isla_md']}) | [`cultivo_{slug}.md`](file://{item['cultivo_md']}) | [`maestro_{slug}.md`](file://{item['maestro_md']}) |"
        )

    lineas.append("")
    lineas.append("---")
    lineas.append("### Estructura de Salida:")
    lineas.append("Los archivos están disponibles tanto en Markdown (`.md`) para lectura formateada con bloques de código, como en Texto Plano (`.txt`) listos para copiar y pegar directamente en DALL-E 3, Midjourney o Flux.")

    with open(indice_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas))

    log_ok(f"Índice general actualizado en: {indice_path}", kaomoji="(^_^)/")


def ejecutar_pruebas_y_auditoria():
    output_dir = asegurar_carpetas_output(BASE_DIR)
    print("\n" + "="*75)
    print("INICIANDO PRUEBA Y AUDITORÍA DE GENERADORES DE PROMPTS")
    print(f"Directorio de salida: {output_dir}")
    print("="*75 + "\n")

    resumen_regiones = []
    errores = []

    for idx, region in enumerate(REGIONES_DE_PRUEBA, start=1):
        print(f"\n[{idx}/{len(REGIONES_DE_PRUEBA)}] Evaluando región: '{region}'...")
        t0 = time.time()
        try:
            # 1. Probar Isla Polinizadora
            log_info(f"Paso 1: Generando prompt de Isla Polinizadora para '{region}'...", kaomoji="[~_~]")
            res_isla = generar_prompt_isla_polinizadora(region, str(BASE_DIR), guardar_en_disco=True)
            assert res_isla.get("prompt_espanol"), "Prompt en español de isla vacío"
            assert res_isla.get("prompt_ingles"), "Prompt en inglés de isla vacío"

            # 2. Probar Parcela Agrícola
            log_info(f"Paso 2: Generando prompt de Parcela Agrícola para '{region}'...", kaomoji="[~_~]")
            res_cultivo = generar_prompt_cultivo_terreno(region, str(BASE_DIR), guardar_en_disco=True)
            assert res_cultivo.get("prompt_espanol"), "Prompt en español de cultivo vacío"
            assert res_cultivo.get("prompt_ingles"), "Prompt en inglés de cultivo vacío"

            # 3. Probar Fusión Maestra
            log_info(f"Paso 3: Fusionando ambos prompts en Escena Maestra para '{region}'...", kaomoji="[~_~]")
            res_maestro = fusionar_prompts_agroecologicos(region, str(BASE_DIR), guardar_en_disco=True)
            assert res_maestro.get("prompt_espanol_extenso"), "Prompt maestro en español vacío"
            assert res_maestro.get("prompt_ingles_extenso"), "Prompt maestro en inglés vacío"

            # 4. Exportar a data/output/prompts/ en .md y .txt
            rutas = exportar_archivos_markdown_y_texto(output_dir, region, res_isla, res_cultivo, res_maestro)
            estado, municipio, _ = parsear_region_jerarquica(region)
            slug = f"{estado}_{municipio}"

            resumen_regiones.append({
                "region": region,
                "slug": slug,
                **rutas
            })

            duracion = round(time.time() - t0, 2)
            log_ok(f"Región '{region}' procesada sin errores en {duracion}s.", kaomoji="(^o^)/")

        except Exception as e:
            log_error(f"Error procesando '{region}': {e}", kaomoji="[X_X]")
            errores.append({"region": region, "error": str(e)})

    # Generar índice consolidado
    generar_indice_general(output_dir, resumen_regiones)

    print("\n" + "="*75)
    print("RESUMEN DE AUDITORÍA Y GENERACIÓN")
    print(f"Total regiones evaluadas: {len(REGIONES_DE_PRUEBA)}")
    print(f"Regiones exitosas:        {len(resumen_regiones)}")
    print(f"Errores encontrados:      {len(errores)}")
    print(f"Carpeta de salida:        {output_dir}")
    print("="*75 + "\n")

    if errores:
        print("Detalle de errores:")
        for err in errores:
            print(f"  * {err['region']}: {err['error']}")
        sys.exit(1)
    else:
        log_ok("Auditoría completada exitosamente al 100% sin errores.", kaomoji="(^w^)")


if __name__ == "__main__":
    ejecutar_pruebas_y_auditoria()
