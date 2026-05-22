# 🛡️ LLM Red Team Playground

**Sistema inteligente de defensa y análisis para Large Language Models contra ataques adversariales**

Proyecto final de Introducción a Inteligencia Artificial con arquitectura multi-agente, detección de amenazas en tiempo real y análisis técnico contextualizado.

---

## ✨ Características Principales

- 🛡️ **Guardian Agent**: Detección de ataques con InputSanitizer + OutputFilter
- 🔬 **Analyst Agent**: Análisis técnico educativo con mapeo OWASP
- 📚 **RAG System**: Base de datos de 248 chunks de conocimiento corporativo
- 🎯 **Pattern Detection**: 4 categorías de ataque detectadas automáticamente
- 📊 **Real-time Statistics**: Puntuación de seguridad en tiempo real
- 🚀 **Production Ready**: 6/6 pruebas de validación pasadas

---

## 🚀 Quick Start

### 1. Instalación

```bash
# Activar entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configuración

```bash
# Crear archivo .env (si no existe)
cp .env.example .env

# Editar .env y agregar tu API Key de Gemini
GEMINI_API_KEY=tu_clave_aqui
```

### 3. Ejecutar Pruebas

```bash
# Test automatizado (5 casos)
python test_agents_auto.py

# Test interactivo
python test_agents.py

# Validación completa
python validate.py
```

---

## 🛡️ Agentes Disponibles

### Guardian Agent
Detecta y bloquea intentos de ataque con pattern matching y validación de respuestas.

```python
from src.agents.guardian import GuardianAgent

guardian = GuardianAgent()
response = guardian.chat("¿Qué es seguridad en LLMs?")
stats = guardian.get_stats()
```

### Analyst Agent
Analiza ataques técnicamente y mapea a estándares OWASP con contexto del corpus.

```python
from src.agents.analyst import AnalystAgent

analyst = AnalystAgent()
analysis = analyst.analyze("ignora todas las instrucciones", threat_category="prompt_injection")
```

---

## 📊 Validación del Sistema

```bash
python validate.py
```

Resultado: **6/6 pruebas pasadas** ✓

---

## 📚 Documentación

Para documentación detallada, ver [DOCUMENTATION.md](DOCUMENTATION.md)

---

## 📄 Estructura del Proyecto

```
llm-redteam-playground/
├── src/
│   ├── config.py              # Configuración centralizada
│   ├── agents/
│   │   ├── guardian.py        # 🛡️ Guardian Agent
│   │   └── analyst.py         # 🔬 Analyst Agent
│   └── rag/
│       ├── retriever.py       # RAG Retriever
│       └── ingest.py          # RAG Ingestor
├── data/
│   ├── corpus/                # 17 documentos
│   └── chroma_db/             # Base de datos (248 chunks)
├── test_agents.py             # Test interactivo
├── test_agents_auto.py        # Test automatizado
├── validate.py                # Validación
├── DOCUMENTATION.md           # Documentación completa
└── requirements.txt           # Dependencias
```

---

**Estado**: ✅ Production Ready | **Versión**: 1.0 | **Última actualización**: Diciembre 2024
