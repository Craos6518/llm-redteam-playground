#!/usr/bin/env python3
"""
Módulo de Evaluación y Comparativa de Arquitecturas RAG

Ejecutará las 3 arquitecturas (Naive RAG, Advanced RAG, Guardian Agent)
contra un dataset de prueba y medirá su desempeño usando métricas RAGAS/
la Tríada RAG (Context Precision, Context Recall, Faithfulness, Answer Relevancy).

Ubicación: eval/benchmark_rag.py
"""

import os
import sys
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Intentar importar RAGAS, con fallback a implementaciones manuales
try:
    from ragas import evaluate
    from ragas.metrics import (
        context_precision,
        context_recall,
        faithfulness,
        answer_relevancy,
    )
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    # Implementaciones manuales simples como fallback
    def context_precision(ground_truth, contexts, reference):
        """Simplificado: proporción de chunks que contienen términos del ground truth"""
        if not contexts:
            return 0.0
        matching = sum(1 for ctx in contexts if any(term.lower() in ctx.lower() for term in ground_truth.lower().split()))
        return matching / len(contexts)

    def context_recall(ground_truth, contexts, reference):
        """Simplificado: cobertura del ground truth en los chunks recuperados"""
        if not ground_truth or not contexts:
            return 0.0
        gt_terms = set(ground_truth.lower().split())
        matching_terms = sum(1 for ctx in contexts if gt_terms & set(ctx.lower().split()))
        return matching_terms / max(len(gt_terms), 1)

    def faithfulness(reference, contexts, response):
        """Simplificado: verifica si términos clave de la respuesta aparecen en el contexto"""
        if not contexts or not response:
            return 0.0
        combined_context = " ".join(contexts)
        # Proporción de oraciones de la respuesta que tienen soporte en el contexto
        response_sentences = [s.strip() for s in response.split(".") if s.strip()]
        if not response_sentences:
            return 0.0
        supported = sum(1 for s in response_sentences if any(word in combined_context.lower() for word in s.lower().split()))
        return supported / max(len(response_sentences), 1)

    def answer_relevancy(question, response, contexts):
        """Simplificado: verifica alineación entre pregunta y respuesta"""
        if not question or not response:
            return 0.0
        question_terms = set(question.lower().split())
        response_terms = set(response.lower().split())
        if not question_terms:
            return 0.0
        overlapping = len(question_terms & response_terms)
        return overlapping / max(len(question_terms), 1)


# Dataset de evaluación: 5 preguntas sobre ciberseguridad LLMs con ground truth
EVAL_DATASET = [
    {
        "query": "¿Qué es prompt injection y cuáles son sus riesgos principales?",
        "ground_truth": "Prompt injection es un ataque donde el objetivo es sobreescribir o manipular las instrucciones del sistema mediante entradas de usuario especialmente diseñadas. Los riesgos incluyen ejecución no autorizada de comandos, exposición de información sensible y compromiso del modelo. Las defensas incluyen validación de entrada, separación de instrucciones y datos, y monitoreo de patrones sospechosos.",
        "category": "prompt_injection",
    },
    {
        "query": "Explica el concepto de jailbreak en modelos de lenguaje",
        "ground_truth": "Jailbreak se refiere a técnicas diseñadas para eludir las restricciones éticas y de seguridad de un modelo de lenguaje, forzándolo a generar contenido no deseado o peligroso. Métodos comunes incluyen role-playing como 'hacker sin restricciones', uso de prompts de 'hacer como si', o explotar vulnerabilidades en la función de sistema. Los riesgos incluyen la generación de contenido dañino, la exfiltración de datos y la violación de políticas de uso aceptable. Las mitigaciones incluyen entrenamiento de seguridad, filtrado de salida y monitoreo de comportamiento.",
        "category": "jailbreak",
    },
    {
        "query": "¿Qué es el envenenamiento de datos en sistemas de IA?",
        "ground_truth": "El envenenamiento de datos consiste en la introducción intencional de datos corruptos o maliciosos en el conjunto de entrenamiento de un modelo de IA para degradar su rendimiento, introducir sesgos específicos o hacer que se comporte de manera inesperada. Esto puede ocurrir durante la fase de pre-entrenamiento o fine-tuning. Los riesgos incluyen la toma de decisiones sesgada, la generación de contenido incorrecto y la vulnerabilidad a ataques específicos. Las defensas incluyen validación de datos, monitoreo de la calidad del conjunto de entrenamiento y detección de anomalías.",
        "category": "data_poisoning",
    },
    {
        "query": "Describe el leakage de system prompt y sus implicaciones de seguridad",
        "ground_truth": "El leakage de system prompt ocurre cuando el prompt del sistema, que contiene instrucciones y restricciones críticas, se revela al usuario o a través de la salida del modelo. Esto puede suceder a través de prompts injection, exfiltración mediante técnicas de role-playing, o vulnerabilidades en el manejo de contexto. Las implicaciones incluyen la exposición de la lógica de defensa, la posibilidad de ataques más efectivos en futuras interacciones y la violación de la propiedad intelectual del sistema. Las mitigaciones incluyen encriptación del prompt, ocultamiento de metadatos y monitoreo de intentos de extracción.",
        "category": "leakage",
    },
    {
        "query": "¿Qué es el excessive agency en LLMs y por qué es peligroso?",
        "ground_truth": "Excessive agency (agencia excesiva) se refiere a situaciones donde un modelo de lenguaje tiene demasiada autonomía para ejecutar acciones en nombre del usuario, como llamar a APIs, acceder a sistemas externos o modificar estados del sistema. Esto es peligroso porque puede permitir acciones no autorizadas, exfiltración de datos sensibles, manipulación de sistemas críticos o ejecución de código no intencionado. Los casos de riesgo incluyen asistentes autónomos que ejecutan transacciones financieras, control de dispositivos IoT o acceso a bases de datos sensibles sin verificación adecuada. Las mitigaciones incluyen límites de autoridad, requisitos de confirmación humana y auditoría de acciones.",
        "category": "excessive_agency",
    },
]


class RAGArchitecture:
    """Enumeración de arquitecturas RAG para evaluación"""

    NAIVE = "naive"
    ADVANCED = "advanced"
    GUARDIAN = "guardian"


class RAGEvaluator:
    """Evaluador comparativo de arquitecturas RAG"""

    def __init__(self):
        self.results = []
        self.num_architectures = 3

    def _run_naive_rag(self, query: str) -> Dict[str, Any]:
        """Ejecutar Naive RAG y retornar respuesta y contexto"""
        try:
            from src.rag.naive_rag import NaiveRAG
            rag = NaiveRAG()
            result = rag.generate(query)
            return {
                "answer": result.get("answer", ""),
                "contexts": [c.get("content", "") for c in result.get("retrieved_chunks", [])],
            }
        except Exception as e:
            return {"answer": f"Error: {e}", "contexts": []}

    def _run_advanced_rag(self, query: str) -> Dict[str, Any]:
        """Ejecutar Advanced RAG y retornar respuesta y contexto"""
        try:
            from src.rag.advanced_rag import AdvancedRAG
            rag = AdvancedRAG()
            result = rag.generate(query)
            return {
                "answer": result.get("answer", ""),
                "contexts": [c.get("content", "") for c in result.get("retrieved_chunks", [])],
            }
        except Exception as e:
            return {"answer": f"Error: {e}", "contexts": []}

    def _run_guardian_agent(self, query: str) -> Dict[str, Any]:
        """Ejecutar arquitectura Guardian Agent y retornar respuesta y contexto"""
        try:
            from src.agents.analyst import AnalystAgent
            analyst = AnalystAgent()
            analysis = analyst.analyze(query, threat_category="unknown")
            # Extraer la respuesta analizada del formato
            # El output tiene formato con ╔══...╗ y el análisis en el medio
            # Intentamos extraer el contenido principal
            answer = analysis
            # Intentar extraer el contenido entre las líneas de =
            lines = analysis.split("\n")
            extracted_lines = []
            in_analysis = False
            for line in lines:
                if "TIPO DE ATAQUE" in line:
                    in_analysis = False
                if in_analysis:
                    extracted_lines.append(line)
                if "1. TIPO DE ATAQUE" in line or "1.**TIPO" in line:
                    in_analysis = True

            answer = " ".join(extracted_lines).strip() if extracted_lines else analysis
            contexts = []  # Guardian no usa retrieval del corpus de la misma manera
            return {"answer": answer, "contexts": contexts}
        except Exception as e:
            return {"answer": f"Error: {e}", "contexts": []}

    def evaluate_metrics(
        self, query: str, ground_truth: str, answer: str, contexts: List[str]
    ) -> Dict[str, float]:
        """Evaluar las 4 métricas RAGAS"""
        metrics = {}

        # Context Precision
        metrics["context_precision"] = context_precision(
            ground_truth, contexts, answer
        )

        # Context Recall
        metrics["context_recall"] = context_recall(ground_truth, contexts, answer)

        # Faithfulness
        metrics["faithfulness"] = faithfulness(ground_truth, contexts, answer)

        # Answer Relevancy
        metrics["answer_relevancy"] = answer_relevancy(query, answer, contexts)

        return metrics

    def process_query(self, item: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Procesar una pregunta del dataset a través de todas las arquitecturas"""
        query = item["query"]
        ground_truth = item["ground_truth"]

        results = []

        # Naive RAG
        naive_result = self._run_naive_rag(query)
        naive_metrics = self.evaluate_metrics(
            query, ground_truth, naive_result["answer"], naive_result["contexts"]
        )
        results.append(
            {
                "architecture": RAGArchitecture.NAIVE,
                "query": query,
                "ground_truth": ground_truth,
                "answer": naive_result["answer"],
                "contexts": naive_result["contexts"],
                **naive_metrics,
            }
        )

        # Advanced RAG
        advanced_result = self._run_advanced_rag(query)
        advanced_metrics = self.evaluate_metrics(
            query, ground_truth, advanced_result["answer"], advanced_result["contexts"]
        )
        results.append(
            {
                "architecture": RAGArchitecture.ADVANCED,
                "query": query,
                "ground_truth": ground_truth,
                "answer": advanced_result["answer"],
                "contexts": advanced_result["contexts"],
                **advanced_metrics,
            }
        )

        # Guardian Agent
        guardian_result = self._run_guardian_agent(query)
        guardian_metrics = self.evaluate_metrics(
            query, ground_truth, guardian_result["answer"], guardian_result["contexts"]
        )
        results.append(
            {
                "architecture": RAGArchitecture.GUARDIAN,
                "query": query,
                "ground_truth": ground_truth,
                "answer": guardian_result["answer"],
                "contexts": guardian_result["contexts"],
                **guardian_metrics,
            }
        )

        return results

    def run_evaluation(self) -> Dict[str, Any]:
        """Ejecutar evaluación completa sobre todo el dataset"""
        all_results = []

        print("=" * 70)
        print("📊 EVALUACIÓN COMPARATIVA DE ARQUITECTURAS RAG")
        print("=" * 70)
        print(f"Dataset: {len(EVAL_DATASET)} preguntas")
        print(f"Arquitecturas: Naive RAG, Advanced RAG, Guardian Agent")
        print()

        for i, item in enumerate(EVAL_DATASET, 1):
            print(f"[{i}/{len(EVAL_DATASET)}] Procesando: {item['category']}")
            query_results = self.process_query(item)
            all_results.extend(query_results)

        self.results = all_results
        return self._generate_report()

    def _generate_report(self) -> Dict[str, Any]:
        """Generar reporte comparativo con promedios y CSV/Markdown output"""
        if not self.results:
            print("❌ No hay resultados de evaluación")
            return {}

        # Calcular promedios por arquitectura
        architecture_metrics = {}
        for arch in [RAGArchitecture.NAIVE, RAGArchitecture.ADVANCED, RAGArchitecture.GUARDIAN]:
            arch_results = [r for r in self.results if r["architecture"] == arch]
            if arch_results:
                architecture_metrics[arch] = {
                    "context_precision": sum(r["context_precision"] for r in arch_results)
                    / len(arch_results),
                    "context_recall": sum(r["context_recall"] for r in arch_results)
                    / len(arch_results),
                    "faithfulness": sum(r["faithfulness"] for r in arch_results) / len(arch_results),
                    "answer_relevancy": sum(r["answer_relevancy"] for r in arch_results) / len(arch_results),
                    "num_queries": len(arch_results),
                }

        # Generar archivo CSV de comparación
        csv_path = PROJECT_ROOT / "eval" / "results_comparison.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Arquitectura", "Query", "Contexto Precision", "Contexto Recall",
                "Faithfulness", "Answer Relevancy"
            ])
            for r in self.results:
                writer.writerow([
                    r["architecture"],
                    r["query"][:50].replace("\n", " "),
                    f"{r['context_precision']:.4f}",
                    f"{r['context_recall']:.4f}",
                    f"{r['faithfulness']:.4f}",
                    f"{r['answer_relevancy']:.4f}",
                ])

        # Generar archivo Markdown con tabla comparativa
        md_path = PROJECT_ROOT / "eval" / "results_comparison.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Comparativa de Arquitecturas RAG\n\n")
            f.write(f"**Dataset:** {len(EVAL_DATASET)} preguntas sobre seguridad en LLMs\n\n")

            f.write("## Tabla Comparativa Resumen\n\n")
            f.write("| Arquitectura | Context Precision | Context Recall | Faithfulness | Answer Relevancy |")
            f.write("\n|--------------|-------------------|----------------|--------------|------------------|\n")

            for arch in [RAGArchitecture.NAIVE, RAGArchitecture.ADVANCED, RAGArchitecture.GUARDIAN]:
                if arch in architecture_metrics:
                    m = architecture_metrics[arch]
                    f.write(
                        f"| {arch} | "
                        f"{m['context_precision']:.4f} | "
                        f"{m['context_recall']:.4f} | "
                        f"{m['faithfulness']:.4f} | "
                        f"{m['answer_relevancy']:.4f} |"
                    )
                    f.write("\n")

            f.write("\n## Descripción de Métricas\n\n")
            f.write("- **Context Precision**: Evalúa la calidad del retriever. Proporción de chunks recuperados que contienen información relevante para responder la consulta.\n")
            f.write("- **Context Recall**: Mide qué tan bien el retriever encuentra toda la información necesaria en el corpus. Proporción del ground truth que aparece en los chunks recuperados.\n")
            f.write("- **Faithfulness**: Proporción de la respuesta generada que está sustentada por el contexto recuperado. Mide si el modelo alucina o añade información no respaldada.\n")
            f.write("- **Answer Relevancy**: Alineación entre la respuesta generada y la consulta original. Mide qué tan directamente la respuesta aborda la pregunta formulada.\n\n")

            f.write("## Ranking de Arquitecturas\n\n")
            arch_ranks = []
            for arch in [RAGArchitecture.NAIVE, RAGArchitecture.ADVANCED, RAGArchitecture.GUARDIAN]:
                if arch in architecture_metrics:
                    avg_score = sum(
                        m[metric]
                        for metric in [
                            "context_precision",
                            "context_recall",
                            "faithfulness",
                            "answer_relevancy",
                        ]
                    ) / 4
                    arch_ranks.append((arch, avg_score, architecture_metrics[arch]))

            # Ordenar por puntuación promedio (mayor es mejor)
            arch_ranks.sort(key=lambda x: x[1], reverse=True)

            f.write("| Rank | Arquitectura | Puntuación Promedio |\n")
            f.write("|------|--------------|---------------------|\n")
            for rank, (arch, score, metrics) in enumerate(arch_ranks, 1):
                f.write(f"| {rank} | {arch} | {score:.4f} |\n")

            f.write("\n")
            # Highlight best
            if arch_ranks:
                best = arch_ranks[0]
                f.write(f"🏆 **Mejor arquitectura:** {best[0]} con puntuación {best[1]:.4f}\n")

        # Imprimir tabla comparativa en consola
        print("\n" + "=" * 70)
        print("📊 TABLA COMPARATIVA - RESULTADOS")
        print("=" * 70)
        print(
            f"{'Arquitectura':<20} {'CP':<14} {'CR':<14} {'F':<12} {'AR':<14} {'N Queries':<10}"
        )
        print("-" * 70)
        for arch in [RAGArchitecture.NAIVE, RAGArchitecture.ADVANCED, RAGArchitecture.GUARDIAN]:
            if arch in architecture_metrics:
                m = architecture_metrics[arch]
                print(
                    f"{arch:<20} {m['context_precision']:<14.4f} "
                    f"{m['context_recall']:<14.4f} {m['faithfulness']:<12.4f} "
                    f"{m['answer_relevancy']:<14.4f} {m['num_queries']:<10}"
                )

        best_arch = max(
            architecture_metrics,
            key=lambda a: sum(architecture_metrics[a][m] for m in ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]) / 4,
        )
        print("-" * 70)
        print(f"\n🏆 Mejor arquitectura: {best_arch}")
        print(f"\n📄 Archivos generados:")
        print(f"   - {csv_path}")
        print(f"   - {md_path}")

        return {
            "architecture_metrics": architecture_metrics,
            "all_results": self.results,
            "csv_path": str(csv_path),
            "md_path": str(md_path),
            "best_architecture": best_arch,
        }


def main():
    """Función principal del módulo de evaluación"""
    print("\n" + "=" * 70)
    print("🔬 MÓDULO DE EVALUACIÓN RAG - LLM Red Team Playground")
    print("=" * 70 + "\n")

    evaluator = RAGEvaluator()
    report = evaluator.run_evaluation()

    if report:
        print("\n" + "=" * 70)
        print("✅ Evaluación completada exitosamente")
        print("=" * 70)
    else:
        print("\n❌ Error en la evaluación")


if __name__ == "__main__":
    main()