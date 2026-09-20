"""
Módulo de introspección y descubrimiento dinámico de modelos de Groq.
Responsabilidad única (SRP): Consultar en vivo a la API de Groq los modelos disponibles
para la API Key configurada y proveer la lista de modelos utilizables.
"""
import os
import sys
import urllib.request
import json

# Asegurar que la raíz del proyecto esté en sys.path para ejecución directa
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from config.keys import GROQ_API_KEY
except ImportError:
    from keys import GROQ_API_KEY

FALLBACK_MODELS_GROQ = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
]


def obtener_modelos_groq() -> list[str]:
    """Consulta la API de Groq y retorna los IDs de los modelos disponibles.
    
    Returns:
        Lista de identificadores de modelos Groq (ej. ['llama-3.3-70b-versatile', ...]).
    """
    if not GROQ_API_KEY:
        return FALLBACK_MODELS_GROQ

    url = "https://api.groq.com/openai/v1/models"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {GROQ_API_KEY}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            modelos = [model["id"] for model in data.get("data", []) if "id" in model]
            # Ordenamos alfabéticamente para mayor legibilidad
            modelos.sort()
            return modelos if modelos else FALLBACK_MODELS_GROQ
    except Exception as e:
        print(f"[Aviso] No se pudo consultar la API de Groq en vivo ({e}). Usando lista de respaldo.")
        return FALLBACK_MODELS_GROQ


if __name__ == "__main__":
    print("=" * 60)
    print("CONSULTA DIRECTA A LA API DE GROQ")
    print("=" * 60)
    
    if not GROQ_API_KEY:
        print("ERROR: GROQ_API_KEY no encontrada en el entorno.")
        exit(1)

    print("\nModelos de Groq disponibles para tu cuenta:")
    modelos = obtener_modelos_groq()
    for m in modelos:
        print(f"  • {m}")
    print("=" * 60)
