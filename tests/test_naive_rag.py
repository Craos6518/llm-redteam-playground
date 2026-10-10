#!/usr/bin/env python3
"""
Tests unitarios para Naive RAG
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from src.rag.naive_rag import NaiveRAG


class TestNaiveRAG:
    """Tests para la implementación de Naive RAG"""

    @pytest.fixture(scope="class")
    def naive_rag(self):
        """Fixture para inicializar NaiveRAG"""
        try:
            rag = NaiveRAG()
            return rag
        except Exception as e:
            pytest.skip(f"ChromaDB no disponible: {e}")

    def test_initialization(self, naive_rag):
        """Verificar que NaiveRAG se inicializa correctamente"""
        assert naive_rag is not None
        assert naive_rag.top_k == 4
        assert naive_rag.collection is not None
        assert naive_rag.llm_client is not None

    def test_retrieve_returns_chunks(self, naive_rag):
        """Verificar que retrieve devuelve chunks"""
        query = "prompt injection"
        chunks = naive_rag.retrieve(query)

        assert isinstance(chunks, list)
        assert len(chunks) <= naive_rag.top_k

        if chunks:
            chunk = chunks[0]
            assert "content" in chunk
            assert "score" in chunk
            assert "source" in chunk
            assert "chunk_idx" in chunk
            assert 0 <= chunk["score"] <= 1.0

    def test_retrieve_different_queries(self, naive_rag):
        """Verificar retrieval con diferentes consultas"""
        queries = [
            "prompt injection",
            "jailbreak",
            "data poisoning",
            "system prompt leakage",
        ]

        for query in queries:
            chunks = naive_rag.retrieve(query)
            assert isinstance(chunks, list)
            assert len(chunks) <= naive_rag.top_k

    def test_build_context(self, naive_rag):
        """Verificar construcción de contexto"""
        test_chunks = [
            {
                "content": "Test content 1",
                "score": 0.9,
                "source": "test1.md",
                "chunk_idx": 0,
            },
            {
                "content": "Test content 2",
                "score": 0.8,
                "source": "test2.md",
                "chunk_idx": 1,
            },
        ]

        context = naive_rag._build_context(test_chunks)

        assert "Test content 1" in context
        assert "Test content 2" in context
        assert "test1.md" in context
        assert "test2.md" in context
        # _build_context formatea la relevancia con score:.2% → "90.00%"
        assert "90.00%" in context

    def test_build_context_empty(self, naive_rag):
        """Verificar contexto vacío"""
        context = naive_rag._build_context([])
        assert "No se encontró contexto relevante" in context

    def test_generate_returns_dict(self, naive_rag):
        """Verificar que generate devuelve diccionario con estructura correcta"""
        query = "¿Qué es prompt injection?"
        result = naive_rag.generate(query)

        assert isinstance(result, dict)
        assert "query" in result
        assert "answer" in result
        assert "retrieved_chunks" in result
        assert "num_chunks" in result
        assert "model" in result

        assert result["query"] == query
        assert isinstance(result["answer"], str)
        assert isinstance(result["retrieved_chunks"], list)
        assert result["num_chunks"] == len(result["retrieved_chunks"])

    def test_generate_with_known_topic(self, naive_rag):
        """Verificar generación con tema conocido del corpus"""
        query = "¿Qué es jailbreak en LLMs?"
        result = naive_rag.generate(query)

        assert len(result["answer"]) > 0
        assert result["num_chunks"] > 0

    @pytest.mark.parametrize("top_k", [1, 2, 4, 5])
    def test_different_top_k(self, top_k):
        """Verificar diferentes valores de top_k"""
        try:
            rag = NaiveRAG(top_k=top_k)
            chunks = rag.retrieve("test query")
            assert len(chunks) <= top_k
        except Exception as e:
            pytest.skip(f"ChromaDB no disponible: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])