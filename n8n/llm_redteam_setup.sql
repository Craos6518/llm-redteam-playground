-- =============================================================================
-- LLM RedTeam - esquema Supabase (Postgres + pgvector)
-- Ejecutar en: Supabase Dashboard -> SQL Editor -> New query
--
-- Este script es el que espera el workflow n8n/llm_redteam_workflow.json.
-- Cubre:
--   1. Tabla `documents` para el nodo Supabase Vector Store (ingesta).
--   2. RPC `match_documents` compatible con el nodo nativo de n8n.
--   3. RPC `search_documents_hybrid` (vector + full-text) usado por el HTTP node.
--   4. Tablas de auditoría `audit_sessions` y `audit_findings`.
--
-- IMPORTANTE: nomic-embed-text produce vectores de 768 dimensiones.
-- Si ya tenias una tabla `documents` con otra dimension, este script se detiene
-- con un error explicito en lugar de dejar el RAG silenciosamente roto.
-- =============================================================================

create extension if not exists vector;

-- -----------------------------------------------------------------------------
-- 1. Corpus vectorizado (tabla estándar del nodo Supabase Vector Store)
-- -----------------------------------------------------------------------------
create table if not exists public.documents (
  id          bigserial primary key,
  content     text        not null,
  metadata    jsonb       not null default '{}'::jsonb,
  embedding   vector(768) not null,
  created_at  timestamptz not null default now()
);

-- Verificación de dimensión: evita el error clásico de indexar 768 y consultar 1536
do $$
declare
  t text;
begin
  select format_type(a.atttypid, a.atttypmod)
    into t
  from pg_attribute a
  join pg_class c on c.oid = a.attrelid
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public'
    and c.relname = 'documents'
    and a.attname = 'embedding'
    and not a.attisdropped;

  if t is not null and t <> 'vector(768)' then
    raise exception
      'public.documents.embedding es %, pero nomic-embed-text genera vector(768). Reindexa o recrea la tabla antes de continuar.',
      t;
  end if;
end $$;

create index if not exists documents_embedding_idx
  on public.documents using hnsw (embedding vector_cosine_ops);

-- Full-text en español para la parte léxica de la búsqueda híbrida
create index if not exists documents_content_spanish_fts_idx
  on public.documents using gin (to_tsvector('spanish', content));

create index if not exists documents_metadata_gin_idx
  on public.documents using gin (metadata jsonb_path_ops);

-- -----------------------------------------------------------------------------
-- 2. RPC estándar para el nodo Supabase Vector Store (modo "retrieve")
--    Firma esperada por n8n: query_embedding, match_count, filter
--    Columnas esperadas: id, content, metadata, similarity
-- -----------------------------------------------------------------------------
drop function if exists public.match_documents(vector, integer, jsonb);

create or replace function public.match_documents(
  query_embedding vector(768),
  match_count     integer default 4,
  filter          jsonb   default '{}'::jsonb
)
returns table (
  id         bigint,
  content    text,
  metadata   jsonb,
  similarity double precision
)
language sql
stable
as $$
  select
    d.id,
    d.content,
    d.metadata,
    1 - (d.embedding <=> query_embedding) as similarity
  from public.documents d
  where filter = '{}'::jsonb
     or d.metadata @> filter
  order by d.embedding <=> query_embedding
  limit greatest(match_count, 1);
$$;

-- -----------------------------------------------------------------------------
-- 3. Búsqueda híbrida usada por el nodo HTTP "Busqueda hibrida"
--    Combina ranking vectorial + full-text con Reciprocal Rank Fusion (RRF).
--    Devuelve `source`, `content` y `score` para el nodo "Construir contexto".
-- -----------------------------------------------------------------------------
create or replace function public.search_documents_hybrid(
  query_text      text,
  query_embedding vector(768),
  match_count     integer default 4
)
returns table (
  id           bigint,
  source       text,
  chunk_idx    integer,
  content      text,
  score        double precision,
  vector_score double precision,
  text_score   double precision
)
language sql
stable
as $$
  with vector_hits as (
    select
      d.id,
      1 - (d.embedding <=> query_embedding) as vector_score,
      row_number() over (order by d.embedding <=> query_embedding) as vrank
    from public.documents d
    order by d.embedding <=> query_embedding
    limit greatest(match_count, 1) * 5
  ),
  text_hits as (
    select
      d.id,
      ts_rank_cd(
        to_tsvector('spanish', d.content),
        websearch_to_tsquery('spanish', coalesce(query_text, ''))
      ) as text_score,
      row_number() over (
        order by ts_rank_cd(
          to_tsvector('spanish', d.content),
          websearch_to_tsquery('spanish', coalesce(query_text, ''))
        ) desc
      ) as trank
    from public.documents d
    where to_tsvector('spanish', d.content)
          @@ websearch_to_tsquery('spanish', coalesce(query_text, ''))
    limit greatest(match_count, 1) * 5
  ),
  candidates as (
    select id from vector_hits
    union
    select id from text_hits
  )
  select
    d.id,
    coalesce(d.metadata->>'source', 'desconocido') as source,
    coalesce((d.metadata->>'chunk_idx')::int, 0)   as chunk_idx,
    d.content,
    coalesce(1.0 / (60 + v.vrank), 0)
      + coalesce(1.0 / (60 + t.trank), 0)           as score,
    coalesce(v.vector_score, 0)                     as vector_score,
    coalesce(t.text_score, 0)                       as text_score
  from candidates c
  join public.documents d on d.id = c.id
  left join vector_hits v on v.id = c.id
  left join text_hits   t on t.id = c.id
  order by score desc
  limit greatest(match_count, 1);
$$;

-- -----------------------------------------------------------------------------
-- 4. Auditoría (columnas alineadas con los nodos Postgres del workflow)
-- -----------------------------------------------------------------------------
create table if not exists public.audit_sessions (
  id           bigserial primary key,
  session_id   text        not null,
  prompt       text,
  answer       text,
  threat_level text,
  model        text,
  latency_ms   integer,
  sources      jsonb       not null default '[]'::jsonb,
  created_at   timestamptz not null default now()
);

create index if not exists audit_sessions_session_id_idx
  on public.audit_sessions (session_id, created_at desc);

create table if not exists public.audit_findings (
  id             bigserial primary key,
  session_id     text        not null,
  prompt         text,
  threat_level   text,
  risk_category  text,
  explanation    text,
  should_block   boolean     not null default false,
  created_at     timestamptz not null default now()
);

create index if not exists audit_findings_session_id_idx
  on public.audit_findings (session_id, created_at desc);

create index if not exists audit_findings_threat_idx
  on public.audit_findings (threat_level, created_at desc);

-- -----------------------------------------------------------------------------
-- 5. Permisos para los roles de Supabase
--    Si usas la service_role key (recomendado en n8n), RLS no aplica.
--    Si usas la anon key, habilita RLS y crea políticas de lectura/escritura.
-- -----------------------------------------------------------------------------
grant execute on function public.match_documents(vector, integer, jsonb)
  to anon, authenticated, service_role;

grant execute on function public.search_documents_hybrid(text, vector, integer)
  to anon, authenticated, service_role;

-- -----------------------------------------------------------------------------
-- 6. Comprobaciones rápidas
-- -----------------------------------------------------------------------------
-- select count(*) as chunks from public.documents;
-- select vector_dims(embedding) as dim from public.documents limit 1;
-- select * from public.search_documents_hybrid(
--   'ignora todas las instrucciones',
--   (select embedding from public.documents limit 1),
--   4
-- );
