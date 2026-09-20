"""
Motor RAG Híbrido para el Sistema Multiagente AgriPoli.

Soporta tres backends de vectorstore:
  - FAISS   → Disco local, ultra-rápido, sin internet. (por defecto)
  - Pinecone → Nube, persistente entre sesiones y máquinas.
  - ChromaDB → Colecciones locales persistentes (legado).

Inspirado en OptiAgent/rag_core.py, adaptado para colecciones
temáticas agrícolas/ecológicas con fallback robusto de chunking.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from langchain_core.vectorstores import VectorStoreRetriever
from langchain_core.documents import Document

from config.models import get_embeddings_model, EMBEDDING_MODELS_INFO
from config.keys import PINECONE_API_KEY

# Directorio base para índices locales
_BASE_DIR = Path(__file__).resolve().parent.parent / "data" / "vectorstores"

# Caché global de retrievers por (colección, proveedor, db_type)
_retriever_cache: dict[str, VectorStoreRetriever] = {}

# Colecciones temáticas estructuradas
COLLECTIONS = {
    "suelo":         "Estudios edafológicos, texturas, pH, retención de humedad, degradación y nutrientes",
    "agricultura":   "Manuales agrícolas, rotación de cultivos, prácticas de labranza y fertilización",
    "polinizadores": "Especies polinizadoras, flora melífera, apicultura y conservación de abejas nativas",
    "general":       "Guías agroecológicas generales, normativas mexicanas y documentos multidisciplinarios",
}

# Aliases de compatibilidad con versiones previas
COLECCION_ALIASES = {
    "manuales_agricolas": "agricultura",
    "flora_botanica": "polinizadores",
    "publicaciones_cientificas": "general",
}


def normalizar_coleccion(nombre: str) -> str:
    """Normaliza el nombre de una colección para mapear a las 4 carpetas estándar."""
    return COLECCION_ALIASES.get(nombre.strip().lower(), nombre.strip().lower())


def _chunk_documents(docs: list[Document], embeddings, fallback_chunk_size: int = 1500) -> list[Document]:
    """
    Fragmenta documentos con RecursiveCharacterTextSplitter de tamaño óptimo (1500 caracteres)
    para minimizar llamadas a la API de embeddings y evitar límites de cuota (429).
    """
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=fallback_chunk_size, chunk_overlap=150
    )
    chunks = splitter.split_documents(docs)
    print(f"[RAG] Fragmentado en {len(chunks)} fragmentos.")
    return chunks


def build_vectorstore(
    collection_name: str = "general",
    provider: str = "Gemini",
    db_type: Literal["FAISS", "Pinecone", "ChromaDB"] = "FAISS",
    embedding_model: str | None = None,
    force_rebuild: bool = False,
) -> VectorStoreRetriever | None:
    """
    Construye o carga un índice vectorial.

    Args:
        collection_name: Una de las colecciones en COLLECTIONS ('suelo', 'agricultura', 'polinizadores', 'general').
        provider:        Proveedor de embeddings ("Gemini", "HuggingFace", "Ollama").
        db_type:         Backend de vectorstore ("FAISS", "Pinecone", "ChromaDB").
        embedding_model: Modelo específico de embeddings. None = default del proveedor.
        force_rebuild:   Si True, borra y reconstruye el índice aunque exista.
    """
    collection_name = normalizar_coleccion(collection_name)
    cache_key = f"{collection_name}:{provider}:{db_type}"
    if cache_key in _retriever_cache and not force_rebuild:
        return _retriever_cache[cache_key]

    embeddings = get_embeddings_model(provider=provider, model_name=embedding_model)

    if db_type == "Pinecone":
        retriever = _build_pinecone(collection_name, embeddings, embedding_model, provider, force_rebuild)
    elif db_type == "ChromaDB":
        retriever = _build_chroma(collection_name, embeddings, force_rebuild)
    else:
        retriever = _build_faiss(collection_name, embeddings, provider, force_rebuild)

    if retriever:
        _retriever_cache[cache_key] = retriever
    return retriever


def _build_faiss(collection_name: str, embeddings, provider: str, force_rebuild: bool) -> VectorStoreRetriever | None:
    """Backend FAISS: índice local en disco, ultra-rápido con tolerancia a 429."""
    from langchain_community.vectorstores import FAISS

    index_path = _BASE_DIR / "faiss" / f"{collection_name}_{provider.lower()}"
    index_path.mkdir(parents=True, exist_ok=True)
    index_file = index_path / "index.faiss"

    if index_file.exists() and not force_rebuild:
        print(f"[RAG/FAISS] Cargando indice '{collection_name}' ({provider}) desde disco...")
        try:
            vs = FAISS.load_local(str(index_path), embeddings, allow_dangerous_deserialization=True)
            print(f"[RAG/FAISS] Indice cargado exitosamente.")
            return vs.as_retriever(search_kwargs={"k": 5})
        except Exception as e:
            print(f"[RAG/FAISS] Error cargando indice: {e}. Reconstruyendo...")

    docs = _load_documents_for_collection(collection_name)
    if not docs:
        print(f"[RAG/FAISS] Sin documentos para la coleccion '{collection_name}'.")
        return None

    chunks = _chunk_documents(docs, embeddings)
    
    try:
        vs = FAISS.from_documents(chunks, embeddings)
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print(f"[RAG/FAISS] Cuota de embeddings remota excedida ({e}). Activando fallback local HuggingFace (sin límite)...")
            from langchain_huggingface import HuggingFaceEmbeddings
            local_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
            index_path = _BASE_DIR / "faiss" / f"{collection_name}_local_hf"
            index_path.mkdir(parents=True, exist_ok=True)
            vs = FAISS.from_documents(chunks, local_embeddings)
        else:
            raise e

    vs.save_local(str(index_path))
    print(f"[RAG/FAISS] Indice guardado en: {index_path}")
    return vs.as_retriever(search_kwargs={"k": 5})


def _build_pinecone(collection_name: str, embeddings, embedding_model: str | None, provider: str, force_rebuild: bool) -> VectorStoreRetriever | None:
    """Backend Pinecone: vectorstore en la nube, persistente entre sesiones."""
    if not PINECONE_API_KEY:
        raise ValueError("Se requiere PINECONE_API_KEY en .env para usar Pinecone.")

    from pinecone import Pinecone, ServerlessSpec
    from langchain_pinecone import PineconeVectorStore

    pc = Pinecone(api_key=PINECONE_API_KEY)
    index_name = f"agripoli-{collection_name.replace('_', '-')}"

    # Dimensión del modelo de embeddings
    models_info = EMBEDDING_MODELS_INFO.get(provider, {})
    if embedding_model and embedding_model in models_info:
        dimension = models_info[embedding_model]
    else:
        dimension = list(models_info.values())[0] if models_info else 768

    existing = [idx["name"] for idx in pc.list_indexes()]

    if index_name in existing and not force_rebuild:
        print(f"[RAG/Pinecone] Conectando a indice existente: {index_name}...")
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        if stats.total_vector_count > 0:
            vs = PineconeVectorStore(index=index, embedding=embeddings)
            return vs.as_retriever(search_kwargs={"k": 5})
        print(f"[RAG/Pinecone] Indice vacio, reconstruyendo...")

    if force_rebuild and index_name in existing:
        pc.delete_index(index_name)
        existing = [idx["name"] for idx in pc.list_indexes()]

    if index_name not in existing:
        print(f"[RAG/Pinecone] Creando indice '{index_name}' (dim={dimension})...")
        pc.create_index(
            name=index_name, dimension=dimension, metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        import time
        while not pc.describe_index(index_name).status["ready"]:
            time.sleep(1)

    index = pc.Index(index_name)
    vs = PineconeVectorStore(index=index, embedding=embeddings)

    docs = _load_documents_for_collection(collection_name)
    if not docs:
        return None
    chunks = _chunk_documents(docs, embeddings)
    vs.add_documents(chunks)
    print(f"[RAG/Pinecone] {len(chunks)} fragmentos subidos a '{index_name}'.")
    return vs.as_retriever(search_kwargs={"k": 5})


def _build_chroma(collection_name: str, embeddings, force_rebuild: bool) -> VectorStoreRetriever | None:
    """Backend ChromaDB: colecciones persistentes locales (legado)."""
    from langchain_chroma import Chroma

    persist_dir = str(_BASE_DIR / "chroma" / collection_name)
    vs = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir
    )
    docs = _load_documents_for_collection(collection_name)
    if docs:
        chunks = _chunk_documents(docs, embeddings)
        vs.add_documents(chunks)
    return vs.as_retriever(search_kwargs={"k": 5})


def _load_documents_for_collection(collection_name: str) -> list[Document]:
    """
    Carga documentos (PDF, TXT, MD, CSV) del directorio correspondiente a la colección.
    Directorio esperado: data/knowledge/<collection_name>/
    """
    col = normalizar_coleccion(collection_name)
    docs_dir = Path(__file__).resolve().parent.parent / "data" / "knowledge" / col
    docs_dir.mkdir(parents=True, exist_ok=True)

    from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader

    docs: list[Document] = []

    # 1. PDFs
    for file_path in docs_dir.glob("*.pdf"):
        try:
            loader = PyPDFLoader(str(file_path))
            docs.extend(loader.load())
        except Exception as e:
            print(f"[RAG] Error cargando PDF {file_path.name}: {e}")

    # 2. Textos planos y Markdown (omitiendo README.md de guía)
    for pattern in ("*.txt", "*.md"):
        for file_path in docs_dir.glob(pattern):
            if file_path.name.lower() == "readme.md":
                continue
            try:
                loader = TextLoader(str(file_path), encoding="utf-8")
                docs.extend(loader.load())
            except Exception as e:
                print(f"[RAG] Error cargando archivo {file_path.name}: {e}")

    # 3. Archivos CSV
    for file_path in docs_dir.glob("*.csv"):
        try:
            loader = CSVLoader(str(file_path), encoding="utf-8")
            docs.extend(loader.load())
        except Exception as e:
            print(f"[RAG] Error cargando CSV {file_path.name}: {e}")

    if docs:
        print(f"[RAG] Cargados {len(docs)} fragmentos/páginas desde '{col}'.")
    return docs


def ingestar_texto(texto: str, fuente: str, collection_name: str = "manuales_agricolas",
                    provider: str = "Gemini", db_type: str = "FAISS") -> None:
    """
    Ingesta texto directo (sin PDF) al vectorstore de la colección indicada.
    Útil para ingestar PDFs scrapeados en memoria por los agentes.
    """
    embeddings = get_embeddings_model(provider=provider)
    chunks = _chunk_documents([Document(page_content=texto, metadata={"source": fuente})], embeddings)

    if db_type == "Pinecone":
        retriever = build_vectorstore(collection_name, provider, "Pinecone")
    else:
        retriever = build_vectorstore(collection_name, provider, "FAISS")

    if retriever:
        retriever.vectorstore.add_documents(chunks)
        print(f"[RAG] {len(chunks)} fragmentos de '{fuente}' ingresados a '{collection_name}'.")


def consultar(query: str, collection_name: str = "general",
              provider: str = "Gemini", db_type: str = "FAISS", k: int = 5) -> str:
    """
    Consulta el vectorstore y retorna el contexto formateado para el LLM.
    """
    col = normalizar_coleccion(collection_name)
    retriever = build_vectorstore(col, provider, db_type)
    if not retriever:
        return f"[RAG/{db_type}] Base de conocimientos '{col}' sin documentos locales."

    try:
        resultados = retriever.invoke(query)
        if not resultados:
            return f"[RAG/{db_type}] No se encontró información relevante para '{query}' en '{col}'."

        contexto = f"Contexto local de '{col}':\n\n"
        for i, doc in enumerate(resultados):
            fuente = doc.metadata.get("source", "Desconocido")
            contexto += f"--- Extracto {i+1} (Fuente: {fuente}) ---\n{doc.page_content}\n\n"
        return contexto
    except Exception as e:
        return f"[RAG] Error al consultar '{col}': {e}"


def obtener_estado_rag() -> dict[str, dict]:
    """Retorna un reporte detallado del estado de documentos por colección."""
    base_dir = Path(__file__).resolve().parent.parent / "data" / "knowledge"
    reporte = {}
    for col, desc in COLLECTIONS.items():
        col_dir = base_dir / col
        col_dir.mkdir(parents=True, exist_ok=True)
        archivos = [
            f.name for f in col_dir.iterdir()
            if f.is_file() and f.name.lower() != "readme.md"
        ]
        reporte[col] = {
            "descripcion": desc,
            "ruta": str(col_dir),
            "cantidad_archivos": len(archivos),
            "archivos": archivos[:5],
        }
    return reporte


class RAGEngine:
    """Clase adaptadora de compatibilidad para agentes que requieren la interfaz orientada a objetos."""
    def __init__(self, collection_name: str = "agricultura", persist_directory: str | None = None, provider: str = "Gemini"):
        self.collection_name = collection_name
        self.provider = provider

    def consultar(self, query: str) -> str:
        return consultar(query=query, collection_name=self.collection_name, provider=self.provider)

