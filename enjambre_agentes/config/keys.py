"""
Gestión centralizada de API keys para AniIta.
Carga las variables de entorno desde el archivo .env en la raíz del proyecto.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto AniIta
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")

# --- API Keys de Proveedores LLM ---
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY: str | None = os.getenv("TAVILY_API_KEY")
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
COHERE_API_KEY: str | None = os.getenv("COHERE_API_KEY")
INEGI_API_TOKEN: str | None = os.getenv("INEGI_API_TOKEN")


def validate_keys(*required_keys: str) -> None:
    """Valida que las API keys requeridas estén presentes en el entorno.
    
    Args:
        *required_keys: Nombres de las variables a validar (ej. "GEMINI_API_KEY").
        
    Raises:
        ValueError: Si alguna key requerida falta o está vacía.
    """
    key_map = {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "TAVILY_API_KEY": TAVILY_API_KEY,
        "GROQ_API_KEY": GROQ_API_KEY,
        "COHERE_API_KEY": COHERE_API_KEY,
    }
    missing = [k for k in required_keys if not key_map.get(k)]
    if missing:
        raise ValueError(
            f"Faltan las siguientes API keys en el archivo .env: {', '.join(missing)}. "
            f"Copia .env.example a .env y rellena los valores."
        )
