# Proyecto Final – Introducción a la IA

## Proyecto Final  
### Introducción a la Inteligencia Artificial  
### Asistente Inteligente con RAG y Multiagentes

---

## 1. Información General

- **Proyecto:** Asistente Inteligente con RAG y Multiagentes  
- **Modalidad:** Parejas (2 estudiantes)  
- **Duración:** 8 días  
- **Exposición:** 10 minutos por pareja  
- **Entregables:** Repositorio GitHub público + Informe (4–6 páginas) + Demo funcional  

---

## 2. Objetivo

Construir un asistente especializado en un dominio elegido por la pareja (educación, turismo regional, soporte técnico, recetas, deportes, etc.) que integre los conceptos vistos en clase:

- Arquitectura Transformer
- Embeddings
- Bases de datos vectoriales
- RAG
- LLMs
- Multiagentes
- MCP y Skills

Todo bajo una arquitectura de software documentada.

---

## 3. Descripción

El sistema debe permitir al usuario hacer preguntas en lenguaje natural sobre un tema específico, responder usando información recuperada de un corpus propio (mínimo 15 documentos), coordinar al menos dos agentes con roles distintos, y entregar respuestas con citación de las fuentes consultadas.

---

## 4. Requisitos Técnicos (todo con herramientas gratuitas)

| Componente | Especificación |
|---|---|
| **LLM** | Modelo local Llama 3.2, Qwen 2.5, Mistral o API gratuita (Groq, Google AI Studio, OpenRouter free tier). Explicar conceptualmente cómo funciona la arquitectura Transformer del modelo elegido. |
| **Embeddings** | Modelo gratuito como `sentence-transformers`, `nomic-embed-text` o similar. Justificar la elección. |
| **Base vectorial** | ChromaDB, FAISS o LanceDB (todas open source y locales). |
| **RAG** | Pipeline completo de ingesta → chunking → embedding → recuperación → generación. Aplicar al menos una mejora sobre el RAG básico (re-ranking, búsqueda híbrida o ajuste de chunking). |
| **Multiagentes** | Mínimo dos agentes con roles diferenciados (por ejemplo: uno busca información y otro redacta la respuesta). Usar LangGraph, CrewAI o implementación propia. |
| **MCP** | Integrar al menos un servidor MCP (existente o propio). |
| **Skills** | Implementar al menos una Skill personalizada que extienda al agente (generar un reporte, procesar un archivo, consumir una API gratuita, etc.). |
| **Interfaz** | Streamlit o Gradio (ambas gratuitas y fáciles). |
| **Lenguaje** | Python 3.11+ |

---

## 5. Documentación de Arquitectura

En la carpeta `/docs` del repositorio debe haber:

- Un diagrama de arquitectura general del sistema.
- Un diagrama del flujo RAG.
- Un diagrama de interacción entre los agentes.
- Mínimo tres decisiones técnicas justificadas en formato corto:
  - contexto
  - decisión
  - consecuencias

---

## 6. Entregables

### 6.1 Repositorio GitHub público

Estructura clara con las carpetas:

- `src/`
- `docs/`
- `data/`
- `tests/`

Además debe incluir:

- `README.md` con instrucciones de instalación y uso
- `requirements.txt`
- `.env.example`

El historial de commits debe mostrar trabajo de ambos integrantes.

---

### 6.2 Informe técnico (4–6 páginas, PDF)

Debe incluir:

- Portada con integrantes y URL del repositorio.
- Introducción y dominio elegido.
- Arquitectura implementada (con diagrama).
- Una sección breve por cada concepto aplicado:
  - Transformer
  - embeddings
  - base vectorial
  - RAG
  - multiagente
  - MCP
  - Skills

Explicando qué y cómo se implementó.

- Decisiones técnicas relevantes.
- Resultados con capturas y limitaciones.
- Conclusiones y referencias.

---

### 6.3 Presentación oral (10 minutos)

Debe cubrir:

- contexto y dominio
- arquitectura general
- demo en vivo
- explicación técnica de un componente
- conclusiones

Ambos integrantes deben hablar.

---

## 7. Criterios de Evaluación (100 puntos)

| Criterio | Puntos |
|---|---|
| Funcionalidad end-to-end del sistema | 20 |
| Pipeline RAG implementado correctamente | 15 |
| Diseño multiagente | 15 |
| Integración de MCP y Skills | 10 |
| Arquitectura y documentación (diagramas, decisiones) | 10 |
| Calidad del repositorio (estructura, commits, README) | 10 |
| Informe técnico | 10 |
| Presentación y demo | 10 |
| **TOTAL** | **100** |

---

## 8. Consideraciones

El corpus debe usar fuentes abiertas, propias o con licencia clara.

Se permite el uso de asistentes de código:

- Claude
- Copilot
- Cursor

Siempre que los estudiantes puedan explicar cualquier línea durante la sustentación.

El sistema no debe presentarse como sustituto de asesoría profesional si el dominio lo involucra.