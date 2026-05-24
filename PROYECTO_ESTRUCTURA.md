# Estructura y Componentes del Proyecto

## 📁 Directorios Principales

```
llm-redteam-playground/
├── src/                          # Código fuente del proyecto
│   ├── guardian.py              # 🛡️  Módulo de seguridad y defensa
│   ├── analyst.py               # 🔬 Módulo de análisis profundo
│   ├── test_api.py              # ✅ Prueba básica de API
│   ├── rag/
│   │   ├── ingest.py            # 📥 Ingesta de corpus y búsqueda
│   │   ├── retriever.py         # 🔍 Recuperación y re-ranking
│   │   └── __init__.py
│   ├── skills/                  # 🎯 Skills personalizadas
│   │   ├── exporter.py          # 📊 Generador de reportes
│   │   └── __init__.py
│   └── mcp/                     # 🔌 Servidor MCP
│       ├── report_server.py     # 📋 Servidor de reportes
│       └── __init__.py
│
├── data/
│   ├── corpus/                  # 📚 Base de conocimiento (17 documentos)
│   │   ├── jailbreak_taxonomy.md
│   │   ├── owasp_llm*.md       (7 archivos OWASP)
│   │   ├── red_teaming_methodology.md
│   │   ├── embeddings_vector_databases.md
│   │   └── ... (más documentos)
│   └── chroma_db/               # 🗄️  Base de datos vectorial
│       ├── (Auto-generada por ingest.py)
│
├── docs/                        # 📖 Documentación
├── tests/                       # 🧪 Tests
├── reports/                     # 📊 Reportes
├── logs/                        # 📋 Logs
│
└── venv/                        # 🐍 Entorno virtual (no subir)
```

## 🔧 Módulos Principales

### 1. Guardian (`src/guardian.py`) 🛡️
**Responsable**: Evaluación de seguridad y defensa

**Funcionalidades**:
- `evaluate_threat()` - Detecta intentos de jailbreak y prompt injection
- `filter_response()` - Valida respuestas de IA para contenido malicioso

```bash
python src/guardian.py
```

### 2. Analyst (`src/analyst.py`) 🔬
**Responsable**: Análisis profundo y generación de respuestas

**Funcionalidades**:
- `generate_detailed_response()` - Respuestas con profundidad variable (brief/standard/deep)
- `analyze_prompt()` - Análisis de prompts
- `identify_attack_vectors()` - Análisis de vulnerabilidades (fines educativos)

```bash
python src/analyst.py
```

### 3. RAG Ingestor (`src/rag/ingest.py`) 📥
**Responsable**: Ingesta de corpus y búsqueda semántica

**Funcionalidades**:
- Ingesta de 17 documentos Markdown (248 chunks)
- Almacenamiento vectorial en ChromaDB
- Búsqueda híbrida (palabras clave + embeddings)
- Criterio validado: query "jailbreak" retorna 3 chunks con score > 0.7

**Comandos**:

```bash
# Ingesta completa (generar data/chroma_db/)
python -m src.rag.ingest

# Reiniciar BD
python -m src.rag.ingest --reset

# Modo test
python -m src.rag.ingest --test

# Búsqueda personalizada
python -m src.rag.ingest --query "prompt injection"
```

### 4. Skills: Exportador de Reportes (`src/skills/exporter.py`) 📊
**Responsable**: Generación de reportes MD con hallazgos y auditoría

**Funcionalidades**:
- `ReportExporter.generate_report()` - Genera reportes MD estructurados
- Validaciones de seguridad: path traversal, límites de tamaño
- Secciones: resumen ejecutivo, hallazgos OWASP, historial, recomendaciones
- Soporte para 10 categorías OWASP LLM

**Uso**:

```python
from src.skills.exporter import generate_report, Vulnerability

report = generate_report(
    session_id="audit_001",
    chat_history=[...],
    vulnerabilities=[
        Vulnerability(category="LLM01", severity="high", ...)
    ]
)
```

**Validaciones**:
- ✅ Sanitización de nombres de archivo
- ✅ Prevención de path traversal
- ✅ Límite de tamaño: 5 MB
- ✅ Límite de mensajes: 1000
- ✅ Validación de categorías OWASP

### 5. Servidor MCP (`src/mcp/report_server.py`) 🔌
**Responsable**: Interfaz Model Context Protocol para herramientas

**Funcionalidades**:
- `ReportMCPServer.get_tools()` - Lista herramientas MCP disponibles
- `ReportMCPServer.call_tool()` - Ejecuta herramientas
- 3 herramientas:
  1. `generate_audit_report` - Genera reporte
  2. `validate_session` - Valida datos
  3. `get_report_status` - Estado de reportes

**Uso**:

```python
from src.mcp.report_server import ReportMCPServer, MCPToolExecutor

server = ReportMCPServer()
executor = MCPToolExecutor(server)

result = executor.execute("generate_audit_report", {...})
```

## 📚 Corpus de Conocimiento (data/corpus/)

17 documentos cubriendo:
- **OWASP Top 10 para LLMs**: LLM01-LLM09
- **Ataques específicos**: Jailbreak, prompt injection, data poisoning
- **Defensas**: Métodos de mitigación, frameworks de evaluación
- **Arquitectura**: Embeddings, vectores, transformers
- **Metodología**: Red teaming, seguridad MCP, social engineering

## 🎯 Criterios de Validación

✅ **Guardian**:
- Detecta prompt malicioso
- Filtra respuestas seguras
- Sin errores de import/API

✅ **Analyst**:
- Genera respuestas de varias profundidades
- Analiza vectores de ataque (educativo)
- Sin errores

✅ **RAG**:
- ✅ 248 chunks ingesta dos
- ✅ Query "jailbreak" → 3 chunks con score 1.0
- ✅ data/chroma_db/ generada
- ✅ Búsqueda funciona correctamente

## 🚀 Uso Integrado

```python
from src.guardian import Guardian
from src.analyst import Analyst
from src.rag.ingest import RAGIngestor

# Inicializar componentes
guardian = Guardian()
analyst = Analyst()
rag = RAGIngestor()

# Flujo: entrada → Guardian → Analyst → Respuesta
user_input = "Explica cómo hacer jailbreak a un LLM"

# 1. Evaluar seguridad
threat = guardian.evaluate_threat(user_input)

# 2. Si es seguro, analizar
if not threat["blocked"]:
    response = analyst.generate_detailed_response(user_input, depth="deep")
    
# 3. Usar RAG para contexto
    rag_results = rag.search(user_input, top_k=3)
    for doc, score, meta in rag_results:
        print(f"Contexto: {doc[:100]}...")
```

## 📦 Dependencias

```
google-genai>=0.8.0           # API de Gemini
chromadb>=0.4.0               # Base de datos vectorial
python-dotenv>=1.0.0          # Variables de entorno
requests>=2.31.0              # HTTP
```

## 🧪 Testing y Validación

### Tests Disponibles

```bash
# Test de Skills y MCP (4/4 passing)
python test_skills_mcp.py

# Validación visual de la implementación
python validate_skills_mcp.py

# Ejemplo de integración
python integration_example.py

# Tests generales del proyecto
python test_modules.py
python test_agents.py
```

### Cobertura de Tests

✅ **Skills (test_skills_mcp.py)**:
- Test 1: Exportador básico - Verifica generación de reportes
- Test 2: Validaciones - Path traversal, tamaño, severidad
- Test 3: Servidor MCP - Herramientas, ejecución, estado
- Test 4: Calidad - Secciones, emojis, citación OWASP

✅ **Reportes Generados**:
- Ubicación: `reports/pentest_report_*.md`
- Validación: Archivo MD bien formado, secciones completas
- Ejemplo: `reports/pentest_report_test_session_001_20260524_072740.md`

## ✅ Estado del Proyecto

- [x] Estructura de carpetas creada
- [x] Guardián implementado
- [x] Analyst implementado
- [x] RAG con 17 documentos
- [x] Búsqueda validada (criterios cumplidos)
- [x] API Keys configuradas
- [x] Base de datos ChromaDB persistida
- [x] **Skill de Exportación (NUEVO)**
  - [x] `src/skills/exporter.py` implementado
  - [x] Función `generate_report()` funcional
  - [x] Validaciones de seguridad (path traversal, tamaños)
  - [x] Reportes MD estructurados con OWASP
  - [x] 4 reportes de prueba generados
- [x] **Servidor MCP (NUEVO)**
  - [x] `src/mcp/report_server.py` implementado
  - [x] Clase `ReportMCPServer` completa
  - [x] 3 herramientas MCP disponibles
  - [x] `MCPToolExecutor` para interfaz consistente
  - [x] Tests validados (4/4 passing)
- [x] Documentación completa
  - [x] `docs/SKILLS_MCP_GUIDE.md` (10KB)
  - [x] `integration_example.py` (ejemplo Streamlit)
  - [x] Docstrings en todas las funciones
- [ ] Interfaz Streamlit (PRÓXIMO)
- [ ] Diagramas de arquitectura (PRÓXIMO)

---
**Última actualización**: 21 de mayo de 2026
**Estado**: ✅ Listo para presentación
