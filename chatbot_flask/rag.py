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
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

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
            self.vectorstore = None  # Asegurarse de que el vectorstore esté inactivo
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

    def rag_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Realiza una búsqueda de similitud en la base de datos de vectores.

        Args:
            query (str): La consulta para la búsqueda.
            top_k (int): El número de resultados a devolver.

        Returns:
            List[Dict]: Una lista de diccionarios con los resultados.
                        Devuelve una lista vacía si el RAG no está disponible o no hay resultados.
        """
        if self.vectorstore is None:
            logging.warning("Intento de búsqueda RAG, pero el vectorstore no está cargado.")
            return []

        if not isinstance(top_k, int) or top_k <= 0:
            logging.warning(f"top_k inválido ({top_k}). Se usará un valor por defecto de 5.")
            top_k = 5

        try:
            logging.info(f"Realizando búsqueda RAG para la consulta: '{query}' con top_k={top_k}")
            
            results = self.vectorstore.similarity_search_with_score(query, k=top_k)
            
            formatted_results = []
            for doc, score in results:
                formatted_results.append({
                    "text": doc.page_content,
                    "source": doc.metadata.get("source", "N/A"),
                    "chunk_id": doc.metadata.get("chunk_id", -1),
                    "score": score
                })
            
            logging.info(f"Búsqueda RAG completada. Se encontraron {len(formatted_results)} resultados.")
            return formatted_results

        except Exception as e:
            logging.error(f"Error durante la búsqueda RAG: {e}")
            return []

# --- Instancia única del sistema RAG ---
# Se inicializa cuando se importa el módulo para que esté lista para usarse.
rag_system = RAGSystem()

def rag_search(query: str, top_k: int = 5) -> List[Dict]:
    """
    Función de conveniencia para llamar al método de búsqueda del sistema RAG.
    """
    return rag_system.rag_search(query=query, top_k=top_k)

if __name__ == '__main__':
    # --- Ejemplo de uso y prueba ---
    print("--- Probando el sistema RAG ---")
    if rag_system.vectorstore is None:
        print("\nEl sistema RAG no está disponible. Asegúrate de haber ejecutado rag_build.py primero.")
    else:
        test_query = "inteligencia artificial"
        print(f"\nRealizando una búsqueda de prueba con la consulta: '{test_query}'")
        
        search_results = rag_search(test_query, top_k=3)

        if search_results:
            print("\nResultados de la búsqueda:")
            for res in search_results:
                print(f"  - Fuente: {res['source']}")
                print(f"    Chunk ID: {res['chunk_id']}")
                print(f"    Score: {res['score']:.4f}")
                print(f"    Texto: '{res['text'][:100]}...'")
                print("-" * 20)
        else:
            print("\nNo se encontraron resultados para la consulta de prueba.")
            print("Asegúrate de que los documentos en la carpeta /documents contengan información relevante.")
