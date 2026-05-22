#!/usr/bin/env python3
"""
RAG Module - Retrieval-Augmented Generation
Ingesta de documentos corpus y búsqueda semántica con ChromaDB
"""

import os
import sys
import argparse
from pathlib import Path
from typing import List, Tuple
import json
import hashlib
import numpy as np

import chromadb
from dotenv import load_dotenv
from google import genai


def simple_hash_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Generar embedding simple basado en hash + distribución
    (Para desarrollo/testing sin necesidad de modelos grandes)
    
    Args:
        text: Texto a embedear
        dim: Dimensión del embedding
        
    Returns:
        Vector de embedding normalizado
    """
    try:
        hash_obj = hashlib.sha256(text.encode()).digest()
        rng = np.random.RandomState(int.from_bytes(hash_obj[:4], 'big'))
        embedding = rng.normal(0, 1, dim).astype(np.float32)
        # Normalizar
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding.tolist()
    except:
        # Fallback si numpy no está disponible
        import random
        seed_val = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        random.seed(seed_val)
        embedding = [random.gauss(0, 1) for _ in range(dim)]
        norm = sum(x**2 for x in embedding) ** 0.5
        if norm > 0:
            embedding = [x / norm for x in embedding]
        return embedding


class RAGIngestor:
    """Ingesta de documentos y gestión de embeddings con ChromaDB"""
    
    def __init__(self, db_path: str = "data/chroma_db", reset: bool = False):
        """
        Inicializar el ingesta RAG
        
        Args:
            db_path: Ruta donde almacenar la BD de ChromaDB
            reset: Si True, borra la BD existente
        """
        self.db_path = db_path
        self.corpus_path = "data/corpus"
        
        # Inicializar ChromaDB (nueva API)
        if reset and Path(db_path).exists():
            print(f"🗑️  Borrando BD anterior en {db_path}...")
            import shutil
            shutil.rmtree(db_path)
        
        # Usar nueva API de ChromaDB
        self.chroma_client = chromadb.PersistentClient(path=db_path)
        
        # Obtener o crear colección
        self.collection = self.chroma_client.get_or_create_collection(
            name="redteam_corpus",
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"✓ ChromaDB inicializado en {db_path}")
        print(f"✓ Colección 'redteam_corpus' lista")
        
    def get_embedding(self, text: str) -> List[float]:
        """
        Obtener embedding usando estrategia simple basada en hash
        (Para desarrollo/testing sin modelos externos)
        
        Args:
            text: Texto a embedear
            
        Returns:
            Vector de embedding normalizado
        """
        return simple_hash_embedding(text, dim=384)
    
    def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 100) -> List[str]:
        """
        Dividir texto en chunks con overlap
        
        Args:
            text: Texto a dividir
            chunk_size: Tamaño de cada chunk
            overlap: Overlap entre chunks
            
        Returns:
            Lista de chunks
        """
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunks.append(text[i:i + chunk_size])
        return chunks
    
    def ingest_corpus(self) -> int:
        """
        Ingestar todos los documentos del corpus
        
        Returns:
            Número de chunks ingesta dos
        """
        corpus_dir = Path(self.corpus_path)
        if not corpus_dir.exists():
            print(f"❌ Corpus no encontrado en {self.corpus_path}")
            return 0
        
        md_files = sorted(corpus_dir.glob("*.md"))
        print(f"\n📚 Encontrados {len(md_files)} archivos\n")
        
        total_chunks = 0
        
        for file_path in md_files:
            print(f"📄 Procesando: {file_path.name}")
            
            try:
                # Leer documento
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Dividir en chunks
                chunks = self.chunk_text(content)
                
                for i, chunk in enumerate(chunks):
                    if not chunk.strip():
                        continue
                    
                    # Generar embedding
                    embedding = self.get_embedding(chunk)
                    
                    # ID único
                    doc_id = f"{file_path.stem}_chunk_{i}"
                    
                    # Agregar a ChromaDB
                    self.collection.add(
                        ids=[doc_id],
                        documents=[chunk],
                        embeddings=[embedding],
                        metadatas=[{
                            "source": file_path.name,
                            "chunk_idx": i,
                            "total_chunks": len(chunks)
                        }]
                    )
                    
                    total_chunks += 1
                
                print(f"   ✓ {len(chunks)} chunks ingesta dos")
                
            except Exception as e:
                print(f"   ❌ Error procesando {file_path.name}: {e}")
        
        print(f"\n✅ Total: {total_chunks} chunks ingesta dos y persistidos")
        return total_chunks
    
    def search(self, query: str, top_k: int = 3) -> List[Tuple[str, float, dict]]:
        """
        Buscar documentos relevantes usando búsqueda por coincidencia de términos
        
        Args:
            query: Texto a buscar
            top_k: Número de resultados
            
        Returns:
            Lista de (documento, score, metadata)
        """
        query_terms = set(query.lower().split())
        
        # Obtener todos los documentos de la colección
        all_results = self.collection.get(
            include=["documents", "metadatas"]
        )
        
        scored_results = []
        
        for i, doc in enumerate(all_results['documents']):
            doc_lower = doc.lower()
            doc_terms = set(doc_lower.split())
            
            # Calcular puntuación basada en coincidencias
            score = 0.0
            
            # 1. Coincidencias exactas de términos (más importante)
            matching_terms = query_terms & doc_terms
            if matching_terms:
                score += 0.5 * (len(matching_terms) / len(query_terms))
            
            # 2. Coincidencias parciales (substring)
            for term in query_terms:
                if term in doc_lower:
                    score += 0.3
            
            # 3. Densidade de coincidencias
            if matching_terms:
                # Contar cuántas veces aparecen los términos
                term_count = sum(doc_lower.count(term) for term in matching_terms)
                score += 0.2 * min(term_count / len(matching_terms), 1.0)
            
            # Boost si contiene la query exacta
            if query.lower() in doc_lower:
                score += 0.5
            
            scored_results.append((
                doc,
                min(score, 1.0),  # Cap at 1.0
                all_results['metadatas'][i]
            ))
        
        # Ordenar por score y retornar top_k
        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:top_k]
    
    def stats(self) -> dict:
        """Obtener estadísticas de la BD"""
        count = self.collection.count()
        return {
            "total_documents": count,
            "collection_name": self.collection.name,
            "db_path": self.db_path
        }


def main():
    parser = argparse.ArgumentParser(description="RAG Ingestor para Red Teaming Playground")
    parser.add_argument("--reset", action="store_true", help="Reiniciar BD (borrar datos anteriores)")
    parser.add_argument("--test", action="store_true", help="Modo test: solo verificar con query de prueba")
    parser.add_argument("--query", type=str, help="Ejecutar búsqueda con query específica")
    
    args = parser.parse_args()
    
    # Cargar variables de entorno
    load_dotenv()
    
    print("\n" + "="*60)
    print("🔬 RAG INGESTOR - Red Teaming Playground")
    print("="*60 + "\n")
    
    try:
        # Inicializar ingesta or
        ingestor = RAGIngestor(reset=args.reset)
        
        if args.test:
            # Modo test: búsqueda sin ingesta
            print("🧪 MODO TEST - Verificación de funcionalidad\n")
            test_queries = ["jailbreak", "prompt injection", "embeddings"]
            
            for test_query in test_queries:
                print(f"   Buscando: '{test_query}'")
                results = ingestor.search(test_query, top_k=3)
                
                if results:
                    for doc, score, meta in results:
                        print(f"      Score: {score:.3f} | Fuente: {meta['source']}")
                        print(f"      Preview: {doc[:100]}...\n")
                else:
                    print(f"      ⚠️  Sin resultados\n")
        
        elif args.query:
            # Búsqueda personalizada
            print(f"🔍 Buscando: '{args.query}'\n")
            results = ingestor.search(args.query, top_k=5)
            
            for i, (doc, score, meta) in enumerate(results, 1):
                print(f"{i}. Score: {score:.3f}")
                print(f"   Fuente: {meta['source']}")
                print(f"   {doc[:150]}...\n")
        
        else:
            # Ingesta completa
            print("📥 Iniciando ingesta del corpus...\n")
            chunks_ingested = ingestor.ingest_corpus()
            
            stats = ingestor.stats()
            print(f"\n📊 Estadísticas:")
            print(f"   Total de chunks: {stats['total_documents']}")
            print(f"   Almacenados en: {stats['db_path']}/")
            
            # Prueba de búsqueda "jailbreak"
            print(f"\n🧪 Verificación: búsqueda de 'jailbreak'\n")
            results = ingestor.search("jailbreak", top_k=3)
            
            print(f"   Encontrados: {len(results)} resultados\n")
            for i, (doc, score, meta) in enumerate(results, 1):
                print(f"   {i}. Score: {score:.3f} (> 0.7: {'✓' if score > 0.7 else '✗'})")
                print(f"      Fuente: {meta['source']}")
                print(f"      {doc[:80]}...\n")
            
            # Validar criterio
            valid_results = sum(1 for _, score, _ in results if score > 0.7)
            if valid_results >= 3:
                print("✅ CRITERIO CUMPLIDO: 3+ chunks con score > 0.7")
            else:
                print(f"⚠️  CRITERIO NO CUMPLIDO: solo {valid_results} chunks > 0.7")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
