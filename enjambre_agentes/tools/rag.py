"""
RAG temporal para documentos extensos encontrados durante el scraping.

Cuando el contenido extraído de una página web o PDF excede un umbral 
(~10,000 caracteres), se vectoriza temporalmente en FAISS en memoria
y se recuperan solo los chunks más relevantes para la consulta.

Adaptado de OptiAgent/rag_core.py pero sin persistencia en disco:
el vectorstore se crea y destruye por sesión.
"""
from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS

from config.models import get_embeddings_model

# Umbral de caracteres para activar RAG temporal
UMBRAL_RAG_CHARS = 10_000

# Configuración del splitter
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 300
TOP_K = 4


def vectorizar_temporal(
    textos: list[str],
    query: str,
    provider: str = "Gemini",
    model_name: str | None = None,
    top_k: int = TOP_K,
) -> str:
    """Vectoriza textos extensos en FAISS temporal y recupera los chunks más relevantes.
    
    Este es el componente RAG del enjambre. Se usa cuando el contenido scraped
    excede UMBRAL_RAG_CHARS caracteres, comprimiendo el contexto a los fragmentos
    más relevantes para la consulta.
    
    Args:
        textos: Lista de textos extensos a vectorizar.
        query: Consulta contra la cual recuperar chunks relevantes.
        provider: Proveedor de embeddings ("Gemini" o "HuggingFace").
        model_name: Modelo específico de embeddings (None = default del proveedor).
        top_k: Número de chunks a recuperar.
        
    Returns:
        Texto concatenado de los chunks más relevantes, o el texto original
        si es menor al umbral.
    """
    # Concatenar todos los textos
    texto_completo = "\n\n".join(t for t in textos if t and t.strip())
    
    if not texto_completo.strip():
        return "No se proporcionó contenido para vectorizar."
    
    # Si el texto es corto, devolverlo directamente sin RAG
    if len(texto_completo) < UMBRAL_RAG_CHARS:
        return texto_completo
    
    print(f"  [RAG Temporal] Texto extenso ({len(texto_completo):,} chars). Vectorizando...")
    
    # Fragmentar
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(texto_completo)
    print(f"  [RAG Temporal] Generados {len(chunks)} chunks.")
    
    if not chunks:
        return texto_completo[:UMBRAL_RAG_CHARS]
    
    # Vectorizar en FAISS en memoria
    try:
        embeddings = get_embeddings_model(provider, model_name)
        vectorstore = FAISS.from_texts(texts=chunks, embedding=embeddings)
        
        # Recuperar los chunks más relevantes
        retriever = vectorstore.as_retriever(search_kwargs={"k": min(top_k, len(chunks))})
        docs = retriever.invoke(query)
        
        resultado = "\n\n---\n\n".join(doc.page_content for doc in docs)
        print(f"  [RAG Temporal] Recuperados {len(docs)} chunks relevantes ({len(resultado):,} chars).")
        
        return resultado
    
    except Exception as e:
        print(f"  [RAG Temporal] Error en vectorización: {e}. Devolviendo texto truncado.")
        return texto_completo[:UMBRAL_RAG_CHARS]


def necesita_rag(texto: str) -> bool:
    """Verifica si un texto es lo suficientemente extenso para requerir RAG.
    
    Args:
        texto: Texto a evaluar.
        
    Returns:
        True si el texto excede el umbral y debe pasar por vectorizar_temporal().
    """
    return len(texto) > UMBRAL_RAG_CHARS if texto else False
