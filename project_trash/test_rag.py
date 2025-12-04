from chatbot_flask.rag import RAGSystem

# Inicializar el sistema RAG
rag_system = RAGSystem()

# Consulta de prueba
query = "guerra fria"
top_k = 5

results = rag_system.rag_search(query, top_k)

print("\nResultados RAG:\n")
for r in results:
    print(f"- Score: {r['score']}")
    print(f"  Texto: {r['text'][:200]}...\n")
