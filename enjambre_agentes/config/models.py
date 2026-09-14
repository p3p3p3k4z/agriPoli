"""
Fábrica de LLMs y Embeddings agnóstica al proveedor para AniIta.

Soporta intercambio transparente entre Google Gemini, Groq y Cohere.
Adaptado del patrón de OptiAgent/my_models.py sin dependencias de Streamlit.
"""
from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from config.keys import GEMINI_API_KEY, GROQ_API_KEY, COHERE_API_KEY

# --- Constantes de modelos por defecto ---
GEMINI_FLASH = "gemini-3.5-flash-lite"
GROQ_LLAMA3 = "llama-3.3-70b-versatile"
COHERE_COMMAND = "command-r7b-12-2024"

# Dimensiones de embeddings por proveedor/modelo
EMBEDDING_MODELS_INFO: dict[str, dict[str, int]] = {
    "Gemini": {
        "models/gemini-embedding-001": 768,
    },
    "HuggingFace": {
        "intfloat/multilingual-e5-small": 384,
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
    },
}


def get_llm(provider: str = "Gemini", model_name: str | None = None, temperature: float = 0.2) -> BaseChatModel:
    """Fábrica de LLMs. Devuelve una instancia de chat model según el proveedor.
    
    Args:
        provider: "Gemini", "Groq" o "Cohere".
        model_name: Nombre específico del modelo. Si es None, usa el default del proveedor.
        temperature: Temperatura de generación (0.0 - 1.0).
        
    Returns:
        Instancia de BaseChatModel configurada.
        
    Raises:
        ValueError: Si falta la API key del proveedor seleccionado.
    """
    if provider == "Groq":
        from langchain_groq import ChatGroq
        if not GROQ_API_KEY:
            raise ValueError("Se requiere GROQ_API_KEY en .env para usar Groq.")
        final_model = model_name or GROQ_LLAMA3
        return ChatGroq(model=final_model, temperature=temperature)
    
    elif provider == "Cohere":
        from langchain_cohere import ChatCohere
        if not COHERE_API_KEY:
            raise ValueError("Se requiere COHERE_API_KEY en .env para usar Cohere.")
        final_model = model_name or COHERE_COMMAND
        return ChatCohere(model=final_model, temperature=temperature)
    
    else:
        # Por defecto: Google Gemini
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not GEMINI_API_KEY:
            raise ValueError("Se requiere GEMINI_API_KEY en .env para usar Gemini.")
        final_model = model_name or GEMINI_FLASH
        return ChatGoogleGenerativeAI(
            model=final_model,
            temperature=temperature,
            google_api_key=GEMINI_API_KEY,
        )


def get_embeddings_model(provider: str = "Gemini", model_name: str | None = None) -> Embeddings:
    """Fábrica de modelos de embeddings para vectorización.
    
    Args:
        provider: "Gemini" o "HuggingFace".
        model_name: Nombre específico del modelo. Si es None, usa el primero del proveedor.
        
    Returns:
        Instancia de Embeddings configurada.
    """
    if not model_name:
        model_name = list(EMBEDDING_MODELS_INFO[provider].keys())[0]

    if provider == "HuggingFace":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=model_name)
    else:
        # Por defecto: Gemini
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        if not GEMINI_API_KEY:
            raise ValueError("Se requiere GEMINI_API_KEY en .env para embeddings Gemini.")
        return GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=GEMINI_API_KEY,
        )
