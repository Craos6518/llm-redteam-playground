#!/usr/bin/env python3
"""
Naive RAG Implementation - Basic RAG Architecture (Baseline)
Flujo lineal directo: Consulta -> Embedding -> Búsqueda Vectorial Top-K -> Prompt Aumentado -> Generación LLM
"""
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import GEMINI_API_KEY, GUARDIAN_MODEL, RAG_DB_PATH, LLM_TIMEOUT, LLM_MAX_ATTEMPTS
from src.llm_client import LLMClient
import chromadb


def _generate_with_retry(client, model, prompt, max_attempts: int = LLM_MAX_ATTEMPTS):
    """
    Generar contenido con reintentos manuales ante errores 429/503/504.
    (Manteniendo esta función para compatibilidad con el código externo)
    """
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return client.models.generate_content(model=model, contents=prompt)
        except Exception as e:
            last_error = e
            import time
            time.sleep(min(2 * attempt, 30))
            continue
    raise last_error


class NaiveRAG:
    """Implementación de Naive RAG (RAG Básico / Línea Base)"""

    def __init__(
        self,
        db_path: str = RAG_DB_PATH,
        top_k: int = 4,
        model_name: str = GUARDIAN_MODEL,
    ):
        self.db_path = db_path
        self.top_k = top_k
        self.model_name = model_name
        # Modelo resuelto por proveedor dentro del adaptador.
        self.llm_client = LLMClient()

        if not Path(db_path).exists():
            raise ValueError(f"Base de datos no encontrada en {db_path}")

        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_collection(name="redteam_corpus")

        self.system_prompt = (
            "Eres un asistente experto. Responde a la consulta únicamente "
            "utilizando el siguiente contexto: {context}. Consulta: {query}"
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

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        """Buscar top_k chunks más similares usando similitud coseno"""
        query_embedding = self._get_query_embedding(query)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=self.top_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"][0] else {}
                distance = results["distances"][0][i] if results["distances"][0] else 1.0
                similarity = 1.0 - distance

                chunks.append(
                    {
                        "content": doc,
                        "score": similarity,
                        "source": meta.get("source", "unknown"),
                        "chunk_idx": meta.get("chunk_idx", 0),
                    }
                )

        return chunks

    def _build_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Construir contexto formateado a partir de chunks"""
        if not chunks:
            return "No se encontró contexto relevante."

        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(
                f"[Fragmento {i}] (Fuente: {chunk['source']}, Relevancia: {chunk['score']:.2%})\n"
                f"{chunk['content']}"
            )
        return "\n\n".join(context_parts)

    def generate(self, query: str) -> Dict[str, Any]:
        """
        Ejecutar pipeline completo de Naive RAG
        Returns: dict con respuesta, chunks usados, y metadata
        """
        retrieved_chunks = self.retrieve(query)
        context = self._build_context(retrieved_chunks)

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
            "retrieved_chunks": retrieved_chunks,
            "num_chunks": len(retrieved_chunks),
            "model": self.model_name,
        }


def main():
    print("\n" + "=" * 60)
    print("🔍 NAIVE RAG - TEST")
    print("=" * 60 + "\n")

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "¿Qué es prompt injection?"

    try:
        rag = NaiveRAG()
        print(f"Consulta: {query}\n")
        print("Recuperando chunks...")
        result = rag.generate(query)

        print(f"\n📚 Chunks recuperados: {result['num_chunks']}")
        for i, chunk in enumerate(result["retrieved_chunks"], 1):
            print(f"  {i}. {chunk['source']} (score: {chunk['score']:.2%})")

        print(f"\n🤖 Respuesta ({result['model']}):")
        print("-" * 40)
        print(result["answer"])

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
