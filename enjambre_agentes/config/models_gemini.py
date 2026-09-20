"""
Módulo de introspección y descubrimiento dinámico de modelos de Google Gemini.
Responsabilidad única (SRP): Consultar en vivo a la API de Google los modelos disponibles
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
    from config.keys import GEMINI_API_KEY
except ImportError:
    from keys import GEMINI_API_KEY

FALLBACK_MODELS_GEMINI = [
    "gemini-3.6-flash",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]


def obtener_modelos_gemini(tipo: str = "chat") -> list[str]:
    """Consulta la API de Google Generative Language y retorna los modelos disponibles.
    
    Args:
        tipo: 'chat' (modelos con generateContent), 'embedding' (embedContent) o 'todos'.
        
    Returns:
        Lista de nombres de modelos (ej. ['gemini-3.6-flash', ...]).
    """
    if not GEMINI_API_KEY:
        return FALLBACK_MODELS_GEMINI

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={GEMINI_API_KEY}"
    req = urllib.request.Request(url)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            modelos = []
            for model in data.get("models", []):
                methods = model.get("supportedGenerationMethods", [])
                nombre = model.get("name", "").replace("models/", "")
                if tipo == "chat" and "generateContent" in methods:
                    modelos.append(nombre)
                elif tipo == "embedding" and "embedContent" in methods:
                    modelos.append(nombre)
                elif tipo == "todos":
                    modelos.append(nombre)
            return modelos if modelos else FALLBACK_MODELS_GEMINI
    except Exception as e:
        print(f"[Aviso] No se pudo consultar la API de Google en vivo ({e}). Usando lista de respaldo.")
        return FALLBACK_MODELS_GEMINI


if __name__ == "__main__":
    print("=" * 60)
    print("CONSULTA DIRECTA A LA API DE GOOGLE GEMINI")
    print("=" * 60)
    
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY no encontrada en el entorno.")
        exit(1)

    print("\nModelos disponibles para generación de texto (Chat):")
    modelos_chat = obtener_modelos_gemini(tipo="chat")
    for m in modelos_chat:
        print(f"  • {m}")

    print("\nModelos disponibles para Embeddings:")
    modelos_emb = obtener_modelos_gemini(tipo="embedding")
    for m in modelos_emb:
        print(f"  • {m}")
    print("=" * 60)
