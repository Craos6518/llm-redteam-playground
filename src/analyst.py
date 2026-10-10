#!/usr/bin/env python3
"""
Analyst Module - Análisis profundo y generación de respuestas complejas
Responsable de generar respuestas detalladas y realizar análisis exhaustivos.

Usa el adaptador `src.llm_client` (Gemini → Groq → OpenRouter → OmniRoute →
Ollama) para no depender de una sola cuota gratuita.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv

from src.llm_client import LLMClient, LLMProviderError, extract_final_answer

load_dotenv()

DEPTH_INSTRUCTIONS = {
    "brief": "Responde de forma concisa en 2-3 oraciones.",
    "standard": "Proporciona una respuesta equilibrada de 1-2 párrafos.",
    "deep": "Realiza un análisis profundo con ejemplos y explicaciones detalladas.",
}


class Analyst:
    """Componente Analyst para análisis profundo y respuestas complejas."""

    def __init__(self, client: LLMClient = None):
        """Inicializa el Analyst sobre el adaptador de LLM."""
        self.client = client or LLMClient()
        self.model = self.client.model or "gemini-2.5-flash"

    # ------------------------------------------------------------------
    def analyze_prompt(self, prompt: str, context: str = "") -> str:
        """Analiza un prompt y proporciona análisis detallado."""
        full_prompt = f"Proporciona un análisis detallado de: {prompt}"
        if context:
            full_prompt += f"\n\nContexto: {context}"
        return self._complete(full_prompt, "Analista de seguridad de LLMs.")

    # ------------------------------------------------------------------
    def generate_detailed_response(self, question: str, depth: str = "standard", context: str = "") -> str:
        """Genera una respuesta detallada a una pregunta."""
        instruction = DEPTH_INSTRUCTIONS.get(depth, DEPTH_INSTRUCTIONS["standard"])
        prompt = f"{instruction}\n\nPregunta: {question}"
        if context:
            prompt += f"\n\nContexto recuperado (RAG):\n{context}"
        return self._complete(prompt,
                              "Analista de seguridad de LLMs.")

    # ------------------------------------------------------------------
    def identify_attack_vectors(self, scenario: str) -> str:
        """Identifica vectores de ataque potenciales (uso educativo y defensivo)."""
        prompt = f"""A fines educativos de red teaming defensivo, identifica los posibles
vectores de ataque en este escenario. Proporciona sugerencias de defensa para cada uno.

Escenario: {scenario}

Formato:
1. Vector de Ataque 1
   - Tipo: [tipo]
   - Riesgo: [nivel]
   - Defensa: [estrategia]
"""
        return self._complete(prompt, "Analista de seguridad de LLMs, con enfoque defensivo.")

    # ------------------------------------------------------------------
    def _complete(self, prompt: str, system_prompt: str) -> str:
        """Ejecuta la generación devolviendo un mensaje de error legible si falla."""
        try:
            return self.client.generate(prompt, system_prompt=system_prompt)
        except LLMProviderError as exc:
            return f"Error en análisis: {exc}"


def main():
    """Demostración del Analyst."""
    print("🔬 Inicializando Analyst...\n")

    try:
        analyst = Analyst()
        print(f"✓ Analyst activo: {analyst}\n")

        for depth in ("brief", "deep"):
            print("=" * 60)
            print(f"PRUEBA: Respuesta {depth}")
            print("=" * 60)
            print(analyst.generate_detailed_response(
                "¿Qué es el Machine Learning?", depth=depth))
            print()

        print("=" * 60)
        print("PRUEBA: Vectores de ataque (educativo)")
        print("=" * 60)
        print(analyst.identify_attack_vectors(
            "Un chatbot público que interactúa sin filtros"))

    except Exception as exc:  # pragma: no cover
        print(f"❌ Error: {exc}")


if __name__ == "__main__":
    main()