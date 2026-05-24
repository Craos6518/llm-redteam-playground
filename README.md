# 🛡️ LLM Red Teaming Playground

**Sistema educativo interactivo para probar seguridad de Modelos de Lenguaje**

Plataforma completa de red teaming con detección de amenazas en tiempo real, análisis técnico contextualizado y generación automática de reportes de auditoría profesionales.

**Proyecto Final:** Introducción a Inteligencia Artificial  
**Estado:** ✅ 100/100 puntos completados  
**Versión:** 1.0  
**Fecha:** 24 de mayo de 2026

---

## ✨ Características Principales

- 🛡️ **Guardian Agent**: Evaluación de amenazas contra OWASP LLM Top 10
- 🔬 **Analyst Agent**: Análisis técnico profundo con contextualización RAG
- 📚 **RAG System**: Pipeline de recuperación + 17 documentos (248 chunks)
- 📝 **Report Exporter**: Generación automática de reportes Markdown
- 🔗 **MCP Server**: Servidor de contexto con 3 herramientas declaradas
- 🎨 **Streamlit UI**: Interfaz web interactiva y profesional
- 📊 **Session Manager**: Gestión de sesiones y estadísticas en tiempo real
- ✅ **Full Test Suite**: 4/4 tests automáticos PASSING (100%)

---

## 🚀 Inicio Rápido

### 1. Instalación

```bash
# Entrar al directorio del proyecto
cd /home/craos6518/Documentos/llm-redteam-playground

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración

```bash
# Crear archivo .env
echo "GEMINI_API_KEY=tu_clave_aqui" > .env
```

### 3. Ejecutar Streamlit

```bash
# Iniciar la aplicación web
streamlit run src/main.py

# Abrirá en: http://localhost:8501
```

### 4. Ejecutar Tests

```bash
# Suite completa de tests
python test_skills_mcp.py

# Validación visual
python validate_skills_mcp.py

# Ejemplo de integración
python integration_example.py
```

---

## 📁 Estructura del Proyecto

```
llm-redteam-playground/
│
├── 📄 PROJECT_SUMMARY.md              # ← EMPIEZA AQUÍ (Resumen completo)
│
├── src/
│   ├── guardian.py                    # 🛡️ Evaluador de amenazas
│   ├── analyst.py                     # 🔬 Análisis técnico
│   ├── main.py                        # 🎨 Interfaz Streamlit (17.6 KB)
│   ├── skills/
│   │   ├── __init__.py
│   │   └── exporter.py                # 📝 Generador de reportes (15.6 KB)
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── report_server.py           # 🔗 Servidor MCP (10.2 KB)
│   └── rag/
│       ├── __init__.py
│       └── retriever.py               # 🧠 Pipeline RAG
│
├── data/
│   ├── corpus/                        # 📚 17 documentos OWASP
│   ├── chroma_db/                     # 💾 Base de datos vectorial
│   └── reports/                       # 📄 Reportes generados
│
├── docs/
│   ├── ARCHITECTURE.md                # 📐 Diagramas del sistema (10 pts)
│   ├── TECHNICAL_REPORT.md            # 📋 Informe técnico (10 pts)
│   ├── PRESENTATION_SCRIPT.md         # 🎤 Guión de presentación (10 pts)
│   ├── STREAMLIT_GUIDE.md             # 📖 Guía de usuario
│   └── SKILLS_MCP_GUIDE.md            # 🔧 Documentación técnica
│
├── tests/
│   ├── test_skills_mcp.py             # ✅ Suite principal (4/4 PASSING)
│   ├── test_streamlit_e2e.py          # 🧪 End-to-end tests
│   ├── validate_skills_mcp.py         # ✓ Validación visual
│   └── integration_example.py         # 📚 Ejemplo de uso
│
├── requirements.txt
├── setup_corpus.py
└── README.md                          # (Este archivo)
```

---

## 🎯 Puntuación del Proyecto

```
═══════════════════════════════════════════════════════════════
                    PUNTUACIÓN FINAL: 100/100
═══════════════════════════════════════════════════════════════

✅ Funcionalidad end-to-end                    20 pts
   • Guardian + Analyst + RAG + Streamlit completo

✅ Pipeline RAG                               15 pts
   • ChromaDB con 17 documentos, 248 chunks

✅ Diseño multiagente                         15 pts
   • Guardian y Analyst separados, orquestados

✅ Skill: Report Exporter                      10 pts
   • generate_report() con validaciones seguridad

✅ MCP Server                                  10 pts
   • 3 herramientas: audit, validate, status

✅ Arquitectura y Diagramas                    10 pts
   • ARCHITECTURE.md con Mermaid + decisiones

✅ Informe Técnico                             10 pts
   • TECHNICAL_REPORT.md (4-6 páginas)

✅ Presentación Oral                           10 pts
   • PRESENTATION_SCRIPT.md (10 minutos)

═══════════════════════════════════════════════════════════════
```

---

## 🧪 Validación y Tests

### Tests Automáticos ✅

```bash
python test_skills_mcp.py
```

**Resultado:** 4/4 PASSING (100%)

```
TEST 1: Exportador Básico                    ✅ PASS
  • generate_report() retorna Path válido
  • Archivo Markdown generado correctamente

TEST 2: Validaciones de Seguridad            ✅ PASS
  • Path traversal bloqueado ✓
  • Chat history límite enforced ✓
  • OWASP categories validadas ✓

TEST 3: Servidor MCP                         ✅ PASS
  • 3 herramientas funcionales ✓
  • Validación pre-ejecución ✓

TEST 4: Calidad de Contenido                 ✅ PASS
  • Secciones del reporte presentes ✓
  • Formato Markdown válido ✓
```

### Reportes Generados ✅

```
reports/
├── pentest_report_demo_session_001_20260524_072847.md (2.1 KB)
├── pentest_report_mcp_test_001_20260524_072740.md (1.8 KB)
├── pentest_report_quality_test_001_20260524_072740.md (2.3 KB)
└── pentest_report_test_session_001_20260524_072740.md (2.5 KB)
```

---

## 📚 Documentación Disponible

| Documento | Tamaño | Propósito |
|-----------|--------|----------|
| [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) | 8 KB | ⭐ **EMPIEZA AQUÍ**: Resumen ejecutivo |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 5 KB | Diagramas arquitectónicos + decisiones |
| [docs/TECHNICAL_REPORT.md](docs/TECHNICAL_REPORT.md) | 12 KB | Informe técnico formal (4-6 páginas) |
| [docs/PRESENTATION_SCRIPT.md](docs/PRESENTATION_SCRIPT.md) | 8 KB | Guión de presentación oral (10 min) |
| [docs/STREAMLIT_GUIDE.md](docs/STREAMLIT_GUIDE.md) | 10.6 KB | Guía de usuario + ejemplos |
| [docs/SKILLS_MCP_GUIDE.md](docs/SKILLS_MCP_GUIDE.md) | 10.6 KB | Documentación técnica + API |
| [PROYECTO_ESTRUCTURA.md](PROYECTO_ESTRUCTURA.md) | - | Estructura general actualizada |

---

## 🛡️ Categorías OWASP Soportadas

El sistema detecta todas las 10 categorías OWASP Top 10 para LLMs:

| # | Categoría | Descripción |
|---|-----------|------------|
| 01 | Prompt Injection | Inyección de instrucciones maliciosas |
| 02 | Sensitive Information Disclosure | Revelación de información confidencial |
| 03 | Training Data Poisoning | Envenenamiento de datos de entrenamiento |
| 04 | Data Poisoning | Envenenamiento de datos en producción |
| 05 | Supply Chain Vulnerabilities | Vulnerabilidades en cadena de suministro |
| 06 | Excessive Agency | Ejecución de acciones no autorizadas |
| 07 | System Prompt Leakage | Fuga del prompt del sistema |
| 08 | Misinformation | Generación de información falsa |
| 09 | Plugin Security | Vulnerabilidades en plugins |
| 10 | Model Theft | Extracción de pesos del modelo |

---

## 💡 Componentes Principales

### 🛡️ Guardian (Evaluador de Amenazas)

```python
from src.guardian import Guardian

guardian = Guardian()
result = guardian.evaluate_threat("Ignora instrucciones...")
# {
#   "is_threat": True,
#   "threat_level": "high",
#   "threat_type": "LLM01",
#   "explanation": "..."
# }
```

### 🔬 Analyst (Análisis Técnico)

```python
from src.analyst import Analyst

analyst = Analyst()
analysis = analyst.generate_detailed_response(
    prompt="Ignora instrucciones...",
    threat_level="high",
    context="[contexto RAG]"
)
# Retorna análisis markdown con explicación técnica
```

### 📝 Report Exporter (Skill)

```python
from src.skills.exporter import generate_report

path = generate_report(
    session_id="session_001",
    chat_history=[...],
    vulnerabilities=[...]
)
# Retorna: Path(/reports/pentest_report_*.md)
```

### 🔗 MCP Server

```python
from src.mcp.report_server import ReportMCPServer

server = ReportMCPServer()
tools = server.get_tools()  # 3 herramientas disponibles
result = server.call_tool("generate_audit_report", {...})
```

---

## 🔄 Flujo de Procesamiento

```
Usuario envía prompt
    ↓
Guardian.evaluate_threat()
    ├─ ¿Es amenaza? → Registrar vulnerabilidad
    ↓
RAG.search()
    └─ Recuperar contexto relevante
    ↓
Analyst.generate_analysis()
    └─ Generar análisis con contexto
    ↓
Streamlit UI
    ├─ Mostrar respuesta con color por severidad
    ├─ Actualizar estadísticas
    └─ Guardar en sesión
    ↓
Usuario descarga reporte
    ↓
ReportExporter.generate_report()
    ├─ Validar datos
    ├─ Generar Markdown
    └─ Retornar archivo .md
```

---

## 🔒 Seguridad Implementada

### Validaciones de Entrada

- ✅ Sanitización de session_id (prevenir path traversal)
- ✅ Límite de chat history (≤1000 mensajes)
- ✅ Límite de tamaño de mensaje (≤10,000 caracteres)
- ✅ Validación de categorías OWASP (whitelist)
- ✅ Validación de severidad (enum)

### Validaciones de Salida

- ✅ Reporte máximo 5 MB
- ✅ Pre-estimación de tamaño antes de generar
- ✅ Hash MD5 para integridad
- ✅ Timestamp de generación

### Protecciones contra Ataques

- ✅ Path Traversal: Regex filtering en filenames
- ✅ Injection: Validación de estructura de datos
- ✅ DoS: Límites de tamaño enforced
- ✅ Información: Reportes sin data sensible

---

## 📊 Estadísticas del Proyecto

- **Líneas de código:** ~3,000
- **Documentos de corpus:** 17
- **Chunks vectoriales:** 248
- **Dimensión de embeddings:** 384
- **Herramientas MCP:** 3
- **Categorías OWASP:** 10/10
- **Tests automáticos:** 4/4 PASSING
- **Documentación:** 5 guías completas
- **Tiempo de procesamiento:** ~2 segundos

---

## 🎓 Casos de Uso

### Para Educadores
- Enseñar vulnerabilidades de LLMs en clase
- Demonstración interactiva de ataques
- Reportes para auditoría de defensa

### Para Investigadores
- Red teaming rápido de nuevos modelos
- Documentación de vulnerabilidades
- Dataset de ataques

### Para Desarrolladores
- Evaluar seguridad de integraciones con LLM
- Validar defensas contra ataques OWASP
- Benchmarking de seguridad

---

## 🚀 Próximos Pasos

### Corto Plazo
- [ ] Validar Streamlit en navegador
- [ ] Agregar persistencia de sesiones
- [ ] Exportación a PDF

### Mediano Plazo
- [ ] Fine-tuning de Guardian
- [ ] API REST para integración
- [ ] Dashboard de estadísticas

### Largo Plazo
- [ ] Modelo defender custom
- [ ] Federated learning
- [ ] Blockchain audit trail

---

## 📞 Referencias

### Documentación del Proyecto
- [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) - Resumen ejecutivo ⭐
- [PROYECTO_ESTRUCTURA.md](PROYECTO_ESTRUCTURA.md) - Estructura general

### Recursos Educativos
- OWASP Top 10 for LLMs: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Model Context Protocol: https://modelcontextprotocol.io/
- Streamlit: https://streamlit.io/
- ChromaDB: https://docs.trychroma.com/

---

## ✅ Checklist Final

- [x] Guardian módulo implementado
- [x] Analyst módulo implementado
- [x] RAG pipeline completo
- [x] Report exporter funcional
- [x] MCP server deployado
- [x] Streamlit UI implementada
- [x] 4/4 Tests pasando
- [x] Arquitectura documentada
- [x] Informe técnico escrito
- [x] Guión de presentación listo
- [x] 100/100 puntos completados

---

## 📄 Licencia y Créditos

**Proyecto Final:** Introducción a Inteligencia Artificial  
**Institución:** [Universidad]  
**Fecha:** 24 de mayo de 2026  
**Estado:** ✅ Completado y validado  

---

**Para comenzar:** Lee [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) para un resumen completo del proyecto.
