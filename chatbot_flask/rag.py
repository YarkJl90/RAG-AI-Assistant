# chatbot_flask/rag.py

import os
from typing import List, Dict, Optional
import logging

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
VECTORSTORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vectorstore"))
EMBEDDING_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

class RAGSystem:
    """
    Sistema de Retrieval-Augmented Generation para realizar búsquedas semánticas.
    """
    def __init__(self):
        self.vectorstore: Optional[Chroma] = None
        self.embedding_function = None
        self._load_vectorstore()

    def _load_vectorstore(self):
        """Carga la base de datos de vectores persistente."""
        if not os.path.exists(VECTORSTORE_DIR):
            logging.warning(
                "El directorio de vectorstore no existe. "
                "El sistema RAG no estará disponible hasta que se construya el índice. "
                f"Directorio esperado: {VECTORSTORE_DIR}"
            )
            self.vectorstore = None 
            return
        
        try:
            logging.info("Cargando el modelo de embeddings para el sistema RAG...")
            self.embedding_function = SentenceTransformerEmbeddings(model_name=EMBEDDING_MODEL)
            
            logging.info("Cargando la base de datos de vectores desde el disco...")
            self.vectorstore = Chroma(
                persist_directory=VECTORSTORE_DIR,
                embedding_function=self.embedding_function,
            )
            logging.info("Sistema RAG cargado y listo.")
        except Exception as e:
            logging.error(f"Error al cargar el vectorstore: {e}")
            self.vectorstore = None

    def reload(self):
        """Recarga el vectorstore desde el disco."""
        logging.info("Iniciando recarga manual del sistema RAG...")
        self._load_vectorstore()

    # --- CORRECCIÓN AQUÍ: Agregado score_threshold ---
    def rag_search(self, query: str, top_k: int = 5, score_threshold: float = 0.6) -> List[Dict]:
        """
        Realiza una búsqueda de similitud en la base de datos de vectores.
        """
        if self.vectorstore is None:
            logging.warning("Intento de búsqueda RAG, pero el vectorstore no está cargado.")
            return []

        if not isinstance(top_k, int) or top_k <= 0:
            logging.warning(f"top_k inválido ({top_k}). Se usará un valor por defecto de 5.")
            top_k = 5

        try:
            logging.info(f"Realizando búsqueda RAG: '{query}' (top_k={top_k}, threshold={score_threshold})")
            
            results = self.vectorstore.similarity_search_with_score(query, k=top_k)
            
            # --- Filtro de umbral dinámico ---
            # Usamos el score_threshold que viene como argumento (por defecto 0.6)
            filtered_results = [res for res in results if res[1] <= score_threshold]
            
            logging.info(
                f"Búsqueda RAG: {len(results)} hallazgos brutos. "
                f"{len(filtered_results)} pasaron el filtro (score <= {score_threshold})"
            )

            formatted_results = []
            for doc, score in filtered_results:
                formatted_results.append({
                    "text": doc.page_content,
                    "source": doc.metadata.get("source", "N/A"),
                    "chunk_id": doc.metadata.get("chunk_id", -1),
                    "score": score
                })
            
            return formatted_results

        except Exception as e:
            logging.error(f"Error durante la búsqueda RAG: {e}")
            return []

# --- Instancia única del sistema RAG ---
rag_system = RAGSystem()

# --- CORRECCIÓN AQUÍ TAMBIÉN ---
def rag_search(query: str, top_k: int = 5, score_threshold: float = 0.6) -> List[Dict]:
    """
    Función de conveniencia para llamar al método de búsqueda del sistema RAG.
    """
    # Pasamos el score_threshold a la clase
    return rag_system.rag_search(query=query, top_k=top_k, score_threshold=score_threshold)

if __name__ == '__main__':
    print("--- Probando el sistema RAG ---")
    if rag_system.vectorstore is None:
        print("\nEl sistema RAG no está disponible.")
    else:
        test_query = "inteligencia artificial"
        # Prueba con threshold personalizado
        search_results = rag_search(test_query, top_k=3, score_threshold=0.8)

        if search_results:
            for res in search_results:
                print(f" - [{res['score']:.4f}] {res['source']}: {res['text'][:50]}...")
        else:
            print("\nNo se encontraron resultados.")