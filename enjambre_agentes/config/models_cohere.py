"""
Módulo de introspección y descubrimiento dinámico de modelos de Cohere.
Responsabilidad única (SRP): Consultar en vivo a la API de Cohere los modelos disponibles
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
    from config.keys import COHERE_API_KEY
except ImportError:
    from keys import COHERE_API_KEY

FALLBACK_MODELS_COHERE = [
    "command-r-plus-08-2024",
    "command-r-plus",
    "command-r-08-2024",
    "command-r",
    "command-light",
]


def obtener_modelos_cohere(tipo: str = "chat") -> list[str]:
    """Consulta la API de Cohere y retorna los modelos disponibles.
    
    Args:
        tipo: 'chat' (modelos con endpoint chat), 'embed' (con endpoint embed) o 'todos'.
        
    Returns:
        Lista de nombres de modelos (ej. ['command-r-plus', ...]).
    """
    if not COHERE_API_KEY:
        return FALLBACK_MODELS_COHERE

    url = "https://api.cohere.com/v1/models"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {COHERE_API_KEY}")
    req.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            modelos = []
            for model in data.get("models", []):
                endpoints = model.get("endpoints", [])
                nombre = model.get("name", "")
                if tipo == "chat" and "chat" in endpoints:
                    modelos.append(nombre)
                elif tipo == "embed" and "embed" in endpoints:
                    modelos.append(nombre)
                elif tipo == "todos":
                    modelos.append(nombre)
            modelos.sort()
            return modelos if modelos else FALLBACK_MODELS_COHERE
    except Exception as e:
        print(f"[Aviso] No se pudo consultar la API de Cohere en vivo ({e}). Usando lista de respaldo.")
        return FALLBACK_MODELS_COHERE


if __name__ == "__main__":
    print("=" * 60)
    print("CONSULTA DIRECTA A LA API DE COHERE")
    print("=" * 60)
    
    if not COHERE_API_KEY:
        print("ERROR: COHERE_API_KEY no encontrada en el entorno.")
        exit(1)

    print("\nModelos de Cohere disponibles para Chat:")
    modelos = obtener_modelos_cohere(tipo="chat")
    for m in modelos:
        print(f"  • {m}")
    print("=" * 60)
