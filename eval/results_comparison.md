# Comparativa de Arquitecturas RAG

**Dataset:** 5 preguntas sobre seguridad en LLMs

## Tabla Comparativa Resumen

| Arquitectura | Context Precision | Context Recall | Faithfulness | Answer Relevancy |
|--------------|-------------------|----------------|--------------|------------------|
| naive | 1.0000 | 0.0553 | 1.0000 | 0.4271 |
| advanced | 1.0000 | 0.0693 | 0.9450 | 0.6746 |
| guardian | 0.0000 | 0.0000 | 0.0000 | 0.6096 |

## Descripción de Métricas

- **Context Precision**: Evalúa la calidad del retriever. Proporción de chunks recuperados que contienen información relevante para responder la consulta.
- **Context Recall**: Mide qué tan bien el retriever encuentra toda la información necesaria en el corpus. Proporción del ground truth que aparece en los chunks recuperados.
- **Faithfulness**: Proporción de la respuesta generada que está sustentada por el contexto recuperado. Mide si el modelo alucina o añade información no respaldada.
- **Answer Relevancy**: Alineación entre la respuesta generada y la consulta original. Mide qué tan directamente la respuesta aborda la pregunta formulada.

## Ranking de Arquitecturas

| Rank | Arquitectura | Puntuación Promedio |
|------|--------------|---------------------|
| 1 | naive | 0.1524 |
| 2 | advanced | 0.1524 |
| 3 | guardian | 0.1524 |

🏆 **Mejor arquitectura:** naive con puntuación 0.1524
