"""
Servicio local de consulta e introspección del Catálogo de Biodiversidad de México.
Utiliza los catálogos descargados de EncicloVida, CONABIO y SNIB ubicados en data/descargas_masivas/.

Permite búsqueda rápida con cero latencia y sin conexión a internet de:
- 1,188 especies de Plantas Melíferas y Flora Nativa.
- 2,734 especies de Visitantes Polinizadores (abejas, mariposas, polillas, colibríes, murciélagos).
"""
import os
import json
import re
from typing import Optional
from langchain_core.tools import tool

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_MASIVAS = os.path.join(BASE_DIR, "data", "descargas_masivas")
PLANTAS_DIR = os.path.join(DATA_MASIVAS, "plantas_meliferas")
POLINIZADORES_DIR = os.path.join(DATA_MASIVAS, "visitantes_polinizadores")

# Caché en memoria para búsquedas instantáneas
_INDICE_PLANTAS: Optional[list[dict]] = None
_INDICE_POLINIZADORES: Optional[list[dict]] = None


def _extraer_id_y_slug(item_str: str) -> tuple[str, str]:
    """Parsea una cadena como '/especies/143953-myrtillocactus-geometrizans'."""
    item = item_str.replace("/especies/", "").strip()
    partes = item.split("-", 1)
    esp_id = partes[0]
    slug = partes[1].replace("-", " ") if len(partes) > 1 else ""
    return esp_id, slug


def _cargar_indice_plantas() -> list[dict]:
    global _INDICE_PLANTAS
    if _INDICE_PLANTAS is not None:
        return _INDICE_PLANTAS

    indice = []
    json_path = os.path.join(DATA_MASIVAS, "catalogo_plantas_meliferas.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                items = json.load(f)
            for item in items:
                esp_id, slug = _extraer_id_y_slug(item)
                # Intentar leer metadata detallada si existe
                meta_file = os.path.join(PLANTAS_DIR, esp_id, "metadata.json")
                nombre_cientifico = slug.capitalize()
                url = f"https://enciclovida.mx/especies/{esp_id}"
                snib_url = ""

                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r", encoding="utf-8") as mf:
                            mdata = json.load(mf)
                            nombre_cientifico = mdata.get("scientific_name", nombre_cientifico)
                            url = mdata.get("url", url)
                            snib_url = mdata.get("snib_url", "")
                    except Exception:
                        pass

                indice.append({
                    "id": esp_id,
                    "nombre": nombre_cientifico,
                    "slug": slug,
                    "tipo": "planta_melifera",
                    "url": url,
                    "snib_url": snib_url,
                })
        except Exception as e:
            print(f"[Aviso] Error cargando catálogo de plantas melíferas: {e}")

    _INDICE_PLANTAS = indice
    return _INDICE_PLANTAS


def _cargar_indice_polinizadores() -> list[dict]:
    global _INDICE_POLINIZADORES
    if _INDICE_POLINIZADORES is not None:
        return _INDICE_POLINIZADORES

    indice = []
    json_path = os.path.join(DATA_MASIVAS, "catalogo_visitantes_polinizadores.json")
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                items = json.load(f)
            for item in items:
                esp_id, slug = _extraer_id_y_slug(item)
                meta_file = os.path.join(POLINIZADORES_DIR, esp_id, "metadata.json")
                nombre_cientifico = slug.capitalize()
                url = f"https://enciclovida.mx/especies/{esp_id}"
                snib_url = ""

                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r", encoding="utf-8") as mf:
                            mdata = json.load(mf)
                            nombre_cientifico = mdata.get("scientific_name", nombre_cientifico)
                            url = mdata.get("url", url)
                            snib_url = mdata.get("snib_url", "")
                    except Exception:
                        pass

                indice.append({
                    "id": esp_id,
                    "nombre": nombre_cientifico,
                    "slug": slug,
                    "tipo": "polinizador",
                    "url": url,
                    "snib_url": snib_url,
                })
        except Exception as e:
            print(f"[Aviso] Error cargando catálogo de polinizadores: {e}")

    _INDICE_POLINIZADORES = indice
    return _INDICE_POLINIZADORES


def buscar_plantas_meliferas(query: str, limite: int = 5) -> list[dict]:
    """Busca plantas melíferas y flora nativa por nombre común o científico."""
    indice = _cargar_indice_plantas()
    q_tokens = re.sub(r"[^\w\s]", "", query.lower()).split()
    resultados = []

    for item in indice:
        texto = f"{item['nombre']} {item['slug']}".lower()
        # Coincidencia de todos o la mayoría de los tokens
        if all(tok in texto for tok in q_tokens):
            resultados.append(item)
        elif any(tok in texto for tok in q_tokens) and len(q_tokens) > 1:
            resultados.append(item)

        if len(resultados) >= limite * 2:
            break

    return resultados[:limite]


def buscar_polinizadores(query: str, limite: int = 5) -> list[dict]:
    """Busca visitantes polinizadores de México (abejas, mariposas, aves, murciélagos)."""
    indice = _cargar_indice_polinizadores()
    q_tokens = re.sub(r"[^\w\s]", "", query.lower()).split()
    resultados = []

    for item in indice:
        texto = f"{item['nombre']} {item['slug']}".lower()
        if all(tok in texto for tok in q_tokens):
            resultados.append(item)
        elif any(tok in texto for tok in q_tokens) and len(q_tokens) > 1:
            resultados.append(item)

        if len(resultados) >= limite * 2:
            break

    return resultados[:limite]


@tool
def consultar_catalogo_biodiversidad_local(consulta: str) -> str:
    """Consulta el catálogo local de biodiversidad mexicana (EncicloVida, CONABIO, SNIB).
    
    Busca al instante y sin conexión a internet en más de 3,900 especies:
    - Plantas melíferas, arbustos y cactáceas nativas que alimentan polinizadores.
    - Polinizadores nativos de México: abejas silvestres, meliponas, abejorros,
      mariposas, polillas, colibríes y murciélagos nectarívoros.
      
    Args:
        consulta: Nombre común o científico de la planta o polinizador (ej. 'Garambullo', 'Melipona', 'Agave', 'Bombus').
    """
    plantas = buscar_plantas_meliferas(consulta, limite=5)
    polinizadores = buscar_polinizadores(consulta, limite=5)

    if not plantas and not polinizadores:
        return (
            f"No se encontraron registros exactos en el catálogo local para '{consulta}'. "
            f"Puedes intentar con nombres científicos o géneros afines (ej. Opuntia, Apis, Bombus, Melipona, Salvia)."
        )

    salida = [f"[CATALOGO LOCAL DE BIODIVERSIDAD] Resultados para: '{consulta}'\n"]

    if plantas:
        salida.append("(^-^) [FLORA MELIFERA Y NATIVA IDENTIFICADA]")
        for p in plantas:
            salida.append(f"- {p['nombre']} (ID: {p['id']})")
            salida.append(f"  * Ficha EncicloVida: {p['url']}")
            if p.get("snib_url"):
                salida.append(f"  * Geoportal SNIB: {p['snib_url']}")
        salida.append("")

    if polinizadores:
        salida.append("(*_*) [VISITANTES POLINIZADORES REGISTRADOS EN MEXICO]")
        for pol in polinizadores:
            salida.append(f"- {pol['nombre']} (ID: {pol['id']})")
            salida.append(f"  * Ficha EncicloVida: {pol['url']}")
            if pol.get("snib_url"):
                salida.append(f"  * Geoportal SNIB: {pol['snib_url']}")
        salida.append("")

    salida.append(
        "(o_o) [NOTA TECNICA] Datos extraidos de los catalogos del Sistema Nacional de Informacion "
        "sobre Biodiversidad (SNIB/CONABIO) y EncicloVida almacenados localmente en AgriPoli."
    )
    return "\n".join(salida)


def exportar_resumen_catalogo_para_rag() -> str:
    """Genera un documento Markdown representativo del catálogo de biodiversidad
    para ser indexado en data/knowledge/polinizadores/catalogo_biodiversidad_mexico.md.
    """
    plantas = _cargar_indice_plantas()
    polinizadores = _cargar_indice_polinizadores()

    dest_file = os.path.join(
        BASE_DIR, "data", "knowledge", "polinizadores", "catalogo_biodiversidad_mexico.md"
    )
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)

    lineas = [
        "# Catálogo de Flora Melífera y Visitantes Polinizadores de México",
        "",
        "**Fuente:** CONABIO / SNIB / EncicloVida México (Descarga Masiva Local AgriPoli)",
        f"**Estadísticas:** {len(plantas)} especies de flora melífera y {len(polinizadores)} especies de visitantes polinizadores.",
        "",
        "## 1. Familias y Especies Notables de Flora Melífera Nativa",
        "Las plantas melíferas proporcionan néctar y polen indispensables para las abejas nativas (Meliponini), abejorros y lepidópteros:",
        "",
    ]

    # Muestra representativa de especies con nombre común
    con_nombre_comun = [p for p in plantas if "(" in p["nombre"]][:60]
    for p in con_nombre_comun:
        lineas.append(f"- **{p['nombre']}** | Ficha: {p['url']}")

    lineas.extend([
        "",
        "## 2. Principales Grupos de Polinizadores Nativos de México",
        "El catálogo abarca insectos, aves y mamíferos polinizadores fundamentales para los agroecosistemas:",
        "",
    ])

    polin_representativos = [p for p in polinizadores if any(term in p["nombre"].lower() for term in ["melipona", "bombus", "apis", "lepidoptera", "glossophaga", "artibeus", "chiroderma", "leptonycteris"])][:60]
    if not polin_representativos:
        polin_representativos = polinizadores[:60]

    for pol in polin_representativos:
        lineas.append(f"- **{pol['nombre']}** (ID SNIB: `{pol['id']}`) | Ficha: {pol['url']}")

    contenido = "\n".join(lineas)
    with open(dest_file, "w", encoding="utf-8") as f:
        f.write(contenido)

    return dest_file


if __name__ == "__main__":
    print(f"Cargando catálogo local de descargas masivas...")
    p = _cargar_indice_plantas()
    pol = _cargar_indice_polinizadores()
    print(f"Plantas melíferas cargadas: {len(p)}")
    print(f"Polinizadores cargados: {len(pol)}")
    
    print("\nProbando búsqueda: 'Garambullo'")
    print(consultar_catalogo_biodiversidad_local.invoke({"consulta": "Garambullo"}))
    
    print("\nExportando resumen para RAG...")
    ruta = exportar_resumen_catalogo_para_rag()
    print(f"Resumen generado en: {ruta}")
