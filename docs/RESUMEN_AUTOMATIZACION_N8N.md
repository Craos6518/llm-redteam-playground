# Resumen funcional y plan de automatización
## LLM Red Teaming Playground → n8n + Ollama + Supabase Vector Store

> Documento de trabajo. Describe **qué hace hoy el sistema**, **qué piezas son reutilizables** y **cómo se traslada a un flujo low-code** con n8n, Ollama y Supabase (pgvector), sin perder las garantías de seguridad ni la trazabilidad de auditoría.

---

## 1. Resumen funcional (qué hace el proyecto)

Es un **laboratorio de red teaming defensivo para LLMs**. El usuario envía prompts (legítimos o maliciosos) y el sistema:

1. **Evalúa el riesgo** del prompt con un agente LLM ("Guardian") que devuelve un veredicto en JSON (`threat_level`, `risk_category`, `should_block`, `explanation`).
2. **Recupera contexto** de un corpus propio de 27 documentos Markdown sobre OWASP LLM Top 10, jailbreak, prompt injection, MCP, RAG security, etc.
3. **Genera un análisis técnico** ("Analyst") que clasifica el ataque, lo mapea a OWASP, explica el mecanismo, el riesgo y la mitigación, citando las fuentes del corpus.
4. **Acumula una sesión de auditoría**: historial, hallazgos, distribución de severidad, score de seguridad.
5. **Exporta un reporte de pentesting** en Markdown (`reports/pentest_report_<session>_<timestamp>.md`) con validaciones anti path-traversal, límites de tamaño y hash.

Interfaz actual: **Streamlit** (`src/main.py`) con estética SOC, selector de arquitectura RAG, panel de estadísticas y botón de descarga del reporte. También hay CLI (`test_agents.py`, `test_agents_auto.py`) y un benchmark RAGAS (`eval/benchmark_rag.py`).

**Valor real del proyecto para una automatización:** no es solo un chat; es un **pipeline de clasificación + RAG + generación de evidencia** con contrato de datos bastante claro. Eso es exactamente lo que n8n puede orquestar.

---

## 2. Flujo actual en tiempo de ejecución

```
Prompt del usuario
   │
   ├─► Guardian (LLM, JSON)  ──► threat_level / risk_category / should_block
   │        └─ si high|medium → se registra Vulnerability (OWASP + severidad)
   │
   ├─► RAG (una de 3 variantes, seleccionable en la UI)
   │      ├─ retriever.py     → scoring léxico + boost por documento fuente (ChromaDB)
   │      ├─ naive_rag.py     → embedding + top-k=4 + prompt aumentado
   │      └─ advanced_rag.py  → query expansion (3 variantes) + top-10 + cross-encoder → top-4
   │
   ├─► Analyst (LLM)          → análisis con el contexto recuperado
   │
   └─► Sesión                 → estadísticas + export vía MCP/Skill a Markdown
```

Puntos de integración ya existentes y estables:

| Punto | Archivo | Contrato |
|---|---|---|
| Evaluación de amenaza | `src/guardian.py` → `Guardian.evaluate_threat()` | `{status, analysis, threat, threat_level, blocked, provider, model}` |
| Análisis | `src/analyst.py` → `Analyst.generate_detailed_response(question, depth, context)` | texto Markdown |
| Filtro de salida | `src/guardian.py` → `filter_response()` | `{status, safe, risks, recommendation, approved}` |
| Recuperación | `src/rag/retriever.py` → `RAGRetriever.retrieve(query, top_k)` | `[{content, score, source, chunk_idx, threat_category}]` |
| RAG baseline | `src/rag/naive_rag.py` → `NaiveRAG.generate(query)` | `{query, answer, retrieved_chunks, num_chunks, model}` |
| RAG avanzado | `src/rag/advanced_rag.py` → `AdvancedRAG.generate(query)` | idem + `expanded_queries` |
| Reporte | `src/skills/exporter.py` → `generate_report(...)` | `Path` al `.md` |
| Herramientas | `src/mcp/report_server.py` → `ReportMCPServer.call_tool(...)` | `generate_audit_report`, `validate_session`, `get_report_status` |
| Abstracción LLM | `src/llm_client.py` → `LLMClient.generate()` | cadena Gemini → Groq → OpenRouter → OmniRoute → **Ollama** |

**Dato clave:** `src/llm_client.py` ya habla el protocolo compatible con OpenAI contra `http://localhost:11434/v1`. Ollama no es una migración: es un proveedor más de la cadena (`LLM_PROVIDER=ollama`).

---

## 3. Estado real del código (lo que impacta la automatización)

Revisión hecha sobre el repositorio, no sobre el README:

| Tema | Estado real | Impacto / acción |
|---|---|---|
| Documentos del corpus | **27** archivos `.md` en `data/corpus/` | Reindexar y recalcular métricas; el README cita 17 docs / 1276 chunks |
| Embeddings en `naive_rag.py` y `advanced_rag.py` | **Hash SHA-256 → vector gaussiano de 384 d** (no semántico) | La búsqueda "vectorial" no es semántica; al migrar a Supabase hay que usar embeddings reales (Ollama) |
| Ingesta | Chroma genera embeddings por defecto (`all-MiniLM-L6-v2`, 384 d, cosine) mientras la consulta usa el hash | Inconsistencia consulta↔índice. Es la deuda técnica principal a corregir |
| `retriever.py` | Recorre **todos** los documentos y re-rankea por reglas léxicas | Funciona con ~1.3k chunks, no escala; pgvector lo reemplaza |
| Guardian duplicado | `src/agents/guardian.py` (regex + `GuardianAgent.chat`) y `src/guardian.py` (LLM JSON, es el que usa Streamlit) | Unificar: regex como pre-filtro barato + LLM como clasificador |
| Mapa OWASP | Inconsistente entre `analyst.py`, `exporter.py` y `main.py` (LLM02/LLM06/LLM07 cambian de nombre) | Fijar **un solo catálogo** antes de automatizar |
| Estado de sesión | `st.session_state` + memoria del proceso | n8n necesita estado explícito en Postgres/Supabase |
| Reportes | Archivos en `reports/` del contenedor | Mover a tabla + Supabase Storage; el volumen Docker no sirve en serverless |
| Auth del "Guardián" | `SECRET_KEY` inyectada en el system prompt | No es autenticación real; en n8n usar credenciales/headers |
| `config.py` | `LLM_TIMEOUT` definido dos veces y `LLM_MODEL` referenciado sin definir en `__main__` | Limpiar antes de reutilizar como servicio |
| Docker | `Dockerfile` + `docker-compose.yml` solo con Streamlit | Base para el microservicio, no para n8n |

---

## 4. Arquitectura objetivo

**Recomendación: híbrida.** n8n orquesta y persiste; un microservicio Python delgado (o Code nodes) cubre lo que n8n no debe hacer.

```
┌──────────────┐   webhook    ┌───────────────────────────────┐
│ UI (Streamlit│─────────────►│  n8n  (workflow "Red Team")   │
│  / Form /    │              │                               │
│  Chat n8n)   │◄─────────────│  1. Normalizar + rate limit   │
└──────────────┘   respuesta  │  2. Pre-filtro regex          │
                              │  3. Guardian  ─► Ollama       │
                              │  4. Embedding ─► Ollama        │
                              │  5. Retrieval ─► Supabase      │
                              │  6. Analyst   ─► Ollama       │
                              │  7. Persistir sesión/hallazgo │
                              │  8. Reporte MD / Storage      │
                              │  9. Notificar (Slack/Email)   │
                              └───────┬───────────────┬───────┘
                                      │               │
                             ┌────────▼──────┐  ┌─────▼─────────┐
                             │ Supabase      │  │ Ollama        │
                             │ Postgres +    │  │ qwen3:4b      │
                             │ pgvector      │  │ nomic-embed-  │
                             │ + Storage     │  │ text (768 d)  │
                             └───────────────┘  └───────────────┘
```

Por qué híbrida:

- n8n tiene nodos nativos **Ollama Chat Model**, **Ollama Embeddings** y **Supabase Vector Store** → el RAG básico se arma sin código.
- Lo que n8n no cubre bien: **query expansion + re-ranking cross-encoder**, validaciones estrictas del reporte, y benchmarks. Eso queda en Python (`AdvancedRAG`, `exporter`, `benchmark_rag`).
- El estado de auditoría **debe** salir de `st.session_state` y vivir en Supabase, para que el workflow sea reintentable e idempotente.

---

## 5. Mapeo componente actual → pieza nueva

| Hoy | Mañana | Notas |
|---|---|---|
| `data/chroma_db` + `RAGIngestor` | `public.corpus_documents` (pgvector) + workflow de ingesta | Chunk 512 / overlap 100 (mismos parámetros) |
| `LLMClient` con fallback | Nodo HTTP Request a `ollama:11434` (o nodo Ollama) | Mantener fallback solo si hay más de un backend |
| `Guardian.evaluate_threat` | Nodo Ollama con `format: json` + IF | Mismo prompt, mismas claves |
| `Guardian.filter_response` | Nodo Ollama post-generación + IF de bloqueo | Opcional en fase 2 |
| `retriever.py` | `rpc('match_documents')` vía Supabase Vector Store | Reemplaza el scoring léxico |
| `naive_rag.py` | Flujo lineal del workflow | Es el camino recomendado para producción |
| `advanced_rag.py` | Microservicio `/rag/advanced` llamado por HTTP | Solo si se necesita calidad extra |
| `Vulnerability` / `ReportExporter` | Tablas `audit_findings` / `audit_reports` + Code node | Portar las validaciones (1000 msgs, 10 KB, 5 MB, regex de `session_id`) |
| `ReportMCPServer` | Workflow hijo "Tool: report" invocable por AI Agent | MCP → herramienta n8n |
| Streamlit | Front que hace `POST /webhook/redteam` | O chat trigger de n8n |
| `eval/benchmark_rag.py` | Workflow programado (cron) con tabla `rag_eval_runs` | Regresión de prompts/modelos |

---

## 6. Modelo de datos en Supabase

```sql
create extension if not exists vector;

-- Corpus vectorizado (compatible con el nodo Supabase Vector Store de n8n:
-- columnas id / content / metadata / embedding y función match_documents)
create table public.corpus_documents (
  id          bigserial primary key,
  source      text        not null,          -- p.ej. owasp_llm01_prompt_injection.md
  chunk_idx   int         not null,
  total_chunks int,
  content     text        not null,
  metadata    jsonb       not null default '{}'::jsonb,
  embedding   vector(768) not null,          -- nomic-embed-text
  created_at  timestamptz not null default now(),
  unique (source, chunk_idx)
);

create index corpus_documents_embedding_idx
  on public.corpus_documents using hnsw (embedding vector_cosine_ops);

create or replace function public.match_documents(
  query_embedding vector(768),
  match_count int default 4,
  filter jsonb default '{}'::jsonb
)
returns table (id bigint, source text, chunk_idx int, content text, similarity float)
language sql stable as $$
  select d.id, d.source, d.chunk_idx, d.content,
         1 - (d.embedding <=> query_embedding) as similarity
  from public.corpus_documents d
  where d.metadata @> filter
  order by d.embedding <=> query_embedding
  limit match_count;
$$;

-- Trazabilidad de la auditoría
create table public.audit_sessions (
  id            uuid primary key default gen_random_uuid(),
  session_id    text unique not null,
  started_at    timestamptz not null default now(),
  ended_at      timestamptz,
  llm_provider  text,
  llm_model     text,
  total_prompts int not null default 0,
  total_blocked int not null default 0,
  risk_score    numeric(4,3),
  raw           jsonb not null default '{}'::jsonb
);

create table public.audit_findings (
  id             bigserial primary key,
  session_id     uuid not null references public.audit_sessions(id) on delete cascade,
  attempt_no     int  not null,
  owasp_category text not null check (owasp_category ~ '^LLM(0[1-9]|10)$'),
  severity       text not null check (severity in ('low','medium','high','critical')),
  title          text not null,
  description    text not null,
  source_doc     text,
  prompt_excerpt text,
  created_at     timestamptz not null default now()
);

create table public.audit_reports (
  id          uuid primary key default gen_random_uuid(),
  session_id  uuid not null references public.audit_sessions(id) on delete cascade,
  storage_path text,          -- Supabase Storage: reports/<session_id>.md
  markdown    text,
  sha256      text not null,
  created_at  timestamptz not null default now()
);

create table public.rag_eval_runs (
  id          bigserial primary key,
  run_at      timestamptz not null default now(),
  architecture text not null,        -- naive | advanced | retriever
  model       text not null,
  context_precision numeric(4,3),
  context_recall    numeric(4,3),
  faithfulness      numeric(4,3),
  answer_relevancy  numeric(4,3),
  dataset_hash text,
  details     jsonb
);
```

> **Dimensión de embedding:** 768 solo si se usa `nomic-embed-text`. Si se elige `mxbai-embed-large` o `bge-m3` (1024), hay que cambiar `vector(768)` y **reindexar todo**. Fijar esto antes de cargar el corpus evita una migración dolorosa.

---

## 7. Workflow n8n (nodos en orden)

Nombre sugerido: **`redteam/evaluate-prompt`**, trigger `Webhook POST /webhook/redteam`.

| # | Nodo | Función | Detalle |
|---|---|---|---|
| 1 | Webhook | Entrada | Body: `{session_id?, prompt, architecture?, depth?}` |
| 2 | Code | Normalizar | Genera `session_id` si falta, valida longitud ≤ 10 000, limita historial |
| 3 | IF | Pre-filtro regex | Patrones de `InputSanitizer` (ignora instrucciones, asume rol, admin, system prompt). Match → salta a 4a |
| 4 | HTTP Request | Guardian | `POST http://ollama:11434/api/chat`, `format: "json"`, `temperature: 0.2` |
| 4a | Code | Fallback determinista | Si el regex disparó, construir veredicto `{threat_level:"high", risk_category:"prompt_injection"}` sin gastar LLM |
| 5 | Code | Parsear veredicto | `JSON.parse($json.message.content)` con tolerancia a bloques ```json |
| 6 | IF | ¿Amenaza? | `threat_level in [medium, high]` o `should_block` |
| 6a | Postgres | Registrar hallazgo | Insert en `audit_findings` (severidad = threat_level) |
| 7 | HTTP Request | Embedding | `POST /api/embed` `{model:"nomic-embed-text", input: prompt}` → `embeddings[0]` |
| 8 | Supabase | Vector search | `match_documents(query_embedding, match_count=4)` |
| 9 | Code | Construir contexto | Formato `[Fragmento i] (Fuente, similitud)` como en `_build_context` |
| 10 | HTTP Request | Analyst | `POST /api/chat` con system prompt de Analyst + contexto + `depth` |
| 11 | Code | Ensamblar reporte | Markdown con las secciones del exporter (resumen, hallazgos, distribución, recomendaciones, hash) |
| 12 | Supabase Storage | Subir `.md` | `reports/<session_id>.md` |
| 13 | Postgres | Upsert sesión + reporte | `audit_sessions`, `audit_reports` |
| 14 | Respond to Webhook | Salida | `{session_id, threat_level, blocked, answer, report_url, provider, model, latency_ms}` |
| 15 | Error Trigger | Workflow de error | Reintento con backoff; tras N fallos → tabla `audit_dlq` + alerta Slack |

Payload de referencia para Ollama:

```json
{
  "model": "qwen3:4b",
  "stream": false,
  "format": "json",
  "options": { "temperature": 0.2, "num_ctx": 8192 },
  "messages": [
    { "role": "system", "content": "<prompt del Guardian/Analyst>" },
    { "role": "user", "content": "<prompt + contexto>" }
  ]
}
```

Buenas prácticas n8n que aplican aquí:

- **Idempotencia:** `session_id` como clave; inserts con `on conflict`. Un reintento no debe duplicar hallazgos.
- **Timeouts:** Ollama local puede tardar 10–40 s con `qwen3:4b` en CPU. Configurar timeout del nodo HTTP por encima del peor caso y `keep_alive: "30m"` para evitar recargas del modelo.
- **JSON mode:** usar `format: "json"` (o JSON Schema en versiones recientes). Si el modelo no respeta el formato, el paso 5 debe degradar a `threat_level: "low"` **y marcar `parse_error`**, nunca asumir "seguro".
- **Secretos:** credenciales de Supabase en n8n Credentials, nunca en nodos ni en el repo.
- **Trazabilidad:** guardar `provider`, `model`, `latency_ms`, `attempts` en `raw` para poder auditar el propio auditor.

---

## 8. Ingesta y reindexación con Ollama

Dos opciones:

**A. Workflow n8n programado (recomendado si el corpus cambia poco)**
`Schedule Trigger` → `Read Binary Files` (`data/corpus/*.md`) → `Code` (chunk 512/100) → `Loop Over Items` → `Ollama Embeddings` → `Supabase` insert → `Code` (reporte de conteos).

**B. Script puntual (más simple y reproducible)**

```python
# scripts/reindex_supabase.py  (propuesto)
import hashlib, json, os, pathlib, requests
from supabase import create_client

CHUNK, OVERLAP, MODEL = 512, 100, "nomic-embed-text"
OLLAMA = os.getenv("OLLAMA_URL", "http://localhost:11434")
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
col = sb.table("corpus_documents")

def chunks(text):
    for i in range(0, len(text), CHUNK - OVERLAP):
        yield text[i:i + CHUNK]

def embed(text):
    r = requests.post(f"{OLLAMA}/api/embed",
                      json={"model": MODEL, "input": text}, timeout=120)
    r.raise_for_status()
    return r.json()["embeddings"][0]

rows = []
for path in sorted(pathlib.Path("data/corpus").glob("*.md")):
    parts = [c for c in chunks(path.read_text(encoding="utf-8")) if c.strip()]
    for idx, part in enumerate(parts):
        rows.append({
            "source": path.name,
            "chunk_idx": idx,
            "total_chunks": len(parts),
            "content": part,
            "metadata": {"source": path.name, "chunk_idx": idx},
            "embedding": embed(part),
        })

for i in range(0, len(rows), 50):
    col.upsert(rows[i:i + 50], on_conflict="source,chunk_idx")
print(f"indexados: {len(rows)} chunks de {len(list(pathlib.Path('data/corpus').glob('*.md')))} documentos")
```

**Criterios de aceptación de la ingesta**

- `select count(*) from corpus_documents` ≈ chunks esperados para 27 documentos (medir, no asumir 1276).
- Query de humo: `"ignora todas las instrucciones"` → el top-1 debe ser `owasp_llm01_prompt_injection.md` (mismo criterio que la Fase 2 del plan original).
- `similarity` en rango 0–1 y no saturada (si todo da > 0.95, la dimensión o el modelo están mal).

---

## 9. Plan por fases

| Fase | Entregable | Criterio de aceptación |
|---|---|---|
| **0. Saneamiento** (1–2 d) | Un solo catálogo OWASP, eliminación del hash-embedding, config limpia, `Guardian` único | `pytest` verde; una sola definición de severidades/categorías |
| **1. Supabase** (2 d) | SQL del §6 aplicado, corpus reindexado, `match_documents` validado | Humo de retrieval correcto sobre 5 consultas del benchmark |
| **2. Ollama** (1 d) | `qwen3:4b` + `nomic-embed-text` sirviendo, contratos JSON verificados | 20 prompts de prueba con 0 `parse_error`; latencia medida |
| **3. Workflow base** (2–3 d) | n8n §7 sin reporte ni storage | Webhook responde `{threat_level, answer, sources}`; sesión persistida |
| **4. Reporte + notificación** (1–2 d) | Storage, `audit_reports`, Slack/Email | Reporte descargable, idempotente, hash estable |
| **5. Avanzado** (2 d) | Microservicio `advanced_rag` + re-ranking | Mejora medible de `context_precision` vs naive en `rag_eval_runs` |
| **6. Observabilidad** (1 d) | Cron de evaluación + dashboard | Regresión detectada automáticamente al cambiar modelo/prompt |

---

## 10. Riesgos y decisiones abiertas

1. **Embeddings inconsistentes (crítico).** Hoy la consulta no usa el mismo espacio vectorial que el índice. Cualquier migración debe reindexar; no se puede "copiar Chroma a Supabase" y esperar calidad.
2. **Fiabilidad del JSON en modelos locales.** `qwen3:4b` es razonable pero no perfecto. Mitigación: `format: "json"`, temperatura baja, validación con Zod/JSON Schema en Code node, y política explícita de fallo (nunca "todo seguro" por defecto).
3. **Latencia.** Un turno puede implicar 3–5 llamadas al LLM (Guardian, expansion, rerank vía cross-encoder, Analyst). Con Ollama local conviene: Guardian en modelo pequeño, Analyst en modelo mayor, y **desactivar query expansion** en el camino de producción.
4. **Dimensión de embedding.** Fijar 768 (`nomic-embed-text`) o 1024 (`bge-m3`) **antes** de cargar. Cambiarla después = reindexar todo.
5. **Seguridad del propio flujo.** Webhook público = superficie de ataque. Exigir header secreto o Basic Auth, rate limit por IP/sesión, y límite de longitud igual al del exporter (10 000 caracteres).
6. **Reportes como archivos.** En un entorno orquestado, el filesystem no es confiable. Tabla + Storage, con el Markdown también en base para auditoría.
7. **Doble fuente de verdad de prompts.** Hoy hay prompts en `config.py`, en `analyst.py`, en `advanced_rag.py` y en `src/guardian.py`. Versionarlos (tabla `prompt_versions` o archivos en el repo) es requisito para comparar modelos.

---

## 11. Qué reutilizar tal cual

- **Prompts** de `src/config.py` (Guardian y Analyst) y el de `THREAT_PROMPT_TEMPLATE` en `src/guardian.py`.
- **Contrato JSON** del veredicto: `threat_level`, `risk_category`, `explanation`, `should_block`.
- **Reglas de validación** del exporter: regex de `session_id`, 1000 mensajes, 10 000 caracteres por mensaje, 5 MB por reporte, hash MD5/SHA.
- **Estructura del reporte**: resumen ejecutivo, hallazgos por categoría OWASP, distribución de severidad, recomendaciones.
- **Dataset de evaluación** de `eval/benchmark_rag.py` (5 preguntas con ground truth) como suite de regresión del workflow.
- **Patrón de fallback** de `LLMClient`, solo si en producción hay más de un backend (p. ej. Ollama + Groq como respaldo).

## 12. Qué no trasladar

- El scoring léxico de `retriever.py` (pgvector lo sustituye).
- El hash-embedding de `naive_rag.py` / `advanced_rag.py`.
- El estado en `st.session_state` como fuente de verdad.
- `InputSanitizer` como **único** mecanismo de defensa (es un pre-filtro, no un guardrail).
- La `SECRET_KEY` en el system prompt como control de acceso.

---

## 13. Primeros pasos concretos (si se arranca ya)

1. Aplicar el SQL del §6 en un proyecto Supabase de pruebas.
2. Levantar `ollama pull qwen3:4b` y `ollama pull nomic-embed-text`.
3. Correr `scripts/reindex_supabase.py` y validar el top-1 de `"ignora todas las instrucciones"`.
4. Importar el workflow de §7 en n8n con solo los nodos 1→10 y probar con 5 prompts.
5. Comparar respuestas contra la app Streamlit actual para calibrar prompts (mismo modelo, distinto orquestador).
6. Recién entonces portar reporte, storage y notificaciones.
