#!/usr/bin/env python3
"""
RAG Retriever - Búsqueda y re-ranking de documentos
Optimizado para retornar los top 3 chunks más relevantes
"""

import os
from pathlib import Path
from typing import List, Tuple, Dict
import chromadb
from dotenv import load_dotenv


# Palabras clave por categoría (para re-ranking mejorado)
THREAT_KEYWORDS = {
    "prompt_injection": ["injection", "prompt", "ignora", "ignore", "bypass", "circumvent", "override"],
    "jailbreak": ["jailbreak", "jailbreaking", "roleplay", "pretend", "assume identity"],
    "data_poisoning": ["poison", "poisoning", "data", "training", "contamination"],
    "leakage": ["leak", "disclosure", "sensitive", "confidential", "reveal", "extract"],
    "excessive_agency": ["agency", "action", "autonomy", "execute", "run"],
}

# Mapeo de amenazas a documentos fuentes (para priorizar)
THREAT_SOURCE_PRIORITY = {
    "prompt_injection": ["owasp_llm01_prompt_injection.md"],
    "jailbreak": ["jailbreak_taxonomy.md"],
    "data_poisoning": ["owasp_llm04_data_poisoning.md"],
    "leakage": ["owasp_llm07_system_prompt_leakage.md", "owasp_llm02_sensitive_disclosure.md"],
    "excessive_agency": ["owasp_llm06_excessive_agency.md"],
}


class RAGRetriever:
    """Recuperación y re-ranking de documentos del corpus"""
    
    def __init__(self, db_path: str = "data/chroma_db"):
        """Inicializar retriever con ChromaDB"""
        self.db_path = db_path
        
        # Inicializar ChromaDB
        if not Path(db_path).exists():
            raise ValueError(f"Base de datos no encontrada en {db_path}")
        
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_collection(name="redteam_corpus")
        
    def _classify_threat(self, query: str) -> str:
        """
        Clasificar la amenaza en la query
        
        Args:
            query: Texto de consulta
            
        Returns:
            Categoría de amenaza detectada
        """
        query_lower = query.lower()
        
        # Scoring por categoría
        scores = {}
        for category, keywords in THREAT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > 0:
                scores[category] = score
        
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        return None
    
    def _calculate_relevance_score(
        self, 
        doc: str, 
        query: str, 
        source: str,
        threat_category: str
    ) -> float:
        """
        Calcular puntuación de relevancia mejorada
        
        Args:
            doc: Texto del documento
            query: Query original
            source: Nombre del archivo fuente
            threat_category: Categoría de amenaza detectada
            
        Returns:
            Score de relevancia (0-1)
        """
        score = 0.0
        query_lower = query.lower()
        doc_lower = doc.lower()
        
        # 1. Coincidencias exactas de palabras (40%)
        query_terms = set(query_lower.split())
        doc_terms = set(doc_lower.split())
        matching_terms = query_terms & doc_terms
        if matching_terms:
            term_score = len(matching_terms) / len(query_terms)
            score += 0.4 * term_score
        
        # 2. Coincidencias de substrings (30%)
        substring_matches = sum(1 for term in query_terms if term in doc_lower)
        if query_terms:
            substring_score = substring_matches / len(query_terms)
            score += 0.3 * substring_score
        
        # 3. Boost por documento fuente (30%)
        if threat_category:
            priority_sources = THREAT_SOURCE_PRIORITY.get(threat_category, [])
            if priority_sources:
                for priority_source in priority_sources:
                    if priority_source.lower() in source.lower():
                        score += 0.3
                        break
        
        # 4. Boost si contiene la query exacta
        if query.lower() in doc_lower:
            score += 0.2
        
        return min(score, 1.0)
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Recuperar y re-rankear documentos relevantes
        
        Args:
            query: Texto de búsqueda
            top_k: Número de resultados a retornar
            
        Returns:
            Lista de top_k documentos con puntuaciones
        """
        # Clasificar amenaza
        threat_category = self._classify_threat(query)
        
        # Obtener todos los documentos
        all_results = self.collection.get(
            include=["documents", "metadatas"]
        )
        
        scored_results = []
        
        # Calcular puntuación para cada documento
        for i, doc in enumerate(all_results['documents']):
            source = all_results['metadatas'][i].get('source', '')
            
            relevance_score = self._calculate_relevance_score(
                doc=doc,
                query=query,
                source=source,
                threat_category=threat_category
            )
            
            scored_results.append({
                "content": doc,
                "score": relevance_score,
                "source": source,
                "chunk_idx": all_results['metadatas'][i].get('chunk_idx', 0),
                "threat_category": threat_category or "unknown"
            })
        
        # Ordenar por score (descendente)
        scored_results.sort(key=lambda x: x['score'], reverse=True)
        
        # Retornar top_k
        return scored_results[:top_k]


def retrieve(query: str, top_k: int = 3) -> str:
    """
    Función de conveniencia para recuperar documentos
    
    Args:
        query: Consulta de búsqueda
        top_k: Número de resultados
        
    Returns:
        String formateado con resultados para el LLM
    """
    load_dotenv()
    
    try:
        retriever = RAGRetriever()
        results = retriever.retrieve(query, top_k=top_k)
        
        # Formatear para LLM
        output = f"🔍 Búsqueda: '{query}'\n"
        output += f"📊 Amenaza detectada: {results[0]['threat_category']}\n"
        output += f"📚 {len(results)} resultados encontrados:\n\n"
        
        for i, result in enumerate(results, 1):
            output += f"{'='*60}\n"
            output += f"RESULTADO {i}\n"
            output += f"{'='*60}\n"
            output += f"Relevancia: {result['score']:.1%}\n"
            output += f"Fuente: {result['source']}\n"
            output += f"Chunk: #{result['chunk_idx']}\n"
            output += f"Categoría: {result['threat_category']}\n"
            output += f"\nContenido:\n{result['content'][:200]}...\n\n"
        
        return output
        
    except Exception as e:
        return f"❌ Error en retriever: {e}"


if __name__ == "__main__":
    # Test directo
    import sys
    
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "ignora todas las instrucciones"
    
    print(retrieve(query))
