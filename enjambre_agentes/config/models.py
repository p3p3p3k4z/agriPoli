"""
Fábrica de LLMs y Embeddings agnóstica al proveedor para el Sistema Multiagente AgriPoli.

Soporta ejecución LOCAL (Ollama, HuggingFace) y EN LA NUBE (Gemini, Groq, Cohere).
Adaptado y extendido del patrón de OptiAgent/my_models.py.
"""
from __future__ import annotations
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from config.keys import GEMINI_API_KEY, GROQ_API_KEY, COHERE_API_KEY, HF_TOKEN

# --- Constantes de modelos por defecto ---
GEMINI_FLASH = "gemini-flash-latest"
GROQ_LLAMA3  = "llama-3.3-70b-versatile"
COHERE_CMD   = "command-r7b-12-2024"
OLLAMA_DEFAULT = "llama3.2"  # Modelo local por defecto si se tiene Ollama instalado


def extraer_texto_mensaje(content: Any) -> str:
    """Extrae texto limpio de la respuesta de un modelo de lenguaje.
    
    Maneja tanto strings directos como estructuras anidadas de la nueva API de Google GenAI
    (listas de diccionarios [{'type': 'text', 'text': ...}]).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        partes = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and "text" in item:
                    partes.append(str(item["text"]))
                elif "text" in item:
                    partes.append(str(item["text"]))
            elif isinstance(item, str):
                partes.append(item)
        return "\n".join(partes) if partes else str(content)
    if isinstance(content, dict):
        return str(content.get("text", content.get("content", str(content))))
    return str(content) if content is not None else ""

# Dimensiones de embeddings por proveedor/modelo
EMBEDDING_MODELS_INFO: dict[str, dict[str, int]] = {
    "Gemini": {
        "models/gemini-embedding-001": 768,
        "models/embedding-001": 768,
    },
    "HuggingFace": {
        "intfloat/multilingual-e5-small": 384,
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2": 384,
        "sentence-transformers/all-MiniLM-L6-v2": 384,
        "BAAI/bge-m3": 1024,
        "intfloat/multilingual-e5-base": 768,
    },
    "Ollama": {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
    }
}

# Proveedores disponibles
PROVIDERS = ["Gemini", "Groq", "Cohere", "Ollama", "HuggingFace"]


def get_llm(provider: str = "Gemini", model_name: str | None = None, temperature: float = 0.2) -> BaseChatModel:
    """Fábrica de LLMs. Devuelve una instancia de chat model según el proveedor.

    Proveedores soportados:
    - "Gemini":     Google Gemini (requiere GEMINI_API_KEY)
    - "Groq":       Groq Cloud, Llama3 ultrarrápido (requiere GROQ_API_KEY)
    - "Cohere":     Cohere Command (requiere COHERE_API_KEY)
    - "Ollama":     Ollama local — SIN internet, SIN costo (requiere `ollama serve`)
    - "HuggingFace": HuggingFace Inference (requiere HF_TOKEN)

    Args:
        provider:    Nombre del proveedor.
        model_name:  Modelo específico. Si es None, usa el default del proveedor.
        temperature: Temperatura de generación (0.0 - 1.0).
    """
    if provider == "Groq":
        from langchain_groq import ChatGroq
        if not GROQ_API_KEY:
            raise ValueError("Se requiere GROQ_API_KEY en .env para usar Groq.")
        return ChatGroq(model=model_name or GROQ_LLAMA3, temperature=temperature)

    elif provider == "Cohere":
        from langchain_cohere import ChatCohere
        if not COHERE_API_KEY:
            raise ValueError("Se requiere COHERE_API_KEY en .env para usar Cohere.")
        return ChatCohere(model=model_name or COHERE_CMD, temperature=temperature)

    elif provider == "Ollama":
        # Ejecución 100% local — requiere `ollama serve` corriendo en background
        from langchain_ollama import ChatOllama
        final_model = model_name or OLLAMA_DEFAULT
        print(f"[models] Usando Ollama LOCAL: {final_model} (sin internet ni API key)")
        return ChatOllama(model=final_model, temperature=temperature)

    elif provider == "HuggingFace":
        from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
        if not HF_TOKEN:
            raise ValueError("Se requiere HF_TOKEN en .env para usar HuggingFace.")
        endpoint = HuggingFaceEndpoint(
            repo_id=model_name or "mistralai/Mistral-7B-Instruct-v0.2",
            huggingfacehub_api_token=HF_TOKEN,
            temperature=temperature,
        )
        return ChatHuggingFace(llm=endpoint)

    else:
        # Defecto: Google Gemini
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not GEMINI_API_KEY:
            raise ValueError("Se requiere GEMINI_API_KEY en .env para usar Gemini.")
        
        m_name = model_name or GEMINI_FLASH
        primary = ChatGoogleGenerativeAI(
            model=m_name,
            temperature=temperature,
            google_api_key=GEMINI_API_KEY,
        )
        
        # Fallbacks automáticos entre versiones de Gemini para tolerancia a cuota y límites de tasa (429)
        candidatos = ["gemini-flash-latest", "gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-3.7-flash"]
        fallbacks = [
            ChatGoogleGenerativeAI(
                model=cand,
                temperature=temperature,
                google_api_key=GEMINI_API_KEY,
            )
            for cand in candidatos if cand != m_name
        ]
        return primary.with_fallbacks(fallbacks) if fallbacks else primary


def get_embeddings_model(provider: str = "Gemini", model_name: str | None = None) -> Embeddings:
    """Fábrica de modelos de embeddings.

    Proveedores:
    - "Gemini":      Google Embeddings (nube)
    - "HuggingFace": Sentence-Transformers (local, sin API)
    - "Ollama":      Ollama Embeddings (local, sin API)

    Args:
        provider:   Proveedor del modelo.
        model_name: Nombre del modelo. Si es None usa el primero del proveedor.
    """
    if not model_name:
        models_dict = EMBEDDING_MODELS_INFO.get(provider, {})
        model_name = list(models_dict.keys())[0] if models_dict else None

    if provider == "HuggingFace":
        from langchain_huggingface import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(model_name=model_name)

    elif provider == "Ollama":
        from langchain_ollama import OllamaEmbeddings
        print(f"[models] Embeddings Ollama LOCAL: {model_name}")
        return OllamaEmbeddings(model=model_name or "nomic-embed-text")

    else:
        # Defecto: Gemini
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        if not GEMINI_API_KEY:
            raise ValueError("Se requiere GEMINI_API_KEY en .env para embeddings Gemini.")
        return GoogleGenerativeAIEmbeddings(
            model=model_name or "models/gemini-embedding-001",
            google_api_key=GEMINI_API_KEY,
        )


def get_available_providers() -> list[str]:
    """Devuelve la lista de proveedores con sus keys configuradas."""
    disponibles = []
    if GEMINI_API_KEY:
        disponibles.append("Gemini")
    if GROQ_API_KEY:
        disponibles.append("Groq")
    if COHERE_API_KEY:
        disponibles.append("Cohere")
    if HF_TOKEN:
        disponibles.append("HuggingFace")
    # Ollama siempre aparece (no requiere key, solo el servicio local)
    disponibles.append("Ollama")
    return disponibles


def obtener_modelos_disponibles(provider: str) -> list[str]:
    """Descubre dinámicamente los modelos disponibles para el proveedor especificado,
    delegando a los módulos especializados de introspección (SRP: models_*).
    
    Args:
        provider: 'Gemini', 'Groq', 'Cohere', 'Ollama', o 'HuggingFace'.
        
    Returns:
        Lista de nombres de modelos listos para ser configurados en el agente.
    """
    prov_lower = provider.strip().lower()
    
    if prov_lower in ("gemini", "google"):
        try:
            from config.models_gemini import obtener_modelos_gemini
            return obtener_modelos_gemini(tipo="chat")
        except Exception:
            return ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-1.5-pro"]
            
    elif prov_lower == "groq":
        try:
            from config.models_groq import obtener_modelos_groq
            return obtener_modelos_groq()
        except Exception:
            return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
            
    elif prov_lower == "cohere":
        try:
            from config.models_cohere import obtener_modelos_cohere
            return obtener_modelos_cohere(tipo="chat")
        except Exception:
            return ["command-r7b-12-2024", "command-r-plus", "command-r"]
            
    elif prov_lower == "ollama":
        try:
            import ollama
            res = ollama.list()
            # ollama.list() retorna modelos instalados localmente
            modelos_locales = [m.model for m in res.models] if hasattr(res, 'models') else []
            if modelos_locales:
                return modelos_locales
        except Exception:
            pass
        return ["llama3.2", "mistral", "gemma2", "deepseek-r1"]
        
    elif prov_lower == "huggingface":
        return [
            "mistralai/Mistral-7B-Instruct-v0.3",
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "microsoft/Phi-3-mini-4k-instruct",
        ]
        
    return []

