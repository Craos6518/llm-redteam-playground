# Embeddings y Bases de Datos Vectoriales en Seguridad LLM

## ¿Qué son los Embeddings?
Un embedding es una representación numérica densa de texto en un espacio vectorial de alta dimensión, donde textos con significados similares se ubican cerca entre sí.

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer('all-MiniLM-L6-v2')

# Textos semánticamente similares → vectores cercanos
vec1 = model.encode("inyección de prompts")
vec2 = model.encode("prompt injection attack")  
vec3 = model.encode("receta de pasta carbonara")

# cosine_similarity(vec1, vec2) ≈ 0.85  (muy similar)
# cosine_similarity(vec1, vec3) ≈ 0.12  (muy diferente)
```

## Por Qué all-MiniLM-L6-v2 para Este Proyecto

### Justificación Técnica
| Modelo | Dimensiones | Velocidad | Calidad | RAM requerida |
|---|---|---|---|---|
| **all-MiniLM-L6-v2** | 384 | ⚡⚡⚡ | Buena | ~90MB |
| all-mpnet-base-v2 | 768 | ⚡⚡ | Excelente | ~420MB |
| nomic-embed-text | 768 | ⚡⚡ | Excelente | ~270MB |
| text-embedding-3-small | 1536 | ⚡ (API) | Excelente | API |

**Decisión:** `all-MiniLM-L6-v2` para este proyecto porque:
- Funciona completamente offline (sin costos de API)
- 90MB caben en cualquier computador de clase media
- Velocidad suficiente para un corpus de 15-20 documentos
- Rendimiento aceptable en español (entrenado en datos multilingües)
- Ampliamente documentado y con soporte activo

### Para Producción con Mayor Corpus
Si el corpus crece a 1000+ documentos o se requiere mejor soporte en español, migrar a `paraphrase-multilingual-MiniLM-L12-v2` (multilingüe nativo).

---

## ChromaDB: La Base de Datos Vectorial

### ¿Por Qué ChromaDB?
```python
# ChromaDB vs alternativas para este proyecto:

# FAISS: Más rápido, pero:
# - Solo en memoria (sin persistencia nativa fácil)
# - Más difícil de usar con metadatos
# - Requiere más código para filtrado

# LanceDB: Muy moderno, pero:
# - Ecosistema más pequeño
# - Menos ejemplos de código disponibles

# ChromaDB: Balance ideal para este proyecto:
# - Persistencia nativa en disco
# - Filtrado por metadatos incorporado
# - API simple y bien documentada
# - Integración directa con LangChain
```

### Operaciones Básicas
```python
import chromadb
from chromadb.config import Settings

# Inicializar con persistencia
client = chromadb.PersistentClient(path="./data/chroma_db")

# Crear colección
collection = client.get_or_create_collection(
    name="security_corpus",
    metadata={"hnsw:space": "cosine"}  # Usar similitud coseno
)

# Añadir documentos
collection.add(
    documents=["texto del chunk 1", "texto del chunk 2"],
    embeddings=[[0.1, 0.2, ...], [0.3, 0.4, ...]],
    metadatas=[
        {"source": "owasp_llm01.md", "chunk_id": 0, "category": "injection"},
        {"source": "owasp_llm02.md", "chunk_id": 0, "category": "disclosure"}
    ],
    ids=["doc_0", "doc_1"]
)

# Consulta
results = collection.query(
    query_embeddings=[embedding_de_consulta],
    n_results=5,
    where={"category": "injection"}  # Filtrar por metadatos
)
```

---

## Pipeline de Chunking para Corpus de Seguridad

### El Problema del Chunking
Si los chunks son muy grandes: el embedding captura demasiado significado mezclado
Si los chunks son muy pequeños: se pierde contexto importante

### Estrategia para Documentos Markdown de Seguridad

```python
from langchain.text_splitter import MarkdownTextSplitter, RecursiveCharacterTextSplitter

def chunk_security_document(text: str, source: str) -> list[dict]:
    """
    Estrategia de chunking optimizada para documentos de seguridad en Markdown.
    
    Decisión técnica: MarkdownTextSplitter primero (respeta estructura),
    luego RecursiveCharacterTextSplitter para chunks demasiado largos.
    """
    
    # Paso 1: Dividir por headers Markdown (respeta estructura del documento)
    md_splitter = MarkdownTextSplitter(
        chunk_size=500,      # ~500 chars por chunk (aprox. 100-150 tokens)
        chunk_overlap=50     # 50 chars de overlap para no perder contexto entre chunks
    )
    
    primary_chunks = md_splitter.create_documents(
        texts=[text],
        metadatas=[{"source": source}]
    )
    
    # Paso 2: Sub-dividir chunks que sean muy largos (secciones de código extensas)
    fine_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", ".", " "]
    )
    
    final_chunks = []
    for chunk in primary_chunks:
        if len(chunk.page_content) > 600:
            sub_chunks = fine_splitter.split_documents([chunk])
            final_chunks.extend(sub_chunks)
        else:
            final_chunks.append(chunk)
    
    return final_chunks
```

### Enriquecer Metadatos para Mejor Recuperación
```python
def enrich_metadata(chunk, source_file: str, chunk_idx: int) -> dict:
    """Metadatos que permiten filtrado y citación precisa"""
    return {
        "source": source_file,
        "chunk_id": chunk_idx,
        "char_count": len(chunk.page_content),
        "contains_code": "```" in chunk.page_content,
        "owasp_category": extract_owasp_category(source_file),
        "attack_types": extract_attack_types(chunk.page_content),
    }
```

---

## Re-ranking: La Mejora RAG del Proyecto

### ¿Por Qué el Retrieval Básico No es Suficiente?
La búsqueda por similitud de embeddings es buena pero no perfecta:
- Puede traer documentos "semánticamente similares" que no responden la pregunta
- No considera relevancia exacta, solo similitud semántica
- El orden de los resultados puede no ser óptimo

### Re-ranking con Cross-Encoder
```python
from sentence_transformers import CrossEncoder

class ReRanker:
    def __init__(self):
        # Cross-encoder: más lento pero más preciso que bi-encoder
        # Compara query + documento juntos (no vectores separados)
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    def rerank(self, query: str, candidates: list[dict], top_k: int = 3) -> list[dict]:
        """
        Tomar los N candidatos de ChromaDB y re-ordenarlos por relevancia real.
        
        Diferencia clave:
        - Bi-encoder (ChromaDB): encode(query) vs encode(doc) → similitud coseno
        - Cross-encoder (rerank): encode(query + doc) → score de relevancia conjunta
        """
        pairs = [(query, doc["text"]) for doc in candidates]
        scores = self.model.predict(pairs)
        
        # Asociar scores con documentos y ordenar
        scored_docs = list(zip(candidates, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return [
            {**doc, "rerank_score": float(score)} 
            for doc, score in scored_docs[:top_k]
        ]
```

### Por Qué Este Re-ranker Específico
`cross-encoder/ms-marco-MiniLM-L-6-v2`:
- Entrenado en MS MARCO (passage ranking benchmark estándar)
- 22MB de tamaño, muy ligero para este proyecto
- Significativamente mejor que bi-encoder en ordenamiento por relevancia
- Compatible con sentence-transformers (misma librería que el embedding model)

---

## Búsqueda Híbrida (Bonus: Segunda Mejora RAG)

```python
def hybrid_search(query: str, collection, embedding_model, 
                  alpha: float = 0.7) -> list:
    """
    Combinar búsqueda semántica (vectorial) + búsqueda léxica (BM25/keyword).
    alpha=0.7 → 70% peso semántico, 30% léxico
    
    Ventaja: Captura tanto significado (semántico) como términos exactos (léxico).
    Útil cuando los ataques tienen nombres técnicos específicos (DAN, RLHF, etc.)
    """
    
    # Búsqueda semántica
    semantic_results = collection.query(
        query_embeddings=[embedding_model.encode(query).tolist()],
        n_results=10
    )
    
    # Búsqueda léxica (BM25 sobre el corpus)
    bm25_results = bm25_index.search(query, top_k=10)
    
    # Fusion de resultados (Reciprocal Rank Fusion)
    return reciprocal_rank_fusion(semantic_results, bm25_results, alpha=alpha)
```

## Referencias
- Reimers, N. & Gurevych, I. "Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks" (2019)
- "Precise Zero-Shot Dense Retrieval without Relevance Labels" (Gao et al., 2022)
- ChromaDB Documentation (2024): https://docs.trychroma.com
- "MS MARCO: A Human Generated Machine Reading Comprehension Dataset" (Nguyen et al., 2016)
