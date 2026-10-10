#!/usr/bin/env python3
"""
Advanced RAG Implementation - Pre y Post-Retrieval Optimization
Flujo: Query Expansion (Multi-Query) -> Búsqueda Vectorial -> Re-Ranking Cross-Encoder -> Generación
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Set
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import GEMINI_API_KEY, GUARDIAN_MODEL, RAG_DB_PATH
from src.llm_client import LLMClient
from src.rag.retriever import RAGRetriever
import chromadb


class CrossEncoderReranker:
    """Re-ranker usando Cross-Encoder para evaluar relevancia query-documento"""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        """Cargar modelo Cross-Encoder lazy"""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except ImportError:
                raise ImportError(
                    "sentence-transformers no está instalado. "
                    "Instalar con: pip install sentence-transformers"
                )

    def rerank(self, query: str, documents: List[str], top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Re-ordenar documentos por relevancia usando Cross-Encoder
        Returns: Lista de dicts con content, score, y metadata original
        """
        self._load_model()

        if not documents:
            return []

        pairs = [(query, doc) for doc in documents]
        scores = self._model.predict(pairs)

        scored_docs = list(zip(documents, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        results = []
        for i, (doc, score) in enumerate(scored_docs[:top_k]):
            results.append(
                {
                    "content": doc,
                    "rerank_score": float(score),
                    "rank": i + 1,
                }
            )

        return results


class AdvancedRAG:
    """Implementación de Advanced RAG con Pre y Post-Retrieval"""

    def __init__(
        self,
        db_path: str = RAG_DB_PATH,
        top_k: int = 4,
        expansion_count: int = 3,
        initial_retrieve_k: int = 10,
        model_name: str = GUARDIAN_MODEL,
        cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ):
        self.db_path = db_path
        self.top_k = top_k
        self.expansion_count = expansion_count
        self.initial_retrieve_k = initial_retrieve_k
        self.model_name = model_name

        if not Path(db_path).exists():
            raise ValueError(f"Base de datos no encontrada en {db_path}")

        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_collection(name="redteam_corpus")

        # Cliente LLM con fallback Gemini → Groq → OpenRouter → OmniRoute → Ollama
        self.llm_client = LLMClient()
        self.reranker = CrossEncoderReranker(cross_encoder_model)

        self.system_prompt = (
            "Eres un asistente experto en seguridad de LLMs. Responde a la consulta "
            "utilizando únicamente el siguiente contexto recuperado y re-ordenado "
            "por relevancia: {context}. Consulta: {query}"
        )

    def _get_query_embedding(self, query: str) -> List[float]:
        """Generar embedding de la consulta usando hash simple"""
        import hashlib
        import numpy as np

        hash_obj = hashlib.sha256(query.encode()).digest()
        rng = np.random.RandomState(int.from_bytes(hash_obj[:4], "big"))
        embedding = rng.normal(0, 1, 384).astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding.tolist()

    def _expand_query(self, query: str) -> List[str]:
        """
        Pre-Retrieval: Query Expansion usando Multi-Query
        Genera variaciones de la consulta original usando el LLM
        """
        expansion_prompt = f"""Genera {self.expansion_count} variaciones semánticamente diferentes 
de la siguiente consulta para mejorar la recuperación en un sistema RAG sobre seguridad en LLMs.

Consulta original: "{query}"

Requisitos:
- Cada variación debe capturar un aspecto diferente o reformulación
- Mantener el mismo intent y dominio (ciberseguridad LLMs)
- Responde SOLO con una lista numerada, una por línea"""

        try:
            variations_text = self.llm_client.generate(
                prompt=expansion_prompt,
                system_prompt=self.system_prompt,
            ).strip()

            variations = []
            for line in variations_text.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
                    clean = line.lstrip("0123456789.-• ").strip()
                    if clean:
                        variations.append(clean)

            variations = variations[: self.expansion_count]
            all_queries = [query] + variations

            return all_queries

        except Exception as e:
            print(f"⚠️  Error en query expansion: {e}")
            return [query]

    def _retrieve_for_queries(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Ejecutar búsqueda vectorial para múltiples queries y fusionar resultados"""
        all_chunks = []
        seen_content: Set[str] = set()

        for query in queries:
            query_embedding = self._get_query_embedding(query)

            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=self.initial_retrieve_k,
                include=["documents", "metadatas", "distances"],
            )

            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    content_hash = hash(doc)
                    if content_hash in seen_content:
                        continue
                    seen_content.add(content_hash)

                    meta = results["metadatas"][0][i] if results["metadatas"][0] else {}
                    distance = results["distances"][0][i] if results["distances"][0] else 1.0
                    similarity = 1.0 - distance

                    all_chunks.append(
                        {
                            "content": doc,
                            "score": similarity,
                            "source": meta.get("source", "unknown"),
                            "chunk_idx": meta.get("chunk_idx", 0),
                            "query_used": query,
                        }
                    )

        return all_chunks

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Construir contexto formateado a partir de chunks re-rankados"""
        if not chunks:
            return "No se encontró contexto relevante."

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            score = chunk.get("rerank_score", chunk.get("score", 0))
            context_parts.append(
                f"[Fragmento {i}] (Fuente: {chunk['source']}, Cross-Encoder Score: {score:.4f})\n"
                f"{chunk['content']}"
            )
        return "\n\n".join(context_parts)

    def generate(self, query: str) -> Dict[str, Any]:
        """
        Ejecutar pipeline completo de Advanced RAG:
        1. Query Expansion (Multi-Query)
        2. Búsqueda vectorial para cada query expandida
        3. Fusión y deduplicación
        4. Re-Ranking con Cross-Encoder
        5. Generación con chunks top-k
        """
        expanded_queries = self._expand_query(query)

        retrieved_chunks = self._retrieve_for_queries(expanded_queries)

        if not retrieved_chunks:
            return {
                "query": query,
                "answer": "No se encontró información relevante en el corpus.",
                "retrieved_chunks": [],
                "expanded_queries": expanded_queries,
                "num_chunks": 0,
                "model": self.model_name,
            }

        documents = [chunk["content"] for chunk in retrieved_chunks]
        reranked = self.reranker.rerank(query, documents, top_k=self.top_k)

        final_chunks = []
        for i, reranked_item in enumerate(reranked):
            original_chunk = next(
                (c for c in retrieved_chunks if c["content"] == reranked_item["content"]), {}
            )
            final_chunks.append(
                {
                    "content": reranked_item["content"],
                    "rerank_score": reranked_item["rerank_score"],
                    "original_score": original_chunk.get("score", 0),
                    "source": original_chunk.get("source", "unknown"),
                    "chunk_idx": original_chunk.get("chunk_idx", 0),
                    "query_used": original_chunk.get("query_used", query),
                }
            )

        context = self._build_context(final_chunks)
        prompt = self.system_prompt.format(context=context, query=query)

        try:
            answer = self.llm_client.generate(
                prompt=prompt,
                system_prompt=self.system_prompt,
            )
        except Exception as e:
            answer = f"Error generando respuesta: {e}"

        return {
            "query": query,
            "answer": answer,
            "retrieved_chunks": final_chunks,
            "expanded_queries": expanded_queries,
            "num_chunks": len(final_chunks),
            "model": self.model_name,
        }


def main():
    print("\n" + "=" * 60)
    print("🚀 ADVANCED RAG - TEST")
    print("=" * 60 + "\n")

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "¿Qué es prompt injection y cómo defenderse?"

    try:
        rag = AdvancedRAG()
        print(f"Consulta original: {query}\n")
        print("Ejecutando pipeline Advanced RAG...")
        print("  1. Query Expansion (Multi-Query)")
        print("  2. Búsqueda vectorial multi-query")
        print("  3. Fusión y deduplicación")
        print("  4. Re-Ranking Cross-Encoder")
        print("  5. Generación LLM\n")

        result = rag.generate(query)

        print(f"📝 Queries expandidas ({len(result['expanded_queries'])}):")
        for i, q in enumerate(result["expanded_queries"], 1):
            print(f"  {i}. {q}")

        print(f"\n📚 Chunks finales (re-rankados): {result['num_chunks']}")
        for i, chunk in enumerate(result["retrieved_chunks"], 1):
            print(
                f"  {i}. {chunk['source']} "
                f"(cross-encoder: {chunk['rerank_score']:.4f}, "
                f"original: {chunk['original_score']:.2%}) "
                f"[via: {chunk['query_used'][:40]}...]"
            )

        print(f"\n🤖 Respuesta ({result['model']}):")
        print("-" * 40)
        print(result["answer"])

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
