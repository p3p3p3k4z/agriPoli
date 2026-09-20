#!/usr/bin/env python3
"""
AgriPoli — Sistema de Apoyo Multiagente para el Manejo Agrícola y Preservación de Polinizadores.

Entry point CLI que ejecuta el pipeline completo:
  1. Investigador (Tavily) → Descubre URLs de fuentes mexicanas
  2. Scraper & RAG (Playwright) → Extrae y vectoriza contenido
  3. Sintetizador (structured output) → Produce JSON DatosRegion

Uso:
    python main.py "La Mixteca, Oaxaca"
    python main.py "Selva Lacandona, Chiapas" --provider Groq
    python main.py "Valle del Yaqui, Sonora" --provider Cohere --model command-r-plus
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from datetime import datetime

from config.keys import validate_keys
from agents.graph import run_agripoli


def main() -> None:
    """Punto de entrada principal del CLI de AgriPoli."""
    parser = argparse.ArgumentParser(
        description="AgriPoli — Sistema de Apoyo Multiagente para el Manejo Agrícola y Preservación de Polinizadores",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python main.py "La Mixteca, Oaxaca"
  python main.py "Selva Lacandona, Chiapas" --provider Groq
  python main.py "Valle del Yaqui, Sonora" --provider Cohere --model command-r-plus
  python main.py "Sierra Norte, Puebla" --output datos_puebla.json
        """,
    )
    
    parser.add_argument(
        "region",
        type=str,
        help="Región de México a investigar (ej. 'La Mixteca, Oaxaca')",
    )
    parser.add_argument(
        "--provider",
        type=str,
        default="Gemini",
        choices=["Gemini", "Groq", "Cohere"],
        help="Proveedor LLM a usar (default: Gemini)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Modelo LLM específico (default: el por defecto del proveedor)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Ruta del archivo JSON de salida (default: output/<region>.json)",
    )
    parser.add_argument(
        "--thread-id",
        type=str,
        default=None,
        help="ID de hilo para la memoria del grafo (default: UUID aleatorio)",
    )
    
    args = parser.parse_args()
    
    # --- Validar API keys ---
    required_keys = ["TAVILY_API_KEY"]
    if args.provider == "Gemini":
        required_keys.append("GEMINI_API_KEY")
    elif args.provider == "Groq":
        required_keys.append("GROQ_API_KEY")
    elif args.provider == "Cohere":
        required_keys.append("COHERE_API_KEY")
    
    try:
        validate_keys(*required_keys)
    except ValueError as e:
        print(f"\n[X_X] [ERROR: CONFIGURACION] {e}", file=sys.stderr)
        sys.exit(1)
    
    # --- Configurar salida ---
    if args.output:
        output_path = Path(args.output)
    else:
        nombre_archivo = args.region.replace(" ", "_").replace(",", "").replace(".", "")
        output_path = Path("output") / f"{nombre_archivo}.json"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    thread_id = args.thread_id or str(uuid.uuid4())
    
    # --- Banner ---
    print("\n" + "=" * 70)
    print("  (^-^) [AGRIPOLI] — Sistema de Apoyo Multiagente")
    print("=" * 70)
    print(f"  Región:    {args.region}")
    print(f"  Proveedor: {args.provider}" + (f" ({args.model})" if args.model else ""))
    print(f"  Salida:    {output_path}")
    print(f"  Thread:    {thread_id[:8]}...")
    print(f"  Inicio:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70 + "\n")
    
    # --- Ejecutar el enjambre ---
    try:
        result = run_agripoli(
            region=args.region,
            thread_id=thread_id,
            provider=args.provider,
            llm_model_name=args.model,
        )
    except Exception as e:
        print(f"\n[X_X] [ERROR: ENJAMBRE] {e}", file=sys.stderr)
        sys.exit(1)
    
    # --- Guardar JSON ---
    json_str = result.get("datos_estructurados", "{}")
    errores = result.get("errores", [])
    
    try:
        # Validar que es JSON válido
        datos = json.loads(json_str)
        
        # Escribir con formato legible
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        print("\n" + "=" * 70)
        print("  (^_^) [OK] EXTRACCION COMPLETADA")
        print("=" * 70)
        print(f"  Archivo: {output_path.absolute()}")
        print(f"  Tamaño:  {output_path.stat().st_size:,} bytes")
        
        # Resumen rápido del contenido
        print(f"\n  [._.] [RESUMEN]")
        print(f"     Región:         {datos.get('region', 'N/A')}")
        print(f"     Estado:         {datos.get('estado', 'N/A')}")
        print(f"     Polinizadores:  {len(datos.get('polinizadores', []))}")
        print(f"     Cultivos:       {len(datos.get('cultivos', []))}")
        print(f"     Flora nativa:   {len(datos.get('flora_nativa', []))}")
        print(f"     Fuentes:        {len(datos.get('fuentes_consultadas', []))}")
        
        if errores:
            print(f"\n  (¬_¬) [ALERTA: ERRORES NO FATALES] ({len(errores)}):")
            for e in errores[:5]:  # Mostrar máximo 5
                print(f"     * {e}")
            if len(errores) > 5:
                print(f"     ... y {len(errores) - 5} más")
        
        print("=" * 70 + "\n")
        
    except json.JSONDecodeError as e:
        print(f"\n[X_X] [ALERTA: FORMATO JSON] {e}", file=sys.stderr)
        # Guardar el texto crudo de todos modos
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"  Texto crudo guardado en: {output_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
