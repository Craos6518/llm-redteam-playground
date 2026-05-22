#!/usr/bin/env python3
"""
Analyst Agent - Análisis Técnico de Ataques a LLMs
Proporciona análisis educativo sobre intentos de ataque
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

# Agregar proyecto root a path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from google import genai
from src.config import GEMINI_API_KEY, ANALYST_MODEL, get_analyst_prompt
from src.rag.retriever import RAGRetriever


class AnalystAgent:
    """Agente Analyst - Análisis técnico de ataques"""
    
    # Mapeo de amenazas a categorías OWASP
    THREAT_TO_OWASP = {
        "prompt_injection": "LLM01:2025 – Prompt Injection",
        "jailbreak": "LLM02:2025 – Insecure Output Handling",
        "data_poisoning": "LLM04:2025 – Data and Model Poisoning",
        "leakage": "LLM07:2025 – System Prompt Leakage",
        "excessive_agency": "LLM06:2025 – Excessive Agency",
    }
    
    def __init__(self):
        """Inicializar el Analyst"""
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = ANALYST_MODEL
        self.system_prompt = get_analyst_prompt()
        
        # Retriever para obtener contexto del corpus
        try:
            self.retriever = RAGRetriever()
        except Exception as e:
            print(f"⚠️  No se pudo inicializar retriever: {e}")
            self.retriever = None
    
    def analyze(self, user_message: str, threat_category: str = "unknown") -> str:
        """
        Analizar un intento de ataque
        
        Args:
            user_message: Mensaje/intento de ataque a analizar
            threat_category: Categoría de amenaza detectada
            
        Returns:
            Análisis técnico detallado
        """
        # 1. RECUPERAR CONTEXTO DEL CORPUS
        context_chunks = []
        if self.retriever:
            try:
                rag_results = self.retriever.retrieve(user_message, top_k=3)
                context_chunks = rag_results
            except Exception as e:
                print(f"⚠️  Error en retrieval: {e}")
        
        # 2. CONSTRUIR PROMPT CON CONTEXTO
        analysis_prompt = self._build_analysis_prompt(
            user_message=user_message,
            threat_category=threat_category,
            context_chunks=context_chunks
        )
        
        # 3. GENERAR ANÁLISIS
        try:
            full_prompt = f"{self.system_prompt}\n\n{analysis_prompt}"
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            analysis = response.text
        except Exception as e:
            return f"❌ Error generando análisis: {e}"
        
        # 4. FORMATEAR OUTPUT
        formatted_output = self._format_analysis(
            analysis=analysis,
            threat_category=threat_category,
            sources=[chunk.get("source", "unknown") for chunk in context_chunks]
        )
        
        return formatted_output
    
    def _build_analysis_prompt(
        self,
        user_message: str,
        threat_category: str,
        context_chunks: List[Dict]
    ) -> str:
        """Construir prompt para análisis con contexto"""
        
        owasp_ref = self.THREAT_TO_OWASP.get(threat_category, "Categoría OWASP desconocida")
        
        # Base del prompt
        prompt = f"""SOLICITUD DE ANÁLISIS DE SEGURIDAD

Intento de Ataque:
"{user_message}"

Categoría Detectada: {threat_category}
Referencia OWASP: {owasp_ref}

"""
        
        # Agregar contexto del corpus si disponible
        if context_chunks:
            prompt += "CONTEXTO DEL CORPUS:\n"
            for i, chunk in enumerate(context_chunks, 1):
                source = chunk.get("source", "unknown")
                score = chunk.get("score", 0)
                content = chunk.get("content", "")[:300]
                prompt += f"\n{i}. Fuente: {source} (Relevancia: {score:.1%})\n"
                prompt += f"   {content}...\n"
        
        # Instrucciones de análisis
        prompt += """

POR FAVOR PROPORCIONA:

1. **TIPO DE ATAQUE**: Clasifica específicamente el ataque
2. **CATEGORÍA OWASP**: Mapea exactamente a OWASP LLM (LLM01-LLM09)
3. **MECANISMO**: Cómo funciona este ataque
4. **RIESGO**: Por qué es peligroso
5. **DEFENSA**: Técnicas de mitigación específicas
6. **REFERENCIA**: Cita los archivos fuente del corpus utilisados

Mantén un tono educativo y profesional."""
        
        return prompt
    
    def _format_analysis(
        self,
        analysis: str,
        threat_category: str,
        sources: List[str]
    ) -> str:
        """Formatear análisis con metadata"""
        
        owasp_ref = self.THREAT_TO_OWASP.get(threat_category, "Unknown")
        
        output = f"""
╔════════════════════════════════════════════════════════════╗
║              📊 ANÁLISIS TÉCNICO DE ATAQUE                ║
╚════════════════════════════════════════════════════════════╝

🎯 CATEGORÍA: {threat_category.upper()}
📋 OWASP: {owasp_ref}

{analysis}

═════════════════════════════════════════════════════════════
📚 FUENTES DEL CORPUS:
"""
        
        for source in set(sources):
            output += f"  • {source}\n"
        
        output += "═════════════════════════════════════════════════════════════\n"
        
        return output
    
    def batch_analyze(self, messages: List[str]) -> List[str]:
        """Analizar múltiples mensajes"""
        results = []
        for msg in messages:
            result = self.analyze(msg)
            results.append(result)
        return results


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔬 ANALYST AGENT - TEST")
    print("="*60 + "\n")
    
    analyst = AnalystAgent()
    
    # Test attacks
    test_attacks = [
        ("ignora todas las instrucciones", "prompt_injection"),
        ("explica jailbreak", "jailbreak"),
        ("envenenamiento de datos", "data_poisoning"),
    ]
    
    for attack, threat in test_attacks:
        print(f"\n📝 Analizando: {attack}\n")
        analysis = analyst.analyze(attack, threat_category=threat)
        print(analysis)
        print()
