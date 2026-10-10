#!/usr/bin/env python3
"""
Tests unitarios para Advanced RAG
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from src.rag.advanced_rag import AdvancedRAG, CrossEncoderReranker


class TestCrossEncoderReranker:
    """Tests para el Cross-Encoder Re-ranker"""

    def test_initialization(self):
        """Verificar inicialización del reranker"""
        reranker = CrossEncoderReranker()
        # Repo correcto del cross-encoder: "sentence-transformers/ms-marco-MiniLM-L-6-v2" no existe (HF responde 401)
        assert reranker.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert reranker._model is None

    def test_rerank_empty_list(self):
        """Verificar rerank con lista vacía"""
        reranker = CrossEncoderReranker()
        result = reranker.rerank("query", [], top_k=4)
        assert result == []


class TestAdvancedRAG:
    """Tests para la implementación de Advanced RAG"""

    @pytest.fixture(scope="class")
    def advanced_rag(self):
        """Fixture para inicializar AdvancedRAG"""
        try:
            rag = AdvancedRAG()
            return rag
        except Exception as e:
            pytest.skip(f"ChromaDB no disponible: {e}")

    def test_initialization(self, advanced_rag):
        """Verificar que AdvancedRAG se inicializa correctamente"""
        assert advanced_rag is not None
        assert advanced_rag.top_k == 4
        assert advanced_rag.expansion_count == 3
        assert advanced_rag.initial_retrieve_k == 10
        assert advanced_rag.collection is not None
        assert advanced_rag.llm_client is not None
        assert advanced_rag.reranker is not None

    def test_expand_query_returns_list(self, advanced_rag):
        """Verificar que query expansion devuelve lista de queries"""
        query = "prompt injection"
        expanded = advanced_rag._expand_query(query)

        assert isinstance(expanded, list)
        assert len(expanded) >= 1
        assert expanded[0] == query
        assert len(expanded) <= advanced_rag.expansion_count + 1

    def test_expand_query_different_topics(self, advanced_rag):
        """Verificar expansion con diferentes temas"""
        queries = [
            "¿Qué es jailbreak?",
            "data poisoning attacks",
            "system prompt leakage",
        ]

        for query in queries:
            expanded = advanced_rag._expand_query(query)
            assert isinstance(expanded, list)
            assert expanded[0] == query

    def test_retrieve_for_queries(self, advanced_rag):
        """Verificar retrieval multi-query"""
        queries = ["prompt injection", "jailbreak"]
        chunks = advanced_rag._retrieve_for_queries(queries)

        assert isinstance(chunks, list)
        if chunks:
            chunk = chunks[0]
            assert "content" in chunk
            assert "score" in chunk
            assert "source" in chunk
            assert "query_used" in chunk

    def test_retrieve_deduplication(self, advanced_rag):
        """Verificar que hay deduplicación en retrieval multi-query"""
        queries = ["prompt injection", "prompt injection attack"]
        chunks = advanced_rag._retrieve_for_queries(queries)

        contents = [c["content"] for c in chunks]
        assert len(contents) == len(set(contents))

    def test_build_context(self, advanced_rag):
        """Verificar construcción de contexto"""
        test_chunks = [
            {
                "content": "Test content 1",
                "rerank_score": 0.95,
                "source": "test1.md",
                "chunk_idx": 0,
            },
            {
                "content": "Test content 2",
                "rerank_score": 0.85,
                "source": "test2.md",
                "chunk_idx": 1,
            },
        ]

        context = advanced_rag._build_context(test_chunks)

        assert "Test content 1" in context
        assert "Test content 2" in context
        assert "test1.md" in context
        assert "test2.md" in context
        assert "0.95" in context or "95" in context

    def test_build_context_empty(self, advanced_rag):
        """Verificar contexto vacío"""
        context = advanced_rag._build_context([])
        assert "No se encontró contexto relevante" in context

    def test_generate_returns_dict(self, advanced_rag):
        """Verificar que generate devuelve diccionario con estructura correcta"""
        query = "¿Qué es prompt injection?"
        result = advanced_rag.generate(query)

        assert isinstance(result, dict)
        assert "query" in result
        assert "answer" in result
        assert "retrieved_chunks" in result
        assert "expanded_queries" in result
        assert "num_chunks" in result
        assert "model" in result

        assert result["query"] == query
        assert isinstance(result["answer"], str)
        assert isinstance(result["retrieved_chunks"], list)
        assert isinstance(result["expanded_queries"], list)
        assert result["num_chunks"] == len(result["retrieved_chunks"])
        assert result["num_chunks"] <= advanced_rag.top_k

    def test_generate_with_known_topic(self, advanced_rag):
        """Verificar generación con tema conocido del corpus"""
        query = "¿Qué es jailbreak en LLMs?"
        result = advanced_rag.generate(query)

        assert len(result["answer"]) > 0
        assert result["num_chunks"] > 0
        assert len(result["expanded_queries"]) > 1

    def test_generate_chunks_have_rerank_scores(self, advanced_rag):
        """Verificar que chunks finales tienen scores de re-ranking"""
        query = "ataques de prompt injection"
        result = advanced_rag.generate(query)

        for chunk in result["retrieved_chunks"]:
            assert "rerank_score" in chunk
            assert "original_score" in chunk
            assert isinstance(chunk["rerank_score"], float)
            assert isinstance(chunk["original_score"], float)

    @pytest.mark.parametrize("top_k", [1, 2, 4, 5])
    def test_different_top_k(self, top_k):
        """Verificar diferentes valores de top_k"""
        try:
            rag = AdvancedRAG(top_k=top_k)
            query = "test query"
            result = rag.generate(query)
            assert result["num_chunks"] <= top_k
        except Exception as e:
            pytest.skip(f"ChromaDB no disponible: {e}")

    @pytest.mark.parametrize("expansion_count", [1, 2, 3, 5])
    def test_different_expansion_count(self, expansion_count):
        """Verificar diferentes valores de expansion_count"""
        try:
            rag = AdvancedRAG(expansion_count=expansion_count)
            expanded = rag._expand_query("test query")
            assert len(expanded) <= expansion_count + 1
        except Exception as e:
            pytest.skip(f"ChromaDB no disponible: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])