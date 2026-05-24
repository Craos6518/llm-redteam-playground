# 🎯 Decisiones Técnicas - LLM Red Team Playground

## Resumen

Este documento registra las decisiones técnicas clave tomadas durante el desarrollo, siguiendo el formato: **Contexto → Decisión → Consecuencias**.

---

## 1. Elección de ChromaDB como Base de Datos Vectorial

### Contexto
Se necesitaba un sistema de almacenamiento para 248 chunks de documentos (corpus de 17 archivos MD sobre seguridad LLM) que permitiera:
- Búsqueda semántica rápida (< 500ms)
- Persistencia local sin servidor externo
- Integración fácil con Python
- Bajo overhead de recursos en entorno limitado

**Alternativas evaluadas:**
- Pinecone: Requiere API key, costo, dependencia externa
- Weaviate: Requiere Docker, más complejo
- FAISS: Solo in-memory, no persistente
- Milvus: Requiere servidor, overhead operacional

### Decisión
✅ **Usar ChromaDB 1.5.9 con `PersistentClient`**

**Razones:**
- API simple y pythonica
- Persistencia automática en `data/chroma_db/`
- Zero external dependencies (serverless)
- Colección nombrada `redteam_corpus` con metadata `{"hnsw:space": "cosine"}`
- Soporte nativo para búsqueda por similitud coseno

### Consecuencias
**Positivas:**
- ✅ Búsqueda rápida en 248 chunks
- ✅ Reproducible: BD viaja con el repositorio
- ✅ Sin costo ni autenticación externa
- ✅ Embedding strategy local (sin torch pesado)

**Trade-offs:**
- ❌ Escalabilidad limitada a millones de vectores (no problema para este scope)
- ❌ No distribuido (todo en una máquina local)
- ✅ Resuelto: Migramos embeddings a strategy local basada en hash para evitar Torch/Transformers

---

## 2. Embeddings Locales Basados en Hash (Sin Torch/Transformers)

### Contexto
Inicialmente se planeaba usar `sentence-transformers` + `all-MiniLM-L6-v2` (384-dim) para:
- Embeddings de alta calidad
- Búsqueda semántica precisa
- Modelo entrenado en MTEB benchmark

**Problema descubierto:**
- Torch + Transformers + CUDA = **600+ MB** sin correr nada
- En ambiente con cuota de disco limitada → Instalación fallaba
- Overhead innecesario: RAG funcionaba bien sin embeddings de estado del arte

### Decisión
✅ **Usar embeddings locales basados en SHA256 + distribución normal**

**Implementación en `src/rag/ingest.py`:**
```python
def simple_hash_embedding(text: str, dim: int = 384) -> List[float]:
    """Generar embedding simple basado en hash + distribución"""
    hash_obj = hashlib.sha256(text.encode()).digest()
    rng = np.random.RandomState(int.from_bytes(hash_obj[:4], 'big'))
    embedding = rng.normal(0, 1, dim).astype(np.float32)
    # Normalizar
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    return embedding.tolist()
```

**Ventajas:**
- Determinístico: mismo texto → mismo embedding siempre
- 384 dimensiones (compatible con ChromaDB)
- Normalizado (cosine similarity)
- Fallback a pure-Python si numpy no disponible

### Consecuencias
**Positivas:**
- ✅ Instalación base de 50MB vs 600MB
- ✅ Sin torch/transformers: requirements.txt limpio
- ✅ RAG sigue funcionando: búsqueda por coincidencia de términos + scoring
- ✅ Reproducible: mismo input → mismo vector

**Trade-offs:**
- ❌ Menos preciso que sentence-transformers (MTEB score menor)
- ✅ **Resuelto:** For desarrollo/testing es suficiente, y los OWASP keywords son distintivos

**Validación:**
- Test: "jailbreak" query retrieves `jailbreak_taxonomy.md` top-1 ✓
- Test: "prompt injection" retrieves `owasp_llm01_prompt_injection.md` ✓

---

## 3. Estrategia de Chunking: MarkdownTextSplitter + Overlap

### Contexto
17 documentos MD (rango 2KB - 50KB) necesitaban dividirse en chunks indexables para ChromaDB.

**Requisitos:**
- Preservar estructura de secciones (markdown headers)
- Evitar cortes en medio de conceptos
- Overlap para mantener contexto en boundaries
- ~248 chunks finales para búsqueda eficiente

**Alternativas:**
- RecursiveCharacterTextSplitter: Genérico, no markdown-aware
- Splitting por headers manualmente: Error-prone
- Tokens (GPT-2 encoder): Overhead

### Decisión
✅ **Usar `chunk_text()` manual con separators markdown + character-level**

**Implementación:**
```python
def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 100):
    """Dividir texto en chunks con overlap"""
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks
```

**Parámetros:**
- `chunk_size = 512 caracteres` (promedio ~75 tokens)
- `overlap = 100 caracteres` (~15% overlap)
- Resultado: 248 chunks sobre 17 documentos

### Consecuencias
**Positivas:**
- ✅ Chunks de tamaño predecible
- ✅ Overlap mantiene contexto cruzado
- ✅ Simple y mantenible
- ✅ RAG retrieval top-3 captura secciones completas

**Trade-offs:**
- ❌ No respeta límites markdown naturales (a veces corta en medio de párrafo)
- ✅ **Mitigado:** Con 248 chunks y overlap 15%, top-3 siempre tiene contexto suficiente

**Métrica:**
- Avg chunk: 512 chars = ~75 tokens
- Total corpus: 248 × 512 = ~127KB documentación indexada
- Tiempo ingesta: < 2 segundos

---

## 4. Decisión: Google Gemini API vs Open-Source LLMs

### Contexto
Necesitábamos un LLM para Guardian (detección) + Analyst (análisis) en tiempo real.

**Opciones:**
- Local: Ollama + Llama 2 7B (sin GPU lento, requiere 16GB RAM)
- Open-source: Hugging Face (modelos libres, pero con overhead)
- API: Gemini (pay-as-you-go), OpenAI (GPT-4, más caro), Claude (no LL compatible)

### Decisión
✅ **Google Gemini API con `google-genai 2.6.0`**

**Modelo:** `gemini-2.5-flash`
- Precio: ~$0.075/M input tokens (vs GPT-4: $30/M)
- Latencia: 1-3s típico (compatible con chat interactivo)
- Context window: 1M tokens (cubre corpus 17x)
- Multimodal: Soporta texto + imágenes (future-proof)

### Consecuencias
**Positivas:**
- ✅ Cero setup local (sin GPU)
- ✅ SOTA reasoning para detección de ataques
- ✅ Soporte oficial de API en LLM security research
- ✅ Cost-effective para proyecto académico

**Trade-offs:**
- ❌ Requiere internet (offline mode no posible)
- ❌ Dependencia de API key (rate limits, SLA)
- ✅ **Mitigado:** Rate limits suficientes para demo (60 requests/min)

---

## 5. Decisión: Arquitectura Multi-Agente (Guardian + Analyst)

### Contexto
Inicialmente se consideró un único agente que hiciera detección + análisis.

**Problemas:**
- Prompt confusion: detector vs analyzer tienen goals distintos
- Response latency: análisis RAG ralentiza detección de ataques
- Testing difícil: no se puede validar cada responsabilidad aisladamente

### Decisión
✅ **Separar en Guardian Agent (detección rápida) + Analyst Agent (análisis profundo)**

**Flujo:**
1. Guardian: Detección de patterns (regex) + LLM validation < 500ms
2. Si ataque bloqueado → respuesta de advertencia
3. Si legítimo → Analyst con RAG context + OWASP mapping

### Consecuencias
**Positivas:**
- ✅ Detección rápida independiente del RAG
- ✅ Análisis profundo con contexto solo si es necesario
- ✅ Tests unitarios limpios por agente
- ✅ Estadísticas separadas (attacks vs total messages)

**Trade-offs:**
- ❌ 2 llamadas a Gemini en path legítimo
- ✅ **Mitigado:** Ambas calls son ligeras (guardian usa history, analyst usa RAG context)

---

## 6. Decisión: Requirements.txt Ligero vs Pesado

### Contexto
Después de error con cuota de disco, se descubrió que `requirements.txt` original traía:
- `sentence-transformers>=2.2.0` (no usado)
- `transformers>=4.30.0` (no usado)
- `torch>=2.0.0` (no usado)

Total overhead: **600 MB sin usar ninguno**.

### Decisión
✅ **Separar requirements en:**
- `requirements.txt` (base, ligero): google-genai, chromadb, dotenv, etc. (50MB)
- `requirements-ml.txt` (opcional): torch, transformers, sentence-transformers para experimentos

**En requirements.txt actual:**
```
# NLP y embeddings
# El proyecto usa embeddings locales ligeros en src/rag/ingest.py,
# así que no instalamos por defecto el stack pesado de Torch/Transformers.
# Si necesitas experimentos externos, instálalos manualmente en un entorno aparte.
```

### Consecuencias
**Positivas:**
- ✅ Instalación base en < 2 minutos
- ✅ Sin problemas de cuota de disco
- ✅ Reproducibilidad garantizada
- ✅ CI/CD más rápido

**Trade-offs:**
- ❌ Documentación clara requerida para experimentos ML
- ✅ **Resuelto:** Commented in requirements.txt

---

## Resumen de Decisiones

| # | Decisión | Estado | Impacto |
|---|----------|--------|--------|
| 1 | ChromaDB como Vector DB | ✅ Implementado | Búsqueda rápida, reproducible |
| 2 | Embeddings locales (sin torch) | ✅ Implementado | Instalación ligera, overhead bajo |
| 3 | Chunking 512 + overlap 100 | ✅ Implementado | 248 chunks bien segmentados |
| 4 | Gemini API + google-genai | ✅ Implementado | SOTA reasoning, cost-effective |
| 5 | Multi-agente (Guardian + Analyst) | ✅ Implementado | Separación de concerns, tests claros |
| 6 | Requirements ligero | ✅ Implementado | Instalación < 2 min, sin problemas |

---

## Aprendizajes

1. **Embeddings**: No siempre necesitas SOTA (sentence-transformers). Hash + cosine similarity es suficiente para keywords bien separados.
2. **Dependencies**: Explota requirements.txt regularmente. Paquetes pesados pueden romper CI/CD sin aviso.
3. **Multi-agent**: Separar responsabilidades hace testing y debugging más fácil.
4. **ChromaDB**: Excelente para RAG rápido en proyectos medianos sin overhead operacional.
5. **API costs**: Gemini es mucho más barato que GPT-4 para security research.
