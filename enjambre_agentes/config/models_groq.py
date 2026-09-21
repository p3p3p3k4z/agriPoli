"""
Módulo de introspección y descubrimiento dinámico de modelos de Groq.
Responsabilidad única (SRP): Consultar en vivo a la API de Groq los modelos disponibles
para la API Key configurada y proveer la lista de modelos utilizables.
"""
import os
import sys
import json
import urllib.request

# Asegurar que la raíz del proyecto esté en sys.path para ejecución directa
_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from config.keys import GROQ_API_KEY
except ImportError:
    from keys import GROQ_API_KEY

FALLBACK_MODELS_GROQ = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "groq/compound",
    "groq/compound-mini",
]


def obtener_modelos_groq() -> list[str]:
    """Consulta la API de Groq y retorna los IDs de los modelos disponibles.
    
    Returns:
        Lista de identificadores de modelos Groq (ej. ['qwen/qwen3.8-27b', ...]).
    """
    if not GROQ_API_KEY:
        return FALLBACK_MODELS_GROQ

    # Intento 1: SDK oficial de Groq si está instalado
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        lista = client.models.list()
        modelos = [m.id for m in lista.data if hasattr(m, "id")]
        # Filtrar modelos que no sean de audio/guard
        modelos_chat = [m for m in modelos if "whisper" not in m and "guard" not in m]
        if modelos_chat:
            modelos_chat.sort()
            return modelos_chat
    except Exception:
        pass

    # Intento 2: Solicitud HTTP directa con User-Agent para evitar bloqueo 403 de Cloudflare
    url = "https://api.groq.com/openai/v1/models"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Accept": "application/json",
            "User-Agent": "AgriPoli/1.0 (Linux; x86_64)",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            modelos = [
                model["id"] for model in data.get("data", [])
                if "id" in model and "whisper" not in model["id"] and "guard" not in model["id"]
            ]
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
