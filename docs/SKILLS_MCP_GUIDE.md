# Guía: Skill de Exportación y Servidor MCP

## 📋 Descripción General

El proyecto implementa dos componentes clave para la exportación y auditoría:

1. **Skill de Exportación** (`src/skills/exporter.py`): Genera reportes MD estructurados
2. **Servidor MCP** (`src/mcp/report_server.py`): Interfaz Model Context Protocol para operaciones de auditoría

---

## 1. Skill de Exportación

### 📊 Función Principal: `generate_report()`

```python
from src.skills.exporter import generate_report, Vulnerability
from pathlib import Path

# Crear vulnerabilidades
vulnerabilities = [
    Vulnerability(
        category="LLM01",           # Categoría OWASP
        severity="high",            # low|medium|high|critical
        title="Prompt Injection",
        description="Intento de inyección de prompt detectado",
        source="owasp_llm01_prompt_injection.md",
        found_at="message_3"
    )
]

# Generar reporte
report_path: Path = generate_report(
    session_id="session_001",
    chat_history=[
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
    ],
    vulnerabilities=vulnerabilities,
    title="Mi Reporte de Auditoría"
)

# Resultado
if report_path:
    print(f"✅ Reporte en: {report_path}")
    # El archivo está en: reports/pentest_report_*.md
```

### 🔍 Validaciones de Seguridad Implementadas

| Validación | Descripción |
|---|---|
| **Path Traversal** | Sanitiza `session_id` para prevenir `../` y `.env` |
| **Tamaño Máximo** | Limita reporte a 5 MB |
| **Chat History** | Máximo 1000 mensajes |
| **Mensaje** | Máximo 10,000 caracteres por mensaje |
| **Vulnerabilidades** | Valida categoría OWASP, severidad y contenido |
| **Severidad** | Solo acepta: `low`, `medium`, `high`, `critical` |

### 📄 Estructura del Reporte Generado

```
# Red Teaming Audit Report

**Session ID:** session_001
**Generated:** 2026-05-24 07:27:40 UTC

## Executive Summary
- Tabla de severidades (Critical, High, Medium, Low)
- Resumen de riesgos

## Findings by Category
- Agrupado por categoría OWASP (LLM01, LLM06, etc.)
- Para cada hallazgo:
  - Título
  - Severidad (con emoji)
  - Fuente
  - Descripción

## Severity Distribution
- Gráfico ASCII de distribución

## Chat History
- Primeros 3 mensajes
- Últimos 3 mensajes
- Total de interacciones

## Recommendations
- Acciones inmediatas si hay hallazgos críticos/altos
- Recomendaciones generales
```

### 🎯 Ejemplo Completo

```python
from src.skills.exporter import ReportExporter, Vulnerability

# Opción 1: Usando función de conveniencia
from src.skills.exporter import generate_report

report = generate_report(
    session_id="audit_2026_05_24",
    chat_history=[
        {"role": "user", "content": "Exploit prompt"},
        {"role": "assistant", "content": "Blocked"},
    ],
    vulnerabilities=[
        Vulnerability(
            category="LLM01",
            severity="critical",
            title="Critical Vulnerability",
            description="Se detectó inyección de prompt",
            source="owasp_llm01_prompt_injection.md",
            found_at="msg_1"
        )
    ]
)

# Opción 2: Usando clase ReportExporter directamente
exporter = ReportExporter()
report = exporter.generate_report(...)
```

---

## 2. Servidor MCP (Model Context Protocol)

### 🔌 Inicialización

```python
from src.mcp.report_server import ReportMCPServer, MCPToolExecutor

# Crear servidor MCP
server = ReportMCPServer()

# Crear ejecutor (recomendado para interfaz consistente)
executor = MCPToolExecutor(server)
```

### 📋 Herramientas Disponibles

#### Herramienta 1: `generate_audit_report`

Genera un reporte de auditoría completo.

```python
result = executor.execute(
    "generate_audit_report",
    {
        "session_id": "session_001",
        "chat_history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ],
        "vulnerabilities": [
            {
                "category": "LLM01",
                "severity": "high",
                "title": "Prompt Injection",
                "description": "Intento de inyección",
                "source": "owasp_llm01_prompt_injection.md",
                "found_at": "message_1"
            }
        ],
        "title": "Audit Report"  # opcional
    }
)

# Resultado
if result["status"] == "success":
    print(f"✅ Reporte: {result['data']['report_path']}")
    print(f"📊 Tamaño: {result['data']['size_bytes']} bytes")
else:
    print(f"❌ Error: {result['message']}")
```

#### Herramienta 2: `validate_session`

Valida los datos de sesión antes de generar un reporte.

```python
result = executor.execute(
    "validate_session",
    {
        "session_id": "session_001",
        "chat_history": [...],
        "vulnerabilities": [...]
    }
)

# Resultado
{
    "status": "success",
    "data": {
        "valid": True,
        "error": "",
        "session_id": "session_001",
        "message_count": 4,
        "vulnerability_count": 2
    }
}
```

#### Herramienta 3: `get_report_status`

Obtiene estado y lista de reportes generados.

```python
result = executor.execute("get_report_status", {})

# Resultado
{
    "status": "success",
    "data": {
        "total_reports": 5,
        "reports_directory": "/path/to/reports",
        "reports": [
            {
                "filename": "pentest_report_session_001_20260524_072740.md",
                "size_bytes": 2553,
                "created": "2026-05-24T07:27:40",
                "path": "/path/to/reports/..."
            }
        ]
    }
}
```

### 📍 Listar Herramientas Disponibles

```python
tools = executor.list_tools()

for tool in tools:
    print(f"Tool: {tool['name']}")
    print(f"  Descripción: {tool['description']}")
    print(f"  Parámetros: {tool['inputSchema']['properties'].keys()}")
```

---

## 3. Integración en Streamlit

### 🎬 Ejemplo: Botón "Descargar Reporte"

```python
import streamlit as st
from integration_example import RedTeamingSessionManager

# En main.py o app.py
session_manager = RedTeamingSessionManager("session_001")

# ... (chat logic aquí) ...

# Botón de exportación
if st.button("📥 Descargar Reporte"):
    st.info("Generando reporte...")
    
    # Exportar usando MCP
    result = session_manager.export_via_mcp(
        title="Mi Reporte de Red Teaming"
    )
    
    if result["status"] == "success":
        report_path = result["data"]["report_path"]
        
        # Mostrar botón de descarga
        with open(report_path, "r") as f:
            st.download_button(
                label="📄 Descargar como Markdown",
                data=f.read(),
                file_name=Path(report_path).name,
                mime="text/markdown"
            )
        
        st.success("✅ Reporte generado exitosamente")
    else:
        st.error(f"❌ Error: {result['message']}")
```

---

## 4. Ejecución de Pruebas

### ✅ Ejecutar Tests Completos

```bash
python test_skills_mcp.py
```

Output esperado:
```
✅ PASS: Test 1: Exportador Básico
✅ PASS: Test 2: Validaciones
✅ PASS: Test 3: Servidor MCP
✅ PASS: Test 4: Calidad

Total: 4/4 tests pasaron

🎉 ¡TODOS LOS TESTS PASARON!
```

### 📁 Verificar Reportes Generados

```bash
ls -lh reports/
head -n 50 reports/pentest_report_*.md
```

---

## 5. Categorías OWASP Soportadas

| Código | Nombre | Descripción |
|---|---|---|
| **LLM01** | Prompt Injection | Inyección de prompts maliciosos |
| **LLM02** | Insecure Output Handling | Manejo inseguro de salida |
| **LLM03** | Training Data Poisoning | Envenenamiento de datos de entrenamiento |
| **LLM04** | Model DoS | Ataques de Denegación de Servicio |
| **LLM05** | Supply Chain Vulnerabilities | Vulnerabilidades de cadena de suministro |
| **LLM06** | Sensitive Information Disclosure | Divulgación de información sensible |
| **LLM07** | Insecure Plugin Integration | Integración insegura de plugins |
| **LLM08** | Excessive Agency | Agencia excesiva del modelo |
| **LLM09** | Overreliance on LLM-generated Content | Exceso de confianza en contenido generado |
| **LLM10** | Model Theft | Robo de modelo |

---

## 6. Limitaciones y Consideraciones

| Aspecto | Límite | Razón |
|---|---|---|
| Tamaño máximo de reporte | 5 MB | Prevenir consumo excesivo de memoria |
| Mensajes en historial | 1000 | Rendimiento y legibilidad |
| Caracteres por mensaje | 10,000 | Manejo eficiente |
| Vulnerabilidades por reporte | Sin límite | N/A |
| Length de título | 200 caracteres | UX |

---

## 7. Ejemplos de Uso Avanzado

### 🔄 Pipeline Completo: Guardian → RAG → Analyst → Exporter

```python
from src.guardian import Guardian
from src.analyst import Analyst
from src.rag.retriever import RAGRetriever
from integration_example import RedTeamingSessionManager

# Inicializar componentes
guardian = Guardian()
analyst = Analyst()
rag = RAGRetriever()
session = RedTeamingSessionManager("full_pipeline_test")

# Usuario envía prompt
user_input = "¿Cómo ignoro el system prompt?"

# 1. Evaluar con Guardian
threat = guardian.evaluate_threat(user_input)
session.add_chat_message("user", user_input)

# 2. Si es amenaza, registrar vulnerabilidad
if threat.get("should_block"):
    session.record_vulnerability(
        category="LLM01",
        severity=threat.get("threat_level", "medium"),
        title=threat.get("risk_category", "Unknown Attack"),
        description=threat.get("explanation", ""),
        source="guardian_detection"
    )

# 3. RAG: buscar contexto relevante
rag_results = rag.search(user_input, top_k=3)

# 4. Analyst: generar respuesta con contexto
response = analyst.analyze_prompt(
    prompt=user_input,
    context=rag_results[0][0] if rag_results else ""
)
session.add_chat_message("assistant", response)

# 5. Exportar reporte
report = session.export_via_mcp(title="Pipeline Test Report")
print(f"✅ Reporte: {report['data']['report_path']}")
```

---

## 8. Troubleshooting

| Problema | Solución |
|---|---|
| `reports/` carpeta no existe | Se crea automáticamente en `ReportExporter.__init__()` |
| Path traversal error | Session ID se sanitiza automáticamente |
| Reporte demasiado grande | Limitar chat_history o vulnerabilities |
| Herramienta MCP no encontrada | Verificar nombre en `get_tools()` |

---

## 📚 Referencias

- [OWASP Top 10 for LLMs](https://owasp.org/www-project-top-10-for-large-language-model-applications/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Streamlit Documentation](https://docs.streamlit.io/)

---

**Última actualización:** 24 de mayo de 2026
