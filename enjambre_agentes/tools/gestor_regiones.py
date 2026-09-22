"""
Gestor de Carpetas y Fuentes Regionales para AgriPoli V3.

Organiza la información y descargas de fuentes por jerarquía regional:
  regiones/<estado>/<municipio_o_localidad>/
    ├── diagnostico.md               (Dossier agroecológico completo en Markdown)
    ├── referencias.json            (Metadatos de fuentes, autores y URLs de la región)
    ├── datos_relevantes.json       (Parámetros clave de clima, suelo, cultivos y biodiversidad)
    └── fuentes/
        ├── pdf/                    (Documentos oficiales, artículos y normativas en PDF)
        ├── html/                   (Páginas web descargadas en HTML y su versión limpia en Markdown)
        └── csv/                    (Tablas de estadísticas agrícolas SIAP, censos INEGI y ocurrencias)
"""
from __future__ import annotations

import os
import re
import json
import datetime
import unicodedata
from pathlib import Path
from typing import Optional, Any

from config.agri_logger import log_ok, log_info, log_error

ESTADOS_MEXICO = {
    "aguascalientes", "baja california", "baja california sur", "campeche",
    "chiapas", "chihuahua", "coahuila", "colima", "ciudad de mexico", "cdmx",
    "durango", "guanajuato", "guerrero", "hidalgo", "jalisco", "mexico",
    "estado de mexico", "edomex", "michoacan", "morelos", "nayarit",
    "nuevo leon", "oaxaca", "puebla", "queretaro", "quintana roo",
    "san luis potosi", "sinaloa", "sonora", "tabasco", "tamaulipas",
    "tlaxcala", "veracruz", "yucatan", "zacatecas"
}


def normalizar_texto(texto: str) -> str:
    """Normaliza texto removiendo acentos y convirtiendo a minusculas."""
    nfkd = unicodedata.normalize("NFKD", texto.lower().strip())
    return "".join([c for c in nfkd if not unicodedata.combining(c)])


def slugify(texto: str) -> str:
    """Convierte un texto en un slug seguro para nombres de directorio."""
    norm = normalizar_texto(texto)
    slug = re.sub(r"[^a-z0-9]+", "_", norm).strip("_")
    return slug or "general"


def parsear_region_jerarquica(region: str) -> tuple[str, str, str]:
    """
    Parsea una cadena de region en (estado, municipio, ruta_relativa).
    Ejemplos:
      'oaxaca,puerto escondido' -> ('oaxaca', 'puerto_escondido', 'regiones/oaxaca/puerto_escondido')
      'puerto escondido, oaxaca' -> ('oaxaca', 'puerto_escondido', 'regiones/oaxaca/puerto_escondido')
      'puebla' -> ('puebla', 'general', 'regiones/puebla/general')
    """
    partes = [p.strip() for p in re.split(r"[,/|;]+", region) if p.strip()]

    if len(partes) >= 2:
        p0_norm = normalizar_texto(partes[0])
        p1_norm = normalizar_texto(partes[1])

        if p0_norm in ESTADOS_MEXICO:
            estado = slugify(p0_norm)
            municipio = slugify(p1_norm)
        elif p1_norm in ESTADOS_MEXICO:
            estado = slugify(p1_norm)
            municipio = slugify(p0_norm)
        else:
            estado = slugify(p0_norm)
            municipio = slugify(p1_norm)
    elif len(partes) == 1:
        p_norm = normalizar_texto(partes[0])
        if p_norm in ESTADOS_MEXICO:
            estado = slugify(p_norm)
            municipio = "general"
        else:
            encontrado = None
            for est in sorted(ESTADOS_MEXICO, key=len, reverse=True):
                if est in p_norm:
                    encontrado = est
                    break
            if encontrado:
                estado = slugify(encontrado)
                resto = p_norm.replace(encontrado, "").strip()
                municipio = slugify(resto) or "general"
            else:
                estado = slugify(p_norm)
                municipio = "general"
    else:
        estado = "mexico"
        municipio = "general"

    ruta_relativa = f"regiones/{estado}/{municipio}"
    return estado, municipio, ruta_relativa


def asegurar_directorio_regional(region: str, base_dir: Optional[str] = None) -> dict[str, Path]:
    """
    Crea y retorna las rutas de carpetas para la region:
      - raiz: data/regiones/<estado>/<municipio>/
      - fuentes: data/regiones/<estado>/<municipio>/fuentes/
      - pdf: data/regiones/<estado>/<municipio>/fuentes/pdf/
      - html: data/regiones/<estado>/<municipio>/fuentes/html/
      - csv: data/regiones/<estado>/<municipio>/fuentes/csv/
    Tambien asegura el symlink 'regiones -> data/regiones' en la raiz del proyecto.
    """
    if not base_dir:
        project_root = Path(__file__).resolve().parent.parent
    else:
        project_root = Path(base_dir).resolve()

    estado, municipio, ruta_rel = parsear_region_jerarquica(region)
    data_regiones = project_root / "data" / "regiones"
    data_regiones.mkdir(parents=True, exist_ok=True)

    # Asegurar symlink regiones -> data/regiones si no existe
    symlink_regiones = project_root / "regiones"
    if not symlink_regiones.exists() and not symlink_regiones.is_symlink():
        try:
            symlink_regiones.symlink_to(Path("data") / "regiones", target_is_directory=True)
        except Exception:
            pass

    region_dir = data_regiones / estado / municipio
    fuentes_dir = region_dir / "fuentes"
    pdf_dir = fuentes_dir / "pdf"
    html_dir = fuentes_dir / "html"
    csv_dir = fuentes_dir / "csv"

    for d in (region_dir, fuentes_dir, pdf_dir, html_dir, csv_dir):
        d.mkdir(parents=True, exist_ok=True)

    return {
        "project_root": project_root,
        "region_dir": region_dir,
        "fuentes_dir": fuentes_dir,
        "pdf_dir": pdf_dir,
        "html_dir": html_dir,
        "csv_dir": csv_dir,
        "estado": estado,
        "municipio": municipio,
        "ruta_relativa": ruta_rel,
    }


def extraer_datos_relevantes(resumen_ejecutivo: str, region: str) -> dict[str, Any]:
    """
    Extrae parametros tecnicos clave a partir del texto del Resumen Ejecutivo
    para estructurar un JSON util para la precision del sistema.
    """
    datos = {
        "region": region,
        "fecha_extraccion": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "clima": {},
        "suelo": {},
        "cultivos": [],
        "flora_nativa": [],
        "polinizadores": [],
        "control_biologico": [],
        "normas_aplicadas": [],
    }

    if not resumen_ejecutivo:
        return datos

    # 1. Clima y Köppen
    koppen_match = re.search(r"(?:koppen|clima)[^\n:]*[:\-]\s*([^\n\.]+)", resumen_ejecutivo, re.IGNORECASE)
    if koppen_match:
        datos["clima"]["clasificacion"] = koppen_match.group(1).strip()
    
    precip_match = re.search(r"(\d+[\d\s,\.]*)\s*mm", resumen_ejecutivo, re.IGNORECASE)
    if precip_match:
        datos["clima"]["precipitacion_estimada_mm"] = precip_match.group(1).strip()

    temp_match = re.search(r"(\d+[\d\.,]*)\s*°\s*C", resumen_ejecutivo)
    if temp_match:
        datos["clima"]["temperatura_referencia_c"] = temp_match.group(1).strip()

    # 2. Suelo
    if "NOM-021" in resumen_ejecutivo:
        datos["normas_aplicadas"].append("NOM-021-SEMARNAT-2000")
    if "NOM-059" in resumen_ejecutivo:
        datos["normas_aplicadas"].append("NOM-059-SEMARNAT-2010")

    ph_match = re.search(r"pH\s*(?:de|estimado|promedio)?\s*([0-9\.\-\s]+)", resumen_ejecutivo, re.IGNORECASE)
    if ph_match:
        datos["suelo"]["ph"] = ph_match.group(1).strip()

    suelos_comunes = ["cambisol", "regosol", "vertisol", "luvisol", "feozem", "leptosol", "arenoso", "arcilloso", "franco"]
    suelos_encontrados = [s.capitalize() for s in suelos_comunes if re.search(rf"\b{s}\b", resumen_ejecutivo, re.IGNORECASE)]
    if suelos_encontrados:
        datos["suelo"]["tipos_identificados"] = suelos_encontrados

    # 3. Polinizadores y especies
    polinizadores_clave = [
        "melipona beecheii", "scaptotrigona mexicana", "bombus", "apis mellifera",
        "xylocopa", "colibri", "murcielago nectarivoro", "mariposa monarca"
    ]
    for p in polinizadores_clave:
        if re.search(rf"\b{p}\b", resumen_ejecutivo, re.IGNORECASE):
            datos["polinizadores"].append(p.title())

    # 4. Cultivos comunes
    cultivos_lista = [
        "maiz", "frijol", "calabaza", "papaya", "mango", "coco", "citricos",
        "limon", "naranja", "cafe", "aguacate", "plátano", "platano", "guanabana",
        "cacahuate", "jamaica", "ajonjoli", "chile", "tomate"
    ]
    for c in cultivos_lista:
        if re.search(rf"\b{c}\b", resumen_ejecutivo, re.IGNORECASE):
            datos["cultivos"].append(c.capitalize())

    # 5. Flora Nativa y Botanica
    flora_clave = [
        "brosimum alicastrum", "capomo", "cordia dentata", "cordoncillo",
        "tecoma stans", "tronadora", "turnera ulmifolia", "botoncillo",
        "verbena litoralis", "bursera", "copal", "prosopis", "mezquite"
    ]
    for f in flora_clave:
        if re.search(rf"\b{f}\b", resumen_ejecutivo, re.IGNORECASE):
            datos["flora_nativa"].append(f.title())

    # 6. Control Biologico y Fauna Auxiliar
    control_clave = [
        "hippodamia convergens", "catarinas", "coccinelidos", "chrysoperla carnea", "crisopas",
        "trichogramma pretiosum", "avispas parasitoides", "tagetes erecta", "cempasuchil",
        "ocimum basilicum", "albahaca", "plantas trampa"
    ]
    for cb in control_clave:
        if re.search(rf"\b{cb}\b", resumen_ejecutivo, re.IGNORECASE):
            datos["control_biologico"].append(cb.title())

    # 7. Rotacion regenerativa detectada
    if "4 Grupos" in resumen_ejecutivo or "Rotación Regenerativa" in resumen_ejecutivo:
        datos["rotacion_regenerativa"] = {
            "fase_1": "Fijadoras de N (Leguminosas)",
            "fase_2": "Descompactadoras (Raices pivotantes profundas)",
            "fase_3": "Control Fitosanitario (Alelopaticas/Biofumigantes)",
            "fase_4": "Eficiencia Hidrica (Coberturas densas)",
        }

    return datos


def deducir_institucion_url(url: str) -> str:
    """Identifica la institucion o base oficial emisora de una URL."""
    u = url.lower()
    if "conabio.gob.mx" in u or "biodiversidad.gob.mx" in u:
        return "CONABIO"
    if "enciclovida.mx" in u:
        return "EncicloVida (CONABIO)"
    if "inegi.org.mx" in u:
        return "INEGI"
    if "sader" in u or "agricultura.gob.mx" in u or "gob.mx/agricultura" in u:
        return "SADER"
    if "inifap.gob.mx" in u:
        return "INIFAP"
    if "unam.mx" in u:
        return "UNAM"
    if "gbif.org" in u:
        return "GBIF"
    if "semar.gob.mx" in u:
        return "SEMAR"
    if "semarnat.gob.mx" in u:
        return "SEMARNAT"
    if "scielo.org" in u:
        return "SciELO"
    if "arxiv.org" in u:
        return "arXiv"
    if "semanticscholar.org" in u:
        return "Semantic Scholar"
    if "gob.mx" in u:
        return "Gobierno de Mexico"
    return "Web / Oficial"


async def guardar_dossier_regional(
    region: str,
    resumen_ejecutivo: str,
    dossier_tecnico: dict,
    referencias_fuentes: list[str],
    base_dir: Optional[str] = None,
) -> dict[str, Any]:
    """
    Orquesta la persistencia local jerarquica completa de una region:
      1. Genera estructura regiones/<estado>/<municipio>/
      2. Guarda diagnostico.md con frontmatter YAML
      3. Extrae y guarda datos_relevantes.json
      4. Descarga fuentes clasificadas en fuentes/ (pdf, html, csv)
      5. Guarda el indice local referencias.json
      6. Actualiza el indice global data/referencias.json
    """
    import aiohttp
    from tools.descargador_masivo import DescargadorMasivoAsync

    carpetas = asegurar_directorio_regional(region, base_dir)
    project_root = carpetas["project_root"]
    region_dir = carpetas["region_dir"]
    estado = carpetas["estado"]
    municipio = carpetas["municipio"]
    ruta_relativa = carpetas["ruta_relativa"]

    ahora_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Nombres de archivo descriptivos con contexto de estado y municipio
    nombre_diag_desc = f"diagnostico_agroecologico_{estado}_{municipio}.md"
    nombre_ref_desc = f"referencias_fuentes_{estado}_{municipio}.json"
    nombre_datos_desc = f"datos_relevantes_{estado}_{municipio}.json"

    diagnostico_desc_path = region_dir / nombre_diag_desc
    diagnostico_alias_path = region_dir / "diagnostico.md"
    referencias_desc_path = region_dir / nombre_ref_desc
    referencias_alias_path = region_dir / "referencias.json"
    datos_desc_path = region_dir / nombre_datos_desc
    datos_alias_path = region_dir / "datos_relevantes.json"

    # Versionado / Historial: Si ya existian archivos previos para esta MISMA region,
    # archivarlos en historial/ con marca de tiempo para nunca sobreescribir ejecuciones anteriores.
    historial_dir = region_dir / "historial"
    if diagnostico_desc_path.exists():
        try:
            historial_dir.mkdir(parents=True, exist_ok=True)
            mtime_str = datetime.datetime.fromtimestamp(diagnostico_desc_path.stat().st_mtime).strftime("%Y%m%d_%H%M%S")
            import shutil
            shutil.copy2(diagnostico_desc_path, historial_dir / f"diagnostico_agroecologico_{estado}_{municipio}_{mtime_str}.md")
            if referencias_desc_path.exists():
                shutil.copy2(referencias_desc_path, historial_dir / f"referencias_fuentes_{estado}_{municipio}_{mtime_str}.json")
            if datos_desc_path.exists():
                shutil.copy2(datos_desc_path, historial_dir / f"datos_relevantes_{estado}_{municipio}_{mtime_str}.json")
            log_info(f"Version previa de '{region}' respaldada en: {ruta_relativa}/historial/", kaomoji="[o_o]")
        except Exception:
            pass

    # 1. Guardar diagnostico agroecologico descriptivo y alias
    contenido_md = (
        f"---\n"
        f"region: \"{region}\"\n"
        f"estado: \"{estado}\"\n"
        f"municipio: \"{municipio}\"\n"
        f"fecha: \"{ahora_str}\"\n"
        f"generador: \"AgriPoli Enjambre V3\"\n"
        f"total_fuentes: {len(referencias_fuentes)}\n"
        f"carpeta_local: \"{ruta_relativa}\"\n"
        f"---\n\n"
        f"{resumen_ejecutivo}\n"
    )
    try:
        # Guardar version con nombre descriptivo
        with open(diagnostico_desc_path, "w", encoding="utf-8") as f:
            f.write(contenido_md)
        # Guardar alias generico para compatibilidad
        with open(diagnostico_alias_path, "w", encoding="utf-8") as f:
            f.write(contenido_md)
        log_ok(f"Dossier regional guardado en: {ruta_relativa}/{nombre_diag_desc}", kaomoji="(^_^)/")
    except Exception as e:
        log_error(f"Error guardando diagnostico: {e}", kaomoji="[X_X]")

    # Guardar tambien copia en data/reportes/ para compatibilidad
    try:
        reportes_legacy = project_root / "data" / "reportes"
        reportes_legacy.mkdir(parents=True, exist_ok=True)
        reporte_legacy_path = reportes_legacy / f"diagnostico_{estado}_{municipio}.md"
        with open(reporte_legacy_path, "w", encoding="utf-8") as f:
            f.write(contenido_md)
    except Exception:
        pass

    # 2. Extraer y guardar datos_relevantes descriptivo y alias
    datos_relevantes = extraer_datos_relevantes(resumen_ejecutivo, region)
    datos_relevantes["estado"] = estado
    datos_relevantes["municipio"] = municipio
    try:
        with open(datos_desc_path, "w", encoding="utf-8") as f:
            json.dump(datos_relevantes, f, ensure_ascii=False, indent=2)
        with open(datos_alias_path, "w", encoding="utf-8") as f:
            json.dump(datos_relevantes, f, ensure_ascii=False, indent=2)
        log_ok(f"Datos estructurados guardados en: {ruta_relativa}/{nombre_datos_desc}", kaomoji="[O_O]")
    except Exception as e:
        log_error(f"Error guardando datos relevantes: {e}", kaomoji="[X_X]")

    # 3. Descarga masiva asincrona de fuentes clasificadas
    descargas_meta = []
    conteo_tipos = {"pdf": 0, "html": 0, "csv": 0, "json": 0, "otros": 0}

    urls_candidatas = [u for u in referencias_fuentes if not u.endswith((".png", ".jpg", ".svg", ".ico"))]

    if urls_candidatas:
        log_info(f"Iniciando descarga y clasificacion de {len(urls_candidatas)} fuentes en {ruta_relativa}/fuentes/...", kaomoji="[~_~]")
        descargador = DescargadorMasivoAsync(max_concurrencia=3, delay_segundos=0.3)

        async with aiohttp.ClientSession() as session:
            for idx, url in enumerate(urls_candidatas[:10], start=1):
                meta = await descargador.descargar_fuente_regional(session, url, carpetas, indice=idx)
                descargas_meta.append(meta)
                t = meta.get("tipo", "otros")
                if t in conteo_tipos:
                    conteo_tipos[t] += 1
                else:
                    conteo_tipos["otros"] += 1

        total_descargados = sum(1 for m in descargas_meta if m.get("estado_descarga") == "completado")
        log_ok(
            f"Descargas concluidas: {total_descargados} archivo(s) almacenado(s) "
            f"(PDFs: {conteo_tipos['pdf']}, HTML: {conteo_tipos['html']}, CSV: {conteo_tipos['csv']})",
            kaomoji="(^o^)"
        )

    # 4. Guardar referencias_fuentes local descriptivo y alias en la carpeta regional
    registro_local = {
        "region": region,
        "estado": estado,
        "municipio": municipio,
        "ruta_relativa": ruta_relativa,
        "fecha_actualizacion": ahora_str,
        "archivos_principales": {
            "diagnostico": nombre_diag_desc,
            "referencias": nombre_ref_desc,
            "datos_relevantes": nombre_datos_desc,
        },
        "total_fuentes_detectadas": len(referencias_fuentes),
        "total_archivos_descargados": len(descargas_meta),
        "conteo_por_tipo": conteo_tipos,
        "fuentes_descargadas": descargas_meta,
        "todas_las_urls": referencias_fuentes,
        "datos_relevantes": datos_relevantes,
    }
    try:
        with open(referencias_desc_path, "w", encoding="utf-8") as f:
            json.dump(registro_local, f, ensure_ascii=False, indent=2)
        with open(referencias_alias_path, "w", encoding="utf-8") as f:
            json.dump(registro_local, f, ensure_ascii=False, indent=2)
        log_ok(f"Indice regional descriptivo guardado en: {ruta_relativa}/{nombre_ref_desc}", kaomoji="(^_^)/")
    except Exception as e:
        log_error(f"Error guardando referencias_fuentes: {e}", kaomoji="[X_X]")

    # 4.5. Generar y guardar prompts hiperrealistas (Isla Polinizadora y Parcela de Cultivo)
    try:
        from agents.mini_prompt_isla import generar_prompt_isla_polinizadora
        res_prompt_isla = generar_prompt_isla_polinizadora(region, str(project_root), guardar_en_disco=True)
        registro_local["prompt_isla_polinizadora"] = res_prompt_isla.get("prompt_espanol", "")
    except Exception as e:
        log_info(f"Generacion automatica de prompt isla omitida: {e}", kaomoji="[o_o]")

    try:
        from agents.mini_prompt_cultivo import generar_prompt_cultivo_terreno
        res_prompt_cultivo = generar_prompt_cultivo_terreno(region, str(project_root), guardar_en_disco=True)
        registro_local["prompt_cultivo_terreno"] = res_prompt_cultivo.get("prompt_espanol", "")
    except Exception as e:
        log_info(f"Generacion automatica de prompt cultivo omitida: {e}", kaomoji="[o_o]")

    try:
        from agents.fusionador_prompts import fusionar_prompts_agroecologicos
        res_prompt_maestro = fusionar_prompts_agroecologicos(region, str(project_root), guardar_en_disco=True)
        registro_local["prompt_agroecologico_maestro"] = res_prompt_maestro.get("prompt_espanol_extenso", "")
    except Exception as e:
        log_info(f"Generacion automatica de prompt maestro omitida: {e}", kaomoji="[o_o]")

    # 5. Actualizar indice global master en data/referencias.json
    global_referencias_path = project_root / "data" / "referencias.json"
    registro_global = {
        "region": region,
        "estado": estado,
        "municipio": municipio,
        "slug": f"{estado}_{municipio}",
        "ruta_local": ruta_relativa,
        "referencias_json": f"{ruta_relativa}/{nombre_ref_desc}",
        "diagnostico_md": f"{ruta_relativa}/{nombre_diag_desc}",
        "datos_relevantes_json": f"{ruta_relativa}/{nombre_datos_desc}",
        "prompt_isla_txt": f"{ruta_relativa}/prompt_isla_polinizadora.txt",
        "prompt_cultivo_txt": f"{ruta_relativa}/prompt_cultivo_terreno.txt",
        "prompt_maestro_txt": f"{ruta_relativa}/prompt_agroecologico_maestro.txt",
        "fecha": ahora_str,
        "total_fuentes": len(referencias_fuentes),
        "archivos_descargados": conteo_tipos,
        "fuentes": referencias_fuentes,
    }

    try:
        historial_ref = []
        if global_referencias_path.exists():
            with open(global_referencias_path, "r", encoding="utf-8") as f:
                try:
                    contenido_json = json.load(f)
                    if isinstance(contenido_json, list):
                        historial_ref = contenido_json
                except Exception:
                    historial_ref = []

        # Reemplazar solo la entrada de esta region en el indice maestro global,
        # dejando intactas todas las demas regiones
        historial_ref = [r for r in historial_ref if r.get("slug") != f"{estado}_{municipio}"]
        historial_ref.append(registro_global)

        with open(global_referencias_path, "w", encoding="utf-8") as f:
            json.dump(historial_ref, f, ensure_ascii=False, indent=2)
        log_ok(f"Indice maestro centralizado actualizado en: data/referencias.json", kaomoji="[O_O]")
    except Exception as e:
        log_error(f"Error actualizando data/referencias.json maestro: {e}", kaomoji="[X_X]")

    return {
        "region": region,
        "estado": estado,
        "municipio": municipio,
        "ruta_relativa": ruta_relativa,
        "diagnostico_path": str(diagnostico_desc_path.relative_to(project_root)),
        "referencias_path": str(referencias_desc_path.relative_to(project_root)),
        "datos_relevantes_path": str(datos_desc_path.relative_to(project_root)),
        "total_fuentes": len(referencias_fuentes),
        "descargas": conteo_tipos,
    }
