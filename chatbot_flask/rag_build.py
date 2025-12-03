# chatbot_flask/rag_build.py

import os
import shutil
from typing import List, Dict
import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.sentence_transformer import (
    SentenceTransformerEmbeddings,
)

# --- Configuración de Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# --- Constantes ---
DOCUMENTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "documents"))
VECTORSTORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vectorstore"))
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

def load_documents() -> List[Dict]:
    """
    Carga documentos desde el directorio /documents.
    Soporta archivos .pdf, .txt y .md.

    Returns:
        List[Dict]: Una lista de documentos, donde cada documento es un diccionario
                     con 'text' y 'source'.
    """
    logging.info(f"Cargando documentos desde: {DOCUMENTS_DIR}")
    if not os.path.exists(DOCUMENTS_DIR):
        logging.error(f"El directorio de documentos no existe: {DOCUMENTS_DIR}")
        return []

    docs = []
    for filename in os.listdir(DOCUMENTS_DIR):
        filepath = os.path.join(DOCUMENTS_DIR, filename)
        if not os.path.isfile(filepath):
            continue
        
        try:
            if filename.lower().endswith(".pdf"):
                loader = PyPDFLoader(filepath)
                pages = loader.load()
                for i, page in enumerate(pages):
                    docs.append({
                        "text": page.page_content,
                        "source": f"{filename} (página {i+1})"
                    })
                logging.info(f"Cargado {len(pages)} páginas de {filename}")

            elif filename.lower().endswith((".txt", ".md")):
                loader = TextLoader(filepath, encoding="utf-8")
                doc = loader.load()[0]
                docs.append({
                    "text": doc.page_content,
                    "source": filename
                })
                logging.info(f"Cargado documento de texto: {filename}")
            else:
                logging.warning(f"Formato no soportado, omitiendo archivo: {filename}")
        except Exception as e:
            logging.error(f"Error cargando el archivo {filename}: {e}")

    return docs

def split_text(documents: List[Dict]) -> List[Dict]:
    """
    Divide los documentos en chunks más pequeños.

    Args:
        documents (List[Dict]): Lista de documentos a procesar.

    Returns:
        List[Dict]: Lista de chunks, cada uno con 'text', 'source', y 'chunk_id'.
    """
    logging.info("Dividiendo documentos en chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )
    
    all_chunks = []
    for doc in documents:
        chunks = text_splitter.split_text(doc["text"])
        for i, chunk_text in enumerate(chunks):
            all_chunks.append({
                "text": chunk_text,
                "source": doc["source"],
                "chunk_id": i
            })
    
    logging.info(f"Se crearon {len(all_chunks)} chunks en total.")
    return all_chunks

def build_vectorstore(chunks: List[Dict]):
    """
    Construye y persiste la base de datos de vectores ChromaDB.

    Args:
        chunks (List[Dict]): Lista de chunks de texto para indexar.
    """
    if not chunks:
        logging.warning("No hay chunks para indexar. Abortando la creación del vectorstore.")
        return

    # --- Limpiar directorio de vectorstore si existe ---
    if os.path.exists(VECTORSTORE_DIR):
        logging.info(f"Eliminando directorio de vectorstore existente: {VECTORSTORE_DIR}")
        shutil.rmtree(VECTORSTORE_DIR)
    
    os.makedirs(VECTORSTORE_DIR)
    logging.info(f"Directorio de vectorstore creado en: {VECTORSTORE_DIR}")

    # --- Inicializar modelo de embeddings ---
    logging.info(f"Inicializando modelo de embeddings: {EMBEDDING_MODEL}")
    embedding_function = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)

    # --- Preparar textos y metadatos para Chroma ---
    texts_to_embed = [chunk["text"] for chunk in chunks]
    metadata = [{"source": chunk["source"], "chunk_id": chunk["chunk_id"]} for chunk in chunks]

    # --- Crear y persistir el vectorstore ---
    logging.info("Creando y persistiendo la base de datos de vectores con ChromaDB...")
    
    vectorstore = Chroma.from_texts(
        texts=texts_to_embed,
        embedding=embedding_function,
        metadatas=metadata,
        persist_directory=VECTORSTORE_DIR
    )

    logging.info(f"Vectorstore creado exitosamente con {len(chunks)} chunks.")
    logging.info(f"La base de datos está persistida en: {VECTORSTORE_DIR}")

def main():
    """
    Orquesta el proceso completo de construcción del índice RAG.
    """
    logging.info("--- Iniciando el proceso de construcción del sistema RAG ---")
    
    # 1. Cargar documentos
    documents = load_documents()
    if not documents:
        logging.warning("No se encontraron documentos. El proceso ha finalizado.")
        return

    # 2. Dividir en chunks
    chunks = split_text(documents)

    # 3. Construir vectorstore
    build_vectorstore(chunks)

    logging.info("--- Proceso de construcción del RAG finalizado ---")

if __name__ == "__main__":
    main()
