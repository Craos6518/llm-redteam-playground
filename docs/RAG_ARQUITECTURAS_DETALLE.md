# Las arquitecturas RAG del proyecto — análisis detallado

> Documento técnico de referencia. Analiza **qué RAG hay implementado realmente** (no lo que dice el README), cómo funciona cada uno a nivel de código, qué parámetros usa, qué problemas tiene y cómo se traduce al stack n8n + Ollama + Supabase.
>
> Verificado contra: `src/rag/ingest.py`, `src/rag/retriever.py`, `src/rag/naive_rag.py`, `src/rag/advanced_rag.py`, `src/agents/analyst.py`, `src/main.py`, `eval/benchmark_rag.py`, `tests/`, `data/corpus/`.

---

## 0. Mapa mental: no hay 2 RAG, hay 4 rutas

En el código conviven **cuatro formas distintas de "recuperar + generar"**, aunque la UI solo expone tres:

| # | Ruta | Archivo | ¿Vectorial? | Seleccionable en UI | Uso real |
|---|---|---|---|---|---|
| A | **Retriever léxico + boosts** | `src/rag/retriever.py` | ❌ No (lee todo) | ✅ `retriever` (default) | Camino que usa `AnalystAgent` y el default de Streamlit |
| B | **Naive RAG** | `src/rag/naive_rag.py` | ⚠️ Sí, pero con embedding de consulta falso | ✅ `naive` | Baseline comparativo |
| C | **Advanced RAG** | `src/rag/advanced_rag.py` | ⚠️ Igual + expansion + cross-encoder | ✅ `advanced` | Demostración de pre/post-retrieval |
| D | **AnalystAgent (RAG + OWASP)** | `src/agents/analyst.py` | ❌ Usa la ruta A | ❌ No | Benchmark (`eval/`) y análisis con mapeo OWASP |

Y una **quinta pieza** que el benchmark etiqueta como arquitectura pero **no es RAG**:

| # | Ruta | Archivo | ¿Recupera? | Problema |
|---|---|---|---|---|
| E | "Guardian Agent" | `src/agents/analyst.py` vía `eval/benchmark_rag.py` | Sí, pero el evaluador **descarta los contextos** | Se evalúa como RAG con `contexts=[]` → 0 en 3 de 4 métricas |

La confusión conceptual es la primera cosa a corregir antes de automatizar: **n8n necesita saber cuántas llamadas hace cada ruta y qué contrato devuelve**, y ahora mismo hay cuatro pipelines distintos con nombres parecidos.

---

## 1. Capa común: ingesta, chunking y embeddings

Todo el RAG depende de esta base. Es donde están los problemas más importantes.

### 1.1 Pipeline de ingesta (`src/rag/ingest.py`)

```
data/corpus/*.md  (27 archivos)
        │
        ▼
lectura completa a string UTF-8
        │
        ▼
chunk_text(text, 512, 100)     ← corte por CARACTERES
        │
        ▼
collection.add(ids, documents, metadatas)   ← 1 escritura por chunk
        │
        ▼
ChromaDB persistente en data/chroma_db/
colección: redteam_corpus, hnsw:space = cosine
```

Código exacto del chunking:

```python
for i in range(0, len(text), chunk_size - overlap):
    chunks.append(text[i:i + chunk_size])
```

- **Tamaño:** 512 caracteres (no tokens).
- **Paso:** `512 - 100 = 412` caracteres.
- **Solape real:** 100 caracteres ≈ 19,5 % del chunk.
- **Fórmula del número de chunks por documento:** `ceil(len(doc) / 412)`.

### 1.2 Corpus real medido

| Métrica | Valor |
|---|---|
| Documentos | **27** (el README sigue diciendo 17) |
| Caracteres totales | **520 556** |
| Chunks esperados con 512/100 | **1 276** (coincide con el README, calculado por archivo) |
| Documento medio | ~19 279 caracteres |
| Documento más grande | `data_poisoning.md` — 77 403 chars → ~188 chunks |
| Documento más pequeño | `owasp_llm01_prompt_injection.md` — 2 429 chars → ~6 chunks |

Consecuencia inmediata: **un solo documento aporta el 15 % del índice**. `data_poisoning.md` (188 chunks) e `indirect_promt_injection.md` (173) dominan la recuperación por pura masa estadística, aunque el documento canónico de OWASP LLM01 solo tenga 6 chunks. Eso sesga cualquier top-k.

### 1.3 Problemas del chunking actual

1. **Corta por carácter, no por estructura.** No respeta encabezados, listas, tablas ni bloques de código. Un chunk puede empezar a mitad de palabra y terminar a mitad de una tabla Markdown.
2. **No guarda la ruta de encabezados.** `metadata` solo tiene `source`, `chunk_idx`, `total_chunks`. Se pierde el `# H1 > ## H2` al que pertenece el fragmento, que es la señal más barata para re-ranking y filtrado.
3. **Overlap uniforme.** 100 caracteres fijos para documentos de 2 KB y de 77 KB; en tablas o listas numeradas el solape no preserva unidades semánticas.
4. **IDs con huecos.** El `doc_id` usa el índice del `enumerate`, pero se saltan chunks vacíos (`if not chunk.strip(): continue`). Quedan IDs tipo `x_chunk_3, x_chunk_4, x_chunk_6`, y `total_chunks` cuenta también los vacíos → inconsistencia menor pero real en trazabilidad.
5. **Escritura una a una.** 1 276 `collection.add()` individuales; no hay batch ni transacción. Para reindexar en Supabase conviene hacer upsert por lotes de 50–100.

### 1.4 El problema crítico: los embeddings

Aquí está la deuda técnica que invalida el discurso "RAG vectorial":

| Momento | Quién genera el vector | Modelo | Dimensión |
|---|---|---|---|
| **Ingesta** | ChromaDB (implícito, `collection.add` sin embeddings) | `all-MiniLM-L6-v2` (ONNX, default de Chroma) según el comentario del propio `ingest.py` | 384 |
| **Consulta en Naive** | `NaiveRAG._get_query_embedding` | **SHA-256 → `RandomState` → `normal(0,1,384)` → normalizado** | 384 |
| **Consulta en Advanced** | `AdvancedRAG._get_query_embedding` | idéntico hash | 384 |
| **Consulta en Retriever** | no hay embedding | — | — |

Código real:

```python
hash_obj = hashlib.sha256(query.encode()).digest()
rng = np.random.RandomState(int.from_bytes(hash_obj[:4], "big"))
embedding = rng.normal(0, 1, 384).astype(np.float32)
embedding = embedding / np.linalg.norm(embedding)
```

Eso genera un **vector unitario pseudoaleatorio determinista por string**. No tiene nada que ver con el significado. La similitud coseno entre ese vector y el embedding semántico de un documento es, estadísticamente, la de dos vectores independientes en 384 dimensiones:

- media ≈ 0
- desviación típica ≈ `1/√384 ≈ 0,051`

Es decir: los `score` de Naive y Advanced deberían rondar **0 ± 0,05**, y el "top-k" es esencialmente **un muestreo aleatorio** del corpus, con desempates por el orden interno del índice HNSW. Cualquier resultado que parezca coherente en esas rutas proviene del LLM (que igual responde bien por conocimiento propio), **no del retrieval**.

> Nota fina: `similarity = 1 - distance` con espacio cosine. Si `distance ∈ [0,2]`, la similitud puede ser negativa; los tests asumen `0 ≤ score ≤ 1`, que no está garantizado.

**Qué se puede salvar:** la ruta A (léxico) no usa embeddings, y por eso el criterio de demostración (`"ignora todas las instrucciones"` → top-1 = `owasp_llm01_prompt_injection.md`) sí se cumple. La demo funciona; el RAG vectorial no.

---

## 2. Ruta A — Retriever léxico con boosts (`src/rag/retriever.py`)

### 2.1 Qué hace

No busca por similitud: **trae los 1 276 documentos completos a memoria y los puntúa con reglas**. Es un motor de scoring tipo "BM25 de pobre", con tres señales.

```
query
  │
  ├─ _classify_threat(query)        ← keywords por categoría
  │
  ├─ collection.get(include=[documents, metadatas])   ← TODO el corpus
  │
  ├─ por cada uno de los 1 276 chunks:
  │     _calculate_relevance_score(doc, query, source, threat_category)
  │
  ├─ sort desc (estable → empates = orden de inserción)
  │
  └─ top_k = 3
```

### 2.2 Clasificador de amenaza

```python
THREAT_KEYWORDS = {
  "prompt_injection": ["injection","prompt","ignora","ignore","bypass","circumvent","override"],
  "jailbreak":        ["jailbreak","jailbreaking","roleplay","pretend","assume identity"],
  "data_poisoning":   ["poison","poisoning","data","training","contamination"],
  "leakage":          ["leak","disclosure","sensitive","confidential","reveal","extract"],
  "excessive_agency": ["agency","action","autonomy","execute","run"],
}
```

- Cuenta **cuántas keywords distintas aparecen**, no cuántas veces.
- Gana la categoría con más coincidencias; si hay empate, gana la primera en el diccionario → **`prompt_injection` siempre desempata**.
- `"prompt"` y `"data"` son términos demasiado genéricos: casi cualquier consulta en español/inglés que mencione "prompt" cae en `prompt_injection`, y "datos" en inglés (`data`) cae en `data_poisoning`.

### 2.3 Fórmula de relevancia

```python
score  = 0.40 * (|query_terms ∩ doc_terms| / |query_terms|)     # coincidencia exacta
score += 0.30 * (|términos que aparecen como substring| / |query_terms|)
score += 0.30  si source ∈ THREAT_SOURCE_PRIORITY[threat_category]
score += 0.20  si la query completa aparece en el documento
score  = min(score, 1.0)
```

Detalles que importan:

- **Tokenización con `.split()`**: incluye puntuación (`¿qué`, `llms?`) y stopwords (`de`, `la`, `los`). El denominador `|query_terms|` se infla con palabras vacías → consultas largas en español se penalizan solas.
- **Sin IDF**: una coincidencia en "de" vale lo mismo que una en "jailbreak".
- **El boost por fuente es binario y de 0,30**: si el chunk pertenece a `owasp_llm01_prompt_injection.md`, sube 30 puntos de golpe, independientemente del contenido real del chunk.
- **Tope en 1,0 con suma máxima 1,2** → muchos documentos pueden empatar en 1,0. Como el `sort` de Python es estable, **el empate lo resuelve el orden de la base**, no la relevancia. De ahí que la guía muestre "Relevancia: 100.0 %" con tanta facilidad.

### 2.4 Ejemplo trabajado (ilustrativo)

Query: `"ignora todas las instrucciones"` → términos `{ignora, todas, las, instrucciones}`.

| Documento | Términos | Substring | Boost fuente | Exacta | Score |
|---|---|---|---|---|---|
| `owasp_llm01_prompt_injection.md` (chunk con la frase) | 4/4 → 0,40 | 4/4 → 0,30 | +0,30 | +0,20 | **1,00 (cap)** |
| `jailbreak_taxonomy.md` | 2/4 → 0,20 | 3/4 → 0,22 | 0 | 0 | **0,42** |
| `data_poisoning.md` (menciona "instrucciones" de entrenamiento) | 1/4 → 0,10 | 2/4 → 0,15 | 0 | 0 | **0,25** |

### 2.5 Coste y comportamiento

- **Complejidad:** O(N × |q| × longitud_doc) por el test de substring → con 1 276 chunks y ~5 términos es rápido (< 500 ms), pero crece linealmente con el corpus.
- **Memoria:** carga los 1 276 documentos completos en cada consulta (no hay caché).
- **Determinista:** sí, mismo corpus + misma query → mismo resultado.
- **Coste LLM:** 0 (el retrieval en sí no llama al modelo).

### 2.6 Fortalezas y fallas

| Fortalezas | Fallas |
|---|---|
| Cero dependencias de embeddings | No generaliza: "cómo saltarse las reglas" ≠ "ignora instrucciones" |
| Explicable y auditable (score por señal) | Falsos positivos por keywords genéricas |
| Rápido para 1,3k chunks | No escala (lee todo) |
| Cumple el criterio OWASP LLM01 | Empates a 1,0 resueltos por orden de inserción |
| Funciona sin GPU ni modelos | Monolingüe de facto: el corpus está en inglés y las queries en español |

---

## 3. Ruta B — Naive RAG (`src/rag/naive_rag.py`)

### 3.1 Pipeline

```
query
  │
  ├─ _get_query_embedding(query)          ← hash → vector 384d (ver §1.4)
  │
  ├─ collection.query(n_results=4)        ← top_k = 4
  │
  ├─ _build_context(chunks)               ← "[Fragmento i] (Fuente, Relevancia %)"
  │
  ├─ system_prompt.format(context, query)
  │
  └─ LLMClient.generate(prompt, system_prompt=self.system_prompt)
```

### 3.2 Parámetros reales

| Parámetro | Valor | Dónde |
|---|---|---|
| `top_k` | **4** | `NaiveRAG.__init__` |
| Colección | `redteam_corpus` | hardcodeado |
| `db_path` | `data/chroma_db` | `RAG_DB_PATH` |
| `model_name` | `GUARDIAN_MODEL` (default `gemini-2.5-flash`) | **solo etiqueta**, no fuerza el modelo |
| `n_results` | `top_k` | `collection.query` |
| Contexto | 4 × 512 chars ≈ 2 048 chars ≈ 500–600 tokens | estimado |

### 3.3 Prompt

```python
system_prompt = (
    "Eres un asistente experto. Responde a la consulta únicamente "
    "utilizando el siguiente contexto: {context}. Consulta: {query}"
)
```

Y la llamada:

```python
answer = self.llm_client.generate(
    prompt=prompt,                 # plantilla YA rellenada
    system_prompt=self.system_prompt,  # plantilla SIN rellenar (con "{context}")
)
```

Esto tiene dos consecuencias:

1. **Doble instrucción**: el mismo texto va como `system` y como `user`, con la instrucción de CoT añadida al final (`LLM_COT=1`). El modelo recibe "responde solo con el contexto" dos veces.
2. **Placeholders literales en el system message**: el modelo ve `{context}` y `{query}` sin sustituir. En modelos pequeños (Ollama qwen3:4b) esto puede confundir el formato de salida.

### 3.4 Contrato de salida

```json
{
  "query": "¿Qué es prompt injection?",
  "answer": "texto generado",
  "retrieved_chunks": [
    {"content": "...", "score": 0.03, "source": "owasp_llm01_prompt_injection.md", "chunk_idx": 2}
  ],
  "num_chunks": 4,
  "model": "gemini-2.5-flash"
}
```

`model` es el **label configurado**, no `llm_client.last_model`. Si el fallback cae a Ollama, el contrato sigue diciendo "gemini-2.5-flash". Para auditoría esto es un bug silencioso: hay que devolver `last_provider` / `last_model`.

### 3.5 Qué está bien y qué no

| Bien | Mal |
|---|---|
| Pipeline canónico y fácil de portar a n8n | Embedding de consulta no semántico → top-4 aleatorio |
| Contexto formateado con fuente y score | Doble system prompt y placeholders sin rellenar |
| Manejo de error que devuelve texto, no excepción | `model` reportado no es el real |
| Tests de contrato completos (init, retrieve, context, generate, top_k) | `score = 1 - distance` puede ser negativo; test asume [0,1] |
| — | No usa filtros por metadato ni deduplicación |

### 3.6 Cuándo tiene sentido

- **Como baseline de comparación** (es su rol declarado).
- **Como plantilla del workflow n8n**: una llamada de embedding + una RPC + una llamada de chat. Es el camino más simple de producción.
- **Nunca** como implementación final con el embedding actual.

---

## 4. Ruta C — Advanced RAG (`src/rag/advanced_rag.py`)

Es la ruta más elaborada: **pre-retrieval (query expansion) + retrieval multi-query + post-retrieval (cross-encoder) + generación**.

### 4.1 Pipeline completo

```
query original
   │
   ├─ 1. EXPANSIÓN (1 llamada LLM)
   │     prompt: "Genera 3 variaciones semánticamente diferentes..."
   │     parser: líneas que empiezan por dígito, "-" o "•"
   │     salida: [query] + hasta 3 variantes
   │
   ├─ 2. RETRIEVAL MULTI-QUERY
   │     por cada una de las 4 queries:
   │        embedding hash → collection.query(n_results=10)
   │     hasta 40 chunks candidatos
   │
   ├─ 3. FUSIÓN Y DEDUPLICACIÓN
   │     seen_content = set(); hash(doc) como clave
   │     guarda el primer chunk, descarta duplicados exactos
   │
   ├─ 4. RE-RANKING (post-retrieval)
   │     CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
   │     pairs = [(query, doc) ...]   ← OJO: solo con la query ORIGINAL
   │     predict → scores (logits) → sort desc → top_k = 4
   │
   ├─ 5. RECONSTRUCCIÓN DE METADATOS
   │     busca el chunk original por igualdad de contenido (lineal)
   │
   ├─ 6. CONTEXTO + GENERACIÓN (1 llamada LLM)
   │     prompt con "[Fragmento i] (Fuente, Cross-Encoder Score: x.xxxx)"
   │
   └─ respuesta
```

### 4.2 Pre-retrieval: query expansion

Prompt exacto:

```
Genera {expansion_count} variaciones semánticamente diferentes
de la siguiente consulta para mejorar la recuperación en un sistema RAG sobre seguridad en LLMs.

Consulta original: "{query}"

Requisitos:
- Cada variación debe capturar un aspecto diferente o reformulación
- Mantener el mismo intent y dominio (ciberseguridad LLMs)
- Responde SOLO con una lista numerada, una por línea
```

Parser:

```python
for line in variations_text.split("\n"):
    line = line.strip()
    if line and (line[0].isdigit() or line.startswith("-") or line.startswith("•")):
        clean = line.lstrip("0123456789.-• ").strip()
        if clean:
            variations.append(clean)
variations = variations[: expansion_count]
all_queries = [query] + variations
```

Fragilidades concretas:

1. **Formatos no contemplados**: `**1.** variante`, `1) variante`, `Variante 1:` → no empiezan por dígito/guion/bullet → se descartan. El modelo puede devolver 3 variaciones y el parser quedarse con 0.
2. **`lstrip` agresivo**: elimina *cualquier* carácter inicial del conjunto `0-9 . - •` + espacio. Una variación que empiece por "2025" pierde los dígitos; una que empiece por "1.1" también.
3. **Sin fallback útil**: si falla la llamada o el parser, devuelve `[query]` y el pipeline sigue como si nada. No se registra que no hubo expansión (`expanded_queries` lo delata, pero nadie lo monitorea).
4. **Coste**: 1 llamada LLM adicional **antes** de saber si hacía falta.

### 4.3 Retrieval multi-query y fusión

- `initial_retrieve_k = 10` por query, 4 queries → **hasta 40 candidatos**.
- Deduplicación por `hash(doc)` (hash de string, aleatorizado por proceso en Python; consistente dentro de la ejecución, no entre ejecuciones). No hay fusión ponderada tipo RRF: se concatenan y se quedan con la primera aparición.
- **No se conserva el score de cada query** para fusionar; solo se usa `original_score = 1 - distance` (que, con el embedding hash, es ruido).
- Con el embedding roto, la expansión no aporta diversidad semántica: multiplica muestreos aleatorios del mismo índice. El cross-encoder es lo único que introduce señal real.

### 4.4 Post-retrieval: cross-encoder

```python
from sentence_transformers import CrossEncoder
self._model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
scores = self._model.predict([(query, doc) for doc in documents])
```

| Aspecto | Detalle |
|---|---|
| Modelo | `cross-encoder/ms-marco-MiniLM-L-6-v2` (MiniLM-L6, ~22M params) |
| Entrenamiento | MS MARCO, pasajes web **en inglés** |
| Entrada | par `(query, documento)` — evalúa conjuntamente, no por embeddings |
| Salida | **logits** (típicamente −11 a +11), no probabilidad |
| Orden | mayor = más relevante |
| Top final | `top_k = 4` |
| Coste | 1 inferencia por par → hasta 40 pares por consulta |
| Dependencia | `sentence-transformers` **no está en `requirements.txt`** |

Consecuencias:

- **Idioma**: corpus en inglés, queries en español → el cross-encoder multilingüe no es; la relevancia que estima es débil para consultas en español. Un modelo como `BAAI/bge-reranker-v2-m3` (multilingüe) sería más adecuado.
- **Escala de score**: se muestra `Cross-Encoder Score: 3.4210` sin sigmoide ni normalización. No es comparable entre consultas ni sirve como umbral absoluto.
- **`original_score`** se conserva pero es ruido con el embedding actual.
- **Reconstrucción de metadatos**: `next(c for c in retrieved_chunks if c["content"] == reranked_item["content"])` → búsqueda lineal O(n²), aceptable con 40 elementos, pero síntoma de que el reranker devuelve solo texto y pierde la metadata.

### 4.5 Generación

```python
self.system_prompt = (
    "Eres un asistente experto en seguridad de LLMs. Responde a la consulta "
    "utilizando únicamente el siguiente contexto recuperado y re-ordenado "
    "por relevancia: {context}. Consulta: {query}"
)
```

Igual que en Naive: se pasa como `system` **sin formatear** (con `{context}` literal) y como `prompt` formateado. Además, ese mismo `system_prompt` se usa en `_expand_query`, donde aparece la instrucción de "responde solo con el contexto re-ordenado" mientras se le pide generar variaciones de la query. **Contradicción de instrucciones** que degrada la expansión, sobre todo en modelos pequeños.

### 4.6 Contrato de salida

```json
{
  "query": "¿Qué es prompt injection?",
  "answer": "texto",
  "retrieved_chunks": [
    {
      "content": "...",
      "rerank_score": 3.421,
      "original_score": 0.02,
      "source": "owasp_llm01_prompt_injection.md",
      "chunk_idx": 1,
      "query_used": "¿Qué es prompt injection?"
    }
  ],
  "expanded_queries": ["original", "variante 1", "variante 2", "variante 3"],
  "num_chunks": 4,
  "model": "gemini-2.5-flash"
}
```

### 4.7 Coste real por consulta

| Etapa | Llamadas | Notas |
|---|---|---|
| Query expansion | 1 LLM | Puede fallar y degradar silenciosamente a 0 expansiones |
| Embeddings de query | 4 (hash, locales) | Coste ~0, pero inútiles |
| Búsquedas | 4 × top-10 | 40 candidatos antes de dedup |
| Re-ranking | 1 batch de ≤40 pares | CPU/GPU; modelo no instalado por defecto |
| Generación | 1 LLM | Contexto final ≈ 2 048 chars |
| **Total** | **2 LLM + 1 cross-encoder + 4 búsquedas** | ~2× la latencia de Naive como mínimo |

### 4.8 Cuándo tiene sentido

- Tiene sentido **con embeddings reales** y **reranker multilingüe**; ahí la expansión + rerank sí mejora `context_recall` en preguntas vagas.
- En su estado actual sirve como **demostración académica de pre/post-retrieval**, no como componente de producción.
- Para n8n: no conviene replicar la expansión en nodos si el modelo local es pequeño; mejor un servicio Python `/rag/advanced` o dejarla fuera del camino crítico.

---

## 5. Ruta D — AnalystAgent: RAG + mapeo OWASP (`src/agents/analyst.py`)

### 5.1 Qué hace distinto

No es una arquitectura de retrieval nueva: **usa la ruta A** (`RAGRetriever`, top_k=3), pero cambia el *prompt de generación* y añade clasificación OWASP + formato de informe.

```
user_message
   │
   ├─ retriever.retrieve(user_message, top_k=3)     ← léxico, 3 chunks
   │
   ├─ _build_analysis_prompt(...)
   │     · incluye OWASP de referencia
   │     · TRUNCA cada chunk a 300 caracteres
   │
   ├─ LLMClient.generate(prompt, system_prompt=ANALYST)
   │
   └─ _format_analysis(...)  → caja ASCII + fuentes
```

### 5.2 Mapa de amenazas

```python
THREAT_TO_OWASP = {
  "prompt_injection": "LLM01:2025 – Prompt Injection",
  "jailbreak":        "LLM02:2025 – Insecure Output Handling",
  "data_poisoning":   "LLM04:2025 – Data and Model Poisoning",
  "leakage":          "LLM07:2025 – System Prompt Leakage",
  "excessive_agency": "LLM06:2025 – Excessive Agency",
}
```

Inconsistente con `exporter.py` y con `main.py` (que mapea `jailbreak → LLM01`, `leakage → LLM06`, `excessive_agency → LLM08`). **Tres catálogos distintos en tres archivos** → los reportes y el benchmark no son comparables. Es el saneamiento P0 antes de automatizar.

### 5.3 Limitación estructural

**Trunca el contexto a 300 caracteres por chunk** (`content = chunk.get("content", "")[:300]`). Con 3 chunks, el Analyst ve como máximo ~900 caracteres de evidencia, mientras que Naive/Advanced ven ~2 048. Es decir: la ruta que produce los informes de auditoría es la que **menos contexto** usa.

### 5.4 Bug de modelo en modo proveedor fijo

```python
self.model = PROVIDER_MODELS["gemini"]          # "gemini-2.5-flash"
...
self.llm_client.generate(..., model=self.model)
```

Con `LLM_PROVIDER=auto` no rompe (el adaptador ignora el override para candidatos distintos del proveedor preferido). Pero con `LLM_PROVIDER=ollama` el `model` forzado es un ID de Gemini y el adaptador lo aplica justo al candidato `ollama` → **404/400**. Es exactamente el escenario al que se migra. Hay que eliminar el `model=` y dejar que `PROVIDER_MODELS` resuelva.

---

## 6. Comparativa lado a lado

### 6.1 Operaciones por consulta

| | A. Retriever | B. Naive | C. Advanced | D. Analyst |
|---|---|---|---|---|
| Embeddings de query | 0 | 1 (falso) | 4 (falsos) | 0 |
| Búsquedas | 1 scan completo | 1 × top-4 | 4 × top-10 | 1 scan completo |
| Candidatos evaluados | **1 276** | 4 | ≤ 40 | **1 276** |
| Cross-encoder | no | no | ≤ 40 pares | no |
| Llamadas LLM | 0 (+1 generación) | 1 | **2** | 1 |
| Contexto al LLM | 3 × 512 | 4 × 512 | 4 × 512 | 3 × **300** |
| Determinista | ✅ | ❌ | ❌ | ✅ retrieval / ❌ generación |
| Dependencia extra | — | chromadb | chromadb + sentence-transformers | chromadb |

### 6.2 Calidad esperada (cualitativa, con el código actual)

| Criterio | A | B | C | D |
|---|---|---|---|---|
| Relevancia del retrieval | Media (léxica) | **Baja (aleatoria)** | **Baja (aleatoria)** | Media (léxica) |
| Cobertura semántica | Baja | Nula | Nula | Baja |
| Resistencia a sinónimos | Muy baja | — | — | Muy baja |
| Explicabilidad | **Alta** | Baja | Media | Alta |
| Coste/latencia | **Bajo** | Medio | **Alto** | Bajo |
| Listo para producción | Con reservas | No | No | Con reservas |

### 6.3 Qué ruta elegir

- **Demo / clase / criterio OWASP**: ruta A (es la que cumple).
- **Baseline medible**: ruta B **después de arreglar el embedding**.
- **Investigación de pre/post-retrieval**: ruta C **con embedding real + reranker multilingüe**.
- **Reportes de auditoría**: ruta D, pero sin truncar a 300 chars y con catálogo OWASP unificado.
- **Producción / n8n**: B corregida (lineal, 1 embedding + 1 RPC + 1 chat). C solo si el presupuesto de latencia lo permite.

---

## 7. La evaluación: qué mide realmente `eval/benchmark_rag.py`

### 7.1 Diseño

- **Dataset:** 5 preguntas (prompt injection, jailbreak, data poisoning, leakage, excessive agency), cada una con `ground_truth` extenso.
- **Arquitecturas:** naive, advanced, guardian.
- **Métricas:** `context_precision`, `context_recall`, `faithfulness`, `answer_relevancy`.
- **Salidas:** `eval/results_comparison.csv` y `.md`, más tabla por consola.

### 7.2 Problema 1: RAGAS no está instalado

```python
try:
    from ragas import evaluate
    ...
except ImportError:
    RAGAS_AVAILABLE = False
    # métricas manuales
```

`ragas` **no figura en `requirements.txt`**, así que en una instalación limpia siempre se usan las métricas de reemplazo, que no son RAGAS. Y las de reemplazo tienen fallos de diseño:

| Métrica | Implementación real | Efecto |
|---|---|---|
| Context Precision | `any(término del ground truth en el chunk)` | El ground truth contiene "de", "la", "los" → **casi todo chunk coincide → 1,0 siempre** |
| Context Recall | cuenta **chunks** que comparten términos y divide por `len(gt_terms)` | Con 4 chunks y ~60 términos → **máximo ≈ 4/60 = 0,067** |
| Faithfulness | proporción de oraciones con *alguna* palabra presente en el contexto | Muy laxa → 1,0 en Naive |
| Answer Relevancy | solapamiento de términos pregunta/respuesta | Ignora el contexto; mide vocabulario, no relevancia |

Eso explica exactamente los números observados: `CP = 1.0000` en naive y advanced, `CR = 0.0553 / 0.0693`, `F = 1.0 / 0.945`.

### 7.3 Problema 2: "Guardian" no es una arquitectura RAG evaluable

```python
analysis = analyst.analyze(query, threat_category="unknown")
...
contexts = []   # Guardian no usa retrieval del corpus de la misma manera
```

Se pasan `contexts=[]` → `context_precision=0`, `context_recall=0`, `faithfulness=0` **por construcción**, no por mérito. El 0,6096 de `answer_relevancy` es el único dato real, y esa métrica ni siquiera usa contextos.

### 7.4 Problema 3: el artefacto está inconsistente

`eval/results_comparison.md` muestra:

```
| naive    | 1.0000 | 0.0553 | 1.0000 | 0.4271 |
| advanced | 1.0000 | 0.0693 | 0.9450 | 0.6746 |
| guardian | 0.0000 | 0.0000 | 0.0000 | 0.6096 |
```

Promedios reales: naive **0,6206**, advanced **0,6722**, guardian **0,1524**. Pero el ranking del mismo archivo dice:

```
| 1 | naive    | 0.1524 |
| 2 | advanced | 0.1524 |
| 3 | guardian | 0.1524 |
```

**Los tres con 0,1524** y "mejor = naive". Ese bloque no corresponde a la tabla: es un artefacto viejo o mal regenerado. No se puede citar en una presentación sin regenerarlo.

### 7.5 Cómo hacerla defendible

1. Instalar `ragas` y fijar versión; o usar un **LLM-as-judge** explícito (mismo Ollama) con rúbrica.
2. **20–30 preguntas**, incluyendo *controles negativos* (preguntas fuera del corpus) para detectar sobre-recuperación.
3. Métricas separadas: **retrieval** (precision@k, recall@k, MRR, nDCG) y **generación** (faithfulness, relevancy).
4. Guardar en `rag_eval_runs`: arquitectura, modelo, dimensión de embedding, hash del corpus, fecha.
5. Comparar siempre contra el mismo índice; si cambia el embedding, **todo se re-ejecuta**.

---

## 8. Diagnóstico priorizado

### P0 — bloquea cualquier migración

1. **Embeddings de consulta falsos** en `naive_rag.py:66` y `advanced_rag.py:105`.
   - Acción: usar `Ollama /api/embed` (o el mismo modelo del índice) para la query; guardar `embedding_model` y `dim` en metadata de la colección.
   - Criterio: `score` deja de estar en ±0,05 y el top-1 cambia según la semántica.
2. **Tres catálogos OWASP distintos** (`analyst.py`, `exporter.py`, `main.py`).
   - Acción: un módulo `owasp.py` con el catálogo único 2025 y severidades.
3. **`sentence-transformers` no está en `requirements.txt`** → Advanced RAG falla en instalación limpia.
   - Acción: añadirlo (o mover Advanced a un extra opcional) y documentar el modelo.

### P1 — calidad y trazabilidad

4. Chunking por caracteres sin metadatos de encabezado → cambiar a chunking Markdown-aware con `chunk 800–1200 chars`, `overlap 10–15 %`, y `metadata.headings`.
5. `model` reportado ≠ modelo real → devolver `last_provider` / `last_model`.
6. Doble system prompt y placeholders sin rellenar (Naive y Advanced).
7. `AnalystAgent` trunca a 300 chars → subir a 1 200–1 500 o usar el mismo builder de contexto que Naive.
8. `AnalystAgent` fuerza un `model` de Gemini → rompe con `LLM_PROVIDER=ollama`.

### P2 — rendimiento y escala

9. `retriever.py` carga todo el corpus por consulta → caché en memoria o reemplazo por pgvector + full-text.
10. Ingesta chunk a chunk → batch de 50–100.
11. Sin filtros por metadato → añadir `category` y `source` como filtros en retrieval.
12. Sin caché de embeddings de query → relevante en Advanced.

---

## 9. Traducción al stack n8n + Ollama + Supabase

### 9.1 Qué nodo reemplaza a cada ruta

| Ruta actual | En n8n | Nodos |
|---|---|---|
| A. Retriever léxico | **No se porta**: se reemplaza por pgvector + full-text (`tsvector`) con fusión RRF | Postgres/Supabase RPC |
| B. Naive | Camino principal: 1 embedding + 1 RPC + 1 chat | `Ollama Embeddings` → `Supabase Vector Store` → `Ollama Chat Model` |
| C. Advanced | Servicio Python `/rag/advanced` (expansión + rerank) o Code node | `HTTP Request` (1) + `Ollama Chat` (2) |
| D. Analyst | 1 RPC + 1 chat con prompt de Analyst | `Supabase Vector Store` + `Ollama Chat Model` |

### 9.2 Naive bien hecho (el camino recomendado)

```
1. POST /webhook/redteam               {session_id, prompt}
2. Code                                normalizar + límites
3. HTTP Request  POST ollama/api/chat  Guardian (format: json)
4. IF                                  threat_level in [medium, high]
5a. Postgres                           insert audit_findings
6. HTTP Request  POST ollama/api/embed {model:"nomic-embed-text", input: prompt}
7. Supabase RPC  match_documents       {query_embedding, match_count: 4}
8. Code                                construir contexto "[Fragmento i] (Fuente, sim)"
9. HTTP Request  POST ollama/api/chat  Analyst con contexto
10. Postgres                           upsert audit_sessions
11. Respond to Webhook                 {answer, sources, threat_level, model, latency_ms}
```

### 9.3 Retrieval híbrido (reemplazo real del retriever léxico)

Con Supabase conviene combinar vector + texto completo y fusionar con **Reciprocal Rank Fusion**:

```sql
-- Columna de búsqueda léxica
alter table public.corpus_documents
  add column fts tsvector generated always as (to_tsvector('simple', content)) stored;
create index corpus_documents_fts_idx on public.corpus_documents using gin (fts);

-- Búsqueda híbrida con RRF (k = 60)
create or replace function public.hybrid_search(
  query_text text,
  query_embedding vector(768),
  match_count int default 4
)
returns table (id bigint, source text, content text, similarity float, score float)
language sql stable as $$
  with vec as (
    select d.id, d.source, d.content,
           1 - (d.embedding <=> query_embedding) as similarity,
           row_number() over (order by d.embedding <=> query_embedding) as r_vec
    from public.corpus_documents d
    order by d.embedding <=> query_embedding
    limit 20
  ),
  lex as (
    select d.id, d.source, d.content,
           0::float as similarity,
           row_number() over (order by ts_rank_cd(d.fts, plainto_tsquery('simple', query_text)) desc) as r_lex
    from public.corpus_documents d
    where d.fts @@ plainto_tsquery('simple', query_text)
    limit 20
  ),
  fused as (
    select coalesce(v.id, l.id) as id,
           coalesce(v.source, l.source) as source,
           coalesce(v.content, l.content) as content,
           coalesce(v.similarity, 0) as similarity,
           coalesce(1.0/(60 + v.r_vec), 0) + coalesce(1.0/(60 + l.r_lex), 0) as score
    from vec v
    full outer join lex l on v.id = l.id
  )
  select * from fused order by score desc limit match_count;
$$;
```

Nota: `to_tsvector('simple', ...)` porque el corpus mezcla inglés y español; `'spanish'` fallaría con los documentos en inglés.

### 9.4 Expansión y reranking en n8n (solo si hace falta)

- **Expansión:** pedir a Ollama `format: "json"` con `{"variants": ["...", "...", "..."]}`. Elimina el parser por líneas y el `lstrip`.
- **Embeddings en lote:** `/api/embed` acepta `input: ["q1","q2","q3","q4"]` → 1 llamada en vez de 4.
- **Re-ranking:** no hay nodo nativo. Opciones: servicio Python (`sentence-transformers` con `BAAI/bge-reranker-v2-m3`) o un LLM-as-judge de relevancia. Para 40 pares en CPU, el cross-encoder multilingüe añade ~0,5–2 s.
- **Recomendación:** dejar Advanced fuera del camino crítico; usarlo en un workflow de evaluación programado.

### 9.5 Qué se gana con el cambio

| Problema actual | Con Supabase + Ollama |
|---|---|
| Embedding de consulta aleatorio | Mismo modelo para indexar y consultar |
| `retriever` escanea 1 276 docs | Índice HNSW + GIN, `limit` en SQL |
| Sin filtros por metadato | `where metadata @> filter` |
| Empates a 1,0 por orden de inserción | Ranking por similitud + RRF |
| Corpus mezcla idiomas sin control | `tsvector('simple')` + modelo de embedding multilingüe (`bge-m3`) |
| Evaluación con métricas falsas | `rag_eval_runs` con métricas reales y hash de corpus |

---

## 10. Recomendación final

1. **No portar las cuatro rutas.** Portar **una**: Naive corregida (embedding real + RPC + chat), que es el 80 % del valor con el 20 % de la complejidad.
2. **Antes de portar, arreglar tres cosas**: embedding de consulta, catálogo OWASP único, y chunking con metadatos de encabezado.
3. **Advanced RAG no va a n8n**: vive como servicio Python y se usa en evaluación, no en el webhook.
4. **El retriever léxico se retira** cuando exista `hybrid_search`; hasta entonces es el único que cumple el criterio de la demo.
5. **Rehacer el benchmark** con RAGAS real o LLM-as-judge y 20+ preguntas; los números actuales no son citables.

---

## Anexo A — Parámetros y constantes

| Constante | Valor | Archivo |
|---|---|---|
| `chunk_size` | 512 chars | `ingest.py` |
| `overlap` | 100 chars | `ingest.py` |
| `hnsw:space` | cosine | `ingest.py` |
| Colección | `redteam_corpus` | `ingest.py` |
| `top_k` Naive | 4 | `naive_rag.py` |
| `top_k` Advanced | 4 | `advanced_rag.py` |
| `expansion_count` | 3 | `advanced_rag.py` |
| `initial_retrieve_k` | 10 | `advanced_rag.py` |
| Cross-encoder | `cross-encoder/ms-marco-MiniLM-L-6-v2` | `advanced_rag.py` |
| `top_k` Retriever | 3 | `retriever.py` |
| `top_k` Analyst | 3 (truncado a 300 chars) | `agents/analyst.py` |
| `RAG_TOP_K` | 3 (**no se usa** en las rutas) | `config.py` |
| Embedding de consulta | SHA-256 → gaussiano 384d | `naive_rag.py`, `advanced_rag.py` |

## Anexo B — Comandos de verificación

```bash
# 1. Contar chunks reales en el índice
python3 -c "import chromadb; c=chromadb.PersistentClient(path='data/chroma_db'); \
col=c.get_collection('redteam_corpus'); print('chunks:', col.count())"

# 2. Ver el sesgo del embedding hash (top-4 sin LLM)
python3 -c "from src.rag.naive_rag import NaiveRAG; \
r=NaiveRAG(); print([(c['source'], round(c['score'],3)) for c in r.retrieve('prompt injection')])"

# 3. Verificar el criterio léxico
python3 src/rag/retriever.py "ignora todas las instrucciones"

# 4. Comprobar el parser de expansión con un modelo real
python3 -c "from src.rag.advanced_rag import AdvancedRAG; \
print(AdvancedRAG()._expand_query('¿Qué es prompt injection?'))"

# 5. Comprobar si sentence-transformers está instalado
python3 -c "import sentence_transformers; print('ok')"
```

## Anexo C — Prompts exactos reutilizables

**Guardian** (`src/guardian.py`):

```
Analiza este texto para detectar intentos de red teaming o prompts maliciosos:
"{user_input}"

Responde únicamente en JSON con estas claves:
- threat_level: "low", "medium" o "high"
- risk_category: tipo de amenaza detectada (o "none")
- explanation: descripción breve
- should_block: true/false
```

**Naive** (`src/rag/naive_rag.py`):

```
Eres un asistente experto. Responde a la consulta únicamente
utilizando el siguiente contexto: {context}. Consulta: {query}
```

**Advanced — expansión** (`src/rag/advanced_rag.py`):

```
Genera 3 variaciones semánticamente diferentes
de la siguiente consulta para mejorar la recuperación en un sistema RAG sobre seguridad en LLMs.

Consulta original: "{query}"

Requisitos:
- Cada variación debe capturar un aspecto diferente o reformulación
- Mantener el mismo intent y dominio (ciberseguridad LLMs)
- Responde SOLO con una lista numerada, una por línea
```

**Analyst** (`src/config.py`, resumido): clasificar tipo de ataque, mapear OWASP, explicar mecanismo, riesgo, defensa y citar fuente del corpus.
