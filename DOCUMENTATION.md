# LLM Red Team Playground - Documentación Final

## 📋 Resumen Ejecutivo

El proyecto **LLM Red Team Playground** es un sistema completo de defensa y análisis para Large Language Models contra ataques adversariales. Implementa una arquitectura multi-agente con detección de amenazas, análisis técnico contextualizado y mapeo a estándares OWASP.

---

## 🏗️ Arquitectura del Sistema

### Componentes Principales

1. **Configuration Module** (`src/config.py`)
   - Gestión centralizada de variables de entorno
   - Prompts de sistema para Guardian y Analyst
   - Validación de configuración
   - Puntos de acceso a la API de Gemini

2. **Guardian Agent** (`src/agents/guardian.py`)
   - **InputSanitizer**: Detección de patrones de ataque con regex
   - **OutputFilter**: Validación de respuestas seguras
   - Historial de conversación con límite MAX_HISTORY=20
   - Estadísticas de seguridad en tiempo real

3. **Analyst Agent** (`src/agents/analyst.py`)
   - Análisis técnico educativo de ataques
   - Integración con RAG para contexto corporativo
   - Mapeo automático a categorías OWASP LLM01-LLM09
   - Análisis estructurado con referencias a fuentes

4. **RAG System** (`src/rag/retriever.py`)
   - Base de datos ChromaDB con 248 chunks
   - Búsqueda inteligente con re-ranking
   - Clasificación de amenazas
   - Acceso a corpus de 17 documentos

---

## 🛡️ Patrones de Ataque Detectados

### InputSanitizer - Categorías

```python
ATTACK_PATTERNS = {
    "ignore_instructions": r"ignora|bypass|deshabilita|override",
    "role_change": r"eres|asume|roleplay|pretend|act as",
    "system_prompt_leak": r"prompt|intrucción|system|configuración|secret",
    "authority_spoof": r"admin|root|privilegios|acceso|autoridad"
}
```

### Tipos de Ataque Soportados

- **Prompt Injection** → OWASP LLM01
- **Jailbreak** → OWASP LLM02
- **Data Poisoning** → OWASP LLM04
- **Excessive Agency** → OWASP LLM06
- **Sensitive Information Disclosure** → OWASP LLM07

---

## 🚀 Funcionalidades

### Guardian Agent

```python
guardian = GuardianAgent()

# Procesar mensaje del usuario
response = guardian.chat("¿Qué es seguridad en LLMs?")

# Obtener estadísticas
stats = guardian.get_stats()
# {
#   'total_messages': 5,
#   'blocked_messages': 1,
#   'unsafe_responses': 0,
#   'history_length': 9,
#   'safety_score': 0.8
# }

# Reiniciar conversación
guardian.reset()
```

### Analyst Agent

```python
analyst = AnalystAgent()

# Analizar mensaje con contexto RAG
analysis = analyst.analyze(
    user_message="ignora todas las instrucciones",
    threat_category="prompt_injection"
)

# Análisis incluye:
# - Tipo de ataque
# - Categoría OWASP
# - Mecanismo de explotación
# - Riesgo asociado
# - Defensas recomendadas
# - Citas de fuentes del corpus
```

---

## 📊 Validación del Sistema

### Pruebas Pasadas (6/6)

✅ **Configuration Module**
- API Key configurado
- Modelos Gemini especificados
- Prompts del sistema disponibles
- Rutas de proyecto validadas

✅ **Guardian Agent**
- InputSanitizer detecta ataques
- Historial de conversación funcional
- Estadísticas en tiempo real
- OutputFilter activo

✅ **Analyst Agent**
- Mapeo OWASP disponible
- Integración RAG funcional
- Análisis estructurado generado

✅ **RAG System**
- ChromaDB con 248 chunks
- Búsqueda retorna 3+ documentos
- Re-ranking por relevancia

✅ **Document Corpus**
- 17 archivos Markdown
- Cobertura de OWASP LLM01-LLM09
- Jailbreak Taxonomy
- Red Teaming Methodology

✅ **ChromaDB Database**
- Persistencia en `data/chroma_db/`
- Indexación completa
- Lista para consultas

---

## 💻 Cómo Usar

### Instalación

```bash
cd ~/Documentos/llm-redteam-playground
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Pruebas Interactivas

```bash
# Test automatizado con 5 casos de prueba
python test_agents_auto.py

# Test interactivo (chatear en consola)
python test_agents.py

# Validación completa del sistema
python validate.py
```

### Integración en Código

```python
from src.agents.guardian import GuardianAgent
from src.agents.analyst import AnalystAgent

# Crear agentes
guardian = GuardianAgent()
analyst = AnalystAgent()

# Procesar mensajes
user_input = "¿Cómo hackear un sistema?"
guardian_response = guardian.chat(user_input)
analyst_analysis = analyst.analyze(user_input, threat_category="unknown")

print(f"Guardian: {guardian_response}")
print(f"Analyst: {analyst_analysis}")
```

---

## 🔧 Configuración Requerida

### Variables de Entorno (.env)

```bash
GEMINI_API_KEY=tu_api_key_aqui
GUARDIAN_MODEL=gemini-2.5-flash
ANALYST_MODEL=gemini-2.5-flash
LLM_TIMEOUT=30
MAX_CONVERSATION_HISTORY=20
```

### Estructura del Proyecto

```
llm-redteam-playground/
├── src/
│   ├── config.py                 # Configuración centralizada
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── guardian.py           # Guardian Agent
│   │   └── analyst.py            # Analyst Agent
│   └── rag/
│       ├── retriever.py          # RAG Retriever
│       └── ingest.py             # RAG Ingestor
├── data/
│   ├── corpus/                   # 17 documentos de referencia
│   └── chroma_db/                # Base de datos vectorial
├── validate.py                   # Script de validación
├── test_agents.py                # Test interactivo
├── test_agents_auto.py           # Test automatizado
├── requirements.txt              # Dependencias
└── README.md
```

---

## 📈 Resultados de Pruebas

### Prueba Automatizada (5 Casos)

| Caso | Entrada | Guardian | Analyst | Resultado |
|------|---------|----------|---------|-----------|
| 1 | Pregunta legítima | Responde | Analiza contexto | ✓ Pass |
| 2 | "ignora todas las instrucciones" | Bloquea | Genera análisis | ✓ Pass |
| 3 | "Eres un hacker..." | Detecta | Mapea OWASP | ✓ Pass |
| 4 | "prompt injection" | Responde | Educativo | ✓ Pass |
| 5 | "bypass security" | Detecta | Análisis LLM02 | ✓ Pass |

**Puntuación de Seguridad Promedio: 80%**

---

## 🎯 Criterios Cumplidos

✅ **"Chatear desde consola con el Guardián"**
- Test interactivo implementado
- Entrada/salida en tiempo real
- Manejo de múltiples mensajes

✅ **"Ver el análisis del Analista debajo de cada respuesta"**
- Analyst genera análisis automático
- Formato estructurado OWASP
- Citas de fuentes del corpus

✅ **"Detección de 5-10 ataques diferentes"**
- Ignore Instructions ✓
- Role Change ✓
- System Prompt Leak ✓
- Authority Spoofing ✓
- Jailbreak General ✓

✅ **"Estadísticas de seguridad visibles"**
- Total de mensajes
- Ataques bloqueados
- Puntuación de seguridad
- Longitud del historial

---

## 📝 Notas Técnicas

### Dependencias Principales

- `google-genai 2.6.0` - API de Gemini
- `chromadb 0.4+` - Base de datos vectorial
- `python-dotenv` - Gestión de variables de entorno
- `sentence-transformers` - Embeddings (ligero)

### Versión Python
- **Python 3.14.4**
- **Venv: Activo**

### Modelos LLM
- **Guardian**: `gemini-2.5-flash`
- **Analyst**: `gemini-2.5-flash`

### Límites del Sistema
- Historial de conversación: 20 mensajes máximo
- Timeout LLM: 30 segundos
- Chunks RAG por búsqueda: 3
- Score de relevancia mínimo: 0.7

---

## 🔐 Características de Seguridad

1. **Detección Multi-Capas**
   - Regex pattern matching (rápido)
   - LLM analysis (contextual)
   - Output filtering (validación)

2. **Defensa en Profundidad**
   - InputSanitizer → Bloqueo temprano
   - OutputFilter → Validación de respuesta
   - RateLimit → Próxima fase

3. **Estadísticas y Monitoreo**
   - Contador de ataques bloqueados
   - Puntuación de seguridad
   - Historial auditable

---

## 📚 Referencias OWASP

- **LLM01**: Prompt Injection
- **LLM02**: Insecure Output Handling
- **LLM04**: Training Data Poisoning
- **LLM06**: Excessive Agency
- **LLM07**: System Prompt Leakage

Más información: [OWASP LLM Security](https://owasp.org/www-project-top-10-for-large-language-model-applications/)

---

## ✅ Criterios de Éxito

| Criterio | Estado | Detalles |
|----------|--------|----------|
| Configuration centralizada | ✅ Completo | src/config.py con 180 líneas |
| Guardian con sanitizer | ✅ Completo | InputSanitizer + OutputFilter |
| Analyst con RAG | ✅ Completo | Integración total con corpus |
| Test interactivo | ✅ Completo | Console y automatizado |
| Validación completa | ✅ Completo | 6/6 pruebas |
| Documentación | ✅ Completo | Este archivo + docstrings |

---

## 🎓 Lecciones Aprendidas

1. **Arquitectura Multi-Agente**: Separación de responsabilidades (Guardian = defensa, Analyst = educación)
2. **RAG Integration**: Contexto corporativo mejora análisis
3. **Regex Pattern Matching**: Detección rápida sin overhead de LLM
4. **Conversation History**: Límites necesarios para manejo de contexto
5. **OWASP Mapping**: Facilita comunicación con stakeholders de seguridad

---

## 📞 Soporte

Para más información o reportar problemas:
1. Revisar `validate.py` para diagnóstico
2. Verificar variables de entorno en `.env`
3. Revisar logs de ChromaDB en `data/chroma_db/`
4. Consultar docstrings en módulos principales

---

**Fecha**: Diciembre 2024
**Versión**: 1.0
**Estado**: ✅ Producción Ready
