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
import os

if COHERE_API_KEY:
    os.environ.setdefault("CO_API_KEY", COHERE_API_KEY)
    os.environ.setdefault("COHERE_API_KEY", COHERE_API_KEY)

# --- Constantes de modelos por defecto ---
GEMINI_FLASH = "gemini-flash-lite-latest"
GROQ_LLAMA3  = "qwen/qwen3.8-27b"
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


def _crear_fallbacks_cruzados(provider: str, model_name: str | None, temperature: float) -> list[BaseChatModel]:
    """Construye una lista jerarquica de modelos de respaldo entre proveedores
    (Gemini -> Groq -> Cohere -> Ollama Local) para garantizar tolerancia total a fallos
    (429 cuota excedida, 404 modelo retirado, intermitencia de red o apagon de APIs externas).
    """
    fallbacks: list[BaseChatModel] = []
    prov_lower = provider.strip().lower()

    # 1. Fallbacks del mismo proveedor si es Gemini
    if prov_lower in ("gemini", "google") and GEMINI_API_KEY:
        from langchain_google_genai import ChatGoogleGenerativeAI
        candidatos_gemini = ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.6-flash"]
        for cand in candidatos_gemini:
            if cand != model_name:
                try:
                    fallbacks.append(ChatGoogleGenerativeAI(
                        model=cand,
                        temperature=temperature,
                        google_api_key=GEMINI_API_KEY,
                    ))
                except Exception:
                    pass

    # 2. Fallbacks de Groq Cloud
    if prov_lower != "groq" and GROQ_API_KEY:
        try:
            from langchain_groq import ChatGroq
            for cand_groq in ("groq/compound", "openai/gpt-oss-120b", "qwen/qwen3.8-27b"):
                try:
                    fallbacks.append(ChatGroq(model=cand_groq, temperature=temperature))
                    break
                except Exception:
                    pass
        except Exception:
            pass

    # 3. Fallbacks de Cohere Command
    if prov_lower != "cohere" and COHERE_API_KEY:
        try:
            from langchain_cohere import ChatCohere
            for cand_cohere in ("command-r7b-12-2024", "command-r-08-2024"):
                try:
                    fallbacks.append(ChatCohere(model=cand_cohere, temperature=temperature, cohere_api_key=COHERE_API_KEY))
                    break
                except Exception:
                    pass
        except Exception:
            pass

    # 4. Fallback a Gemini si el proveedor principal era Groq o Cohere
    if prov_lower not in ("gemini", "google") and GEMINI_API_KEY:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            fallbacks.append(ChatGoogleGenerativeAI(
                model="gemini-flash-lite-latest",
                temperature=temperature,
                google_api_key=GEMINI_API_KEY,
            ))
        except Exception:
            pass

    # 5. Fallback 100% Local (Ollama) — Sin internet, sin cuotas de API ni costo
    try:
        from langchain_ollama import ChatOllama
        fallbacks.append(ChatOllama(model="llama3.1:latest", temperature=temperature))
    except Exception:
        pass

    return fallbacks


def get_llm(provider: str = "Gemini", model_name: str | None = None, temperature: float = 0.2) -> BaseChatModel:
    """Fabrica de LLMs con tolerancia cruzada a fallos y fallback local.
    Devuelve una instancia de chat model segun el proveedor con respaldo automatico.

    Proveedores soportados:
    - "Gemini":     Google Gemini (con fallback a Groq, Cohere y Ollama Local)
    - "Groq":       Groq Cloud (con fallback a Gemini, Cohere y Ollama Local)
    - "Cohere":     Cohere Command (con fallback a Gemini, Groq y Ollama Local)
    - "Ollama":     Ollama local — SIN internet, SIN costo (ej. llama3.1:latest)
    - "HuggingFace": HuggingFace Inference (requiere HF_TOKEN)
    """
    if provider == "Groq":
        from langchain_groq import ChatGroq
        if not GROQ_API_KEY:
            raise ValueError("Se requiere GROQ_API_KEY en .env para usar Groq.")
        primary = ChatGroq(model=model_name or GROQ_LLAMA3, temperature=temperature)
        fallbacks = _crear_fallbacks_cruzados("Groq", model_name or GROQ_LLAMA3, temperature)
        return primary.with_fallbacks(fallbacks) if fallbacks else primary

    elif provider == "Cohere":
        from langchain_cohere import ChatCohere
        if not COHERE_API_KEY:
            raise ValueError("Se requiere COHERE_API_KEY en .env para usar Cohere.")
        primary = ChatCohere(model=model_name or COHERE_CMD, temperature=temperature, cohere_api_key=COHERE_API_KEY)
        fallbacks = _crear_fallbacks_cruzados("Cohere", model_name or COHERE_CMD, temperature)
        return primary.with_fallbacks(fallbacks) if fallbacks else primary

    elif provider == "Ollama":
        from langchain_ollama import ChatOllama
        final_model = model_name or "llama3.1:latest"
        primary = ChatOllama(model=final_model, temperature=temperature)
        fallbacks = _crear_fallbacks_cruzados("Ollama", final_model, temperature)
        return primary.with_fallbacks(fallbacks) if fallbacks else primary

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
        fallbacks = _crear_fallbacks_cruzados("Gemini", m_name, temperature)
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



# ─────────────────────────────────────────────────────────────────────────────
# Configuracion por agente desde YAML — Hot-Reload sin reiniciar el proceso
# ─────────────────────────────────────────────────────────────────────────────

import os as _os
import yaml as _yaml

_CONFIG_YAML_PATH = _os.path.join(_os.path.dirname(__file__), "agentes.yaml")

_MODELOS_POR_AGENTE_DEFAULT: dict[str, dict] = {
    # ── Grupo Extractor ───────────────────────────────────────────────────────
    "mini_tavily":           {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.1},
    "mini_academico":        {"proveedor": "Cohere", "modelo": "command-r7b-12-2024",       "temperatura": 0.1},
    "mini_scraper":          {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.0},
    "mini_referencias_extractor": {"proveedor": "Cohere", "modelo": "command-r7b-12-2024",  "temperatura": 0.1},
    "descargador":           {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.1},
    "fusionador_extractor":  {"proveedor": "Gemini", "modelo": "gemini-3.5-flash-lite",    "temperatura": 0.0},
    # ── Grupo Agronomo ────────────────────────────────────────────────────────
    "mini_suelo":            {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.2},
    "mini_cultivo":          {"proveedor": "Gemini", "modelo": "gemini-3.5-flash-lite",    "temperatura": 0.2},
    "mini_siap":             {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.0},
    "mini_inegi_agro":       {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.1},
    "mini_calculadora":      {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.0},
    "mini_rotacion_regenerativa": {"proveedor": "Gemini", "modelo": "gemini-3.5-flash-lite", "temperatura": 0.2},
    "mini_referencias":      {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.1},
    "mini_referencias_agronomo": {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.1},
    "fusionador_agronomo":   {"proveedor": "Gemini", "modelo": "gemini-3.5-flash-lite",    "temperatura": 0.0},
    # ── Grupo Ecologico ───────────────────────────────────────────────────────
    "mini_flora_nativa":     {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.2},
    "mini_polinizadores":    {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.2},
    "mini_catalogo_local":   {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.1},
    "mini_gbif":             {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.0},
    "mini_control_biologico":{"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.2},
    "mini_atractores_polinizadores": {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.2},
    "mini_referencias_ecologico": {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.1},
    "fusionador_ecologico":  {"proveedor": "Gemini", "modelo": "gemini-3.5-flash-lite",    "temperatura": 0.0},
    # ── Grupo 3D ──────────────────────────────────────────────────────────────
    "fusionador_3d":         {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.0},
    "estructurador":         {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.0},
    "mini_referencias_3d":   {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.1},
    "validador_3d":          {"proveedor": "Gemini", "modelo": "gemini-flash-lite-latest", "temperatura": 0.0},
    # ── Supervisor Maestro ────────────────────────────────────────────────────
    "supervisor":            {"proveedor": "Gemini", "modelo": "gemini-3.5-flash-lite",    "temperatura": 0.1},
    # ── Sintetizador y Resumen Ejecutivo ──────────────────────────────────────
    "agente_sintetizador":   {"proveedor": "Gemini", "modelo": "gemini-3.5-flash-lite",    "temperatura": 0.1},
}



_last_yaml_mtime: float = 0.0


def cargar_config_agentes() -> dict:
    """Carga la configuracion de agentes desde config/agentes.yaml con hot-reload.
    Si detecta un cambio manual en el archivo, dispara la regeneracion de diagramas.
    """
    global _last_yaml_mtime

    if not _os.path.exists(_CONFIG_YAML_PATH):
        datos = {
            "modelos": _MODELOS_POR_AGENTE_DEFAULT,
            "configuracion": {
                "max_ciclos_retroalimentacion": 3,
                "confirmacion_descarga": "manual",
                "flow_type": "Hibrido",
                "activar_3d_automatico": False,
                "max_iteraciones_supervisor": 3,
            },
        }
        with open(_CONFIG_YAML_PATH, "w", encoding="utf-8") as _f:
            _yaml.dump(datos, _f, allow_unicode=True, sort_keys=False)

    try:
        current_mtime = _os.path.getmtime(_CONFIG_YAML_PATH)
        if _last_yaml_mtime > 0 and current_mtime != _last_yaml_mtime:
            _last_yaml_mtime = current_mtime
            try:
                from scripts.generar_diagrama_v3 import disparar_actualizacion_diagramas
                disparar_actualizacion_diagramas(async_mode=True)
            except Exception:
                pass
        else:
            _last_yaml_mtime = current_mtime

        with open(_CONFIG_YAML_PATH, "r", encoding="utf-8") as _f:
            return _yaml.safe_load(_f) or {}
    except Exception:
        return {"modelos": _MODELOS_POR_AGENTE_DEFAULT, "configuracion": {}}


_vigilante_iniciado = False


def iniciar_vigilante_agentes(intervalo_segundos: float = 2.0):
    """Inicia un hilo en segundo plano que vigila config/agentes.yaml.
    Cada vez que se actualiza o guarda el archivo de agentes, dispara
    automaticamente la generacion y guardado de las arquitecturas por cada subgrafo
    y del enjambre en formato imagen PNG.
    """
    global _vigilante_iniciado
    if _vigilante_iniciado:
        return
    _vigilante_iniciado = True

    import time
    import threading

    def _loop_vigilante():
        global _last_yaml_mtime
        while True:
            time.sleep(intervalo_segundos)
            if _os.path.exists(_CONFIG_YAML_PATH):
                try:
                    mtime = _os.path.getmtime(_CONFIG_YAML_PATH)
                    if _last_yaml_mtime > 0 and mtime != _last_yaml_mtime:
                        _last_yaml_mtime = mtime
                        from scripts.generar_diagrama_v3 import disparar_actualizacion_diagramas
                        disparar_actualizacion_diagramas(async_mode=True)
                    elif _last_yaml_mtime == 0.0:
                        _last_yaml_mtime = mtime
                except Exception:
                    pass

    t = threading.Thread(target=_loop_vigilante, name="AgentesConfigWatcher", daemon=True)
    t.start()


# Mapa de capacidad: qué modelos preferir por proveedor cuando hay que hacer fallback
_GROQ_FALLBACK_CHAIN = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "groq/compound",
    "groq/compound-mini",
]
_GEMINI_FALLBACK_CHAIN = [
    "gemini-flash-lite-latest",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.6-flash",
    "gemini-flash-latest",
]
_COHERE_FALLBACK_CHAIN = [
    "command-r7b-12-2024",
    "command-r-08-2024",
    "command-r-plus-08-2024",
    "c4ai-aya-expanse-32b",
]

# Cache de modelos verificados para no consultar la API en cada llamada
_modelos_groq_verificados: list[str] | None = None
_modelos_gemini_verificados: list[str] | None = None
_modelos_cohere_verificados: list[str] | None = None


def _obtener_primer_modelo_disponible(proveedor: str, preferidos: list[str]) -> str:
    """Consulta la API del proveedor y retorna el primer modelo de la lista 'preferidos'
    que este efectivamente disponible. Si ninguno esta en la lista live, retorna el primero
    de 'preferidos' como ultimo recurso (puede fallar pero al menos lo intenta).
    """
    global _modelos_groq_verificados, _modelos_gemini_verificados, _modelos_cohere_verificados

    try:
        if proveedor.lower() == "groq":
            if _modelos_groq_verificados is None:
                from config.models_groq import obtener_modelos_groq
                _modelos_groq_verificados = obtener_modelos_groq()
            disponibles = _modelos_groq_verificados
        elif proveedor.lower() == "gemini":
            if _modelos_gemini_verificados is None:
                from config.models_gemini import obtener_modelos_gemini
                _modelos_gemini_verificados = obtener_modelos_gemini(tipo="chat")
            disponibles = _modelos_gemini_verificados
        elif proveedor.lower() == "cohere":
            if _modelos_cohere_verificados is None:
                from config.models_cohere import obtener_modelos_cohere
                _modelos_cohere_verificados = obtener_modelos_cohere(tipo="chat")
            disponibles = _modelos_cohere_verificados
        else:
            return preferidos[0]

        for modelo in preferidos:
            if modelo in disponibles:
                return modelo
        # Si ninguno esta en la lista live, usar el primero de los disponibles
        # que coincida con la capacidad buscada (grande o pequeno)
        return disponibles[0] if disponibles else preferidos[0]
    except Exception:
        return preferidos[0]


def get_llm_para_agente(nombre_agente: str) -> "BaseChatModel":
    """Retorna el LLM configurado para el agente segun config/agentes.yaml (hot-reload).
    Si el modelo configurado no esta disponible (404, decomisionado, 429 cuota excedida o falla de red),
    consulta la API en vivo mediante introspeccion dinamica (models_gemini.py, models_groq.py, models_cohere.py)
    y, en caso necesario, conmuta automaticamente a otro proveedor o a ejecucion 100% local en Ollama.
    """
    from config.agri_logger import log_info, log_alerta, log_error

    config = cargar_config_agentes()
    modelos = config.get("modelos", {})
    cfg = modelos.get(nombre_agente, _MODELOS_POR_AGENTE_DEFAULT.get(nombre_agente, {}))
    proveedor   = cfg.get("proveedor",   "Gemini")
    modelo      = cfg.get("modelo",      None)
    temperatura = float(cfg.get("temperatura", 0.1))

    # Intentar con el modelo configurado
    try:
        return get_llm(provider=proveedor, model_name=modelo, temperature=temperatura)
    except Exception as e_primario:
        log_alerta(
            f"Agente '{nombre_agente}': no se pudo inicializar '{modelo}' ({proveedor}): {e_primario}. "
            f"Iniciando introspeccion dinamica de modelos en vivo...",
            kaomoji="(-_-;)",
        )

        # 1. Intentar descubrir un modelo activo del mismo proveedor
        try:
            if proveedor.lower() in ("gemini", "google"):
                from config.models_gemini import obtener_modelos_gemini
                modelos_live = obtener_modelos_gemini(tipo="chat")
            elif proveedor.lower() == "groq":
                from config.models_groq import obtener_modelos_groq
                modelos_live = obtener_modelos_groq()
            elif proveedor.lower() == "cohere":
                from config.models_cohere import obtener_modelos_cohere
                modelos_live = obtener_modelos_cohere(tipo="chat")
            else:
                modelos_live = []

            for cand in modelos_live:
                if cand != modelo:
                    try:
                        llm_alt = get_llm(provider=proveedor, model_name=cand, temperature=temperatura)
                        log_info(
                            f"Agente '{nombre_agente}': recuperado con modelo en vivo '{cand}' ({proveedor}).",
                            kaomoji="(^_^)/",
                        )
                        return llm_alt
                    except Exception:
                        continue
        except Exception as e_live:
            log_error(f"Introspeccion dinamica para {proveedor} fallo: {e_live}", kaomoji="[X_X]")

        # 2. Conmutar a proveedores alternativos con credenciales (Gemini, Groq, Cohere)
        orden_proveedores = ["Gemini", "Groq", "Cohere"]
        for alt_prov in orden_proveedores:
            if alt_prov.lower() != proveedor.lower():
                try:
                    log_info(f"Agente '{nombre_agente}': conmutando a proveedor alternativo '{alt_prov}'...", kaomoji="[._.]")
                    return get_llm(provider=alt_prov, temperature=temperatura)
                except Exception:
                    continue

        # 3. Respaldo final garantizado 100% Local (Ollama)
        try:
            log_alerta(f"Agente '{nombre_agente}': activando fallback 100% local en Ollama (llama3.1:latest)...", kaomoji="[O_O]")
            from langchain_ollama import ChatOllama
            return ChatOllama(model="llama3.1:latest", temperature=temperatura)
        except Exception as e_local:
            log_error(f"Fallo critico en todos los respaldos para '{nombre_agente}': {e_local}", kaomoji="[X_X]")
            raise e_primario


def actualizar_config_agente(
    nombre_agente: str,
    proveedor: str | None = None,
    modelo: str | None = None,
    temperatura: float | None = None,
) -> bool:
    """Actualiza en caliente config/agentes.yaml para el agente indicado.
    Usado por el CLI con /model <agente> <modelo> y /provider <agente> <proveedor>.
    """
    try:
        config = cargar_config_agentes()
        if "modelos" not in config:
            config["modelos"] = {}
        if nombre_agente not in config["modelos"]:
            config["modelos"][nombre_agente] = dict(
                _MODELOS_POR_AGENTE_DEFAULT.get(nombre_agente, {})
            )
        if proveedor is not None:
            config["modelos"][nombre_agente]["proveedor"] = proveedor
        if modelo is not None:
            config["modelos"][nombre_agente]["modelo"] = modelo
        if temperatura is not None:
            config["modelos"][nombre_agente]["temperatura"] = temperatura
        with open(_CONFIG_YAML_PATH, "w", encoding="utf-8") as _f:
            _yaml.dump(config, _f, allow_unicode=True, sort_keys=False)

        global _last_yaml_mtime
        try:
            _last_yaml_mtime = _os.path.getmtime(_CONFIG_YAML_PATH)
            from scripts.generar_diagrama_v3 import disparar_actualizacion_diagramas
            disparar_actualizacion_diagramas(async_mode=True)
        except Exception:
            pass

        return True
    except Exception:
        return False
