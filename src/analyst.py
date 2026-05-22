#!/usr/bin/env python3
"""
Analyst Module - Análisis profundo y generación de respuestas complejas
Responsable de generar respuestas detalladas y realizar análisis exhaustivos
"""

import os
from dotenv import load_dotenv
from google import genai

# Cargar variables de entorno
load_dotenv()

class Analyst:
    """
    Componente Analyst para análisis profundo y respuestas complejas
    """
    
    def __init__(self):
        """Inicializar el Analyst con la API de Gemini"""
        api_key = os.getenv('GEMINI_API_KEY')
        model_name = os.getenv('ANALYST_MODEL', 'gemini-2.5-flash')
        
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada en .env")
        
        self.client = genai.Client(api_key=api_key)
        self.model = model_name
        
    def analyze_prompt(self, prompt: str, context: str = "") -> str:
        """
        Analizar un prompt y proporcionar análisis detallado
        
        Args:
            prompt: Texto a analizar
            context: Contexto adicional (opcional)
            
        Returns:
            Análisis detallado
        """
        full_prompt = f"Proporciona un análisis detallado de: {prompt}"
        if context:
            full_prompt += f"\n\nContexto: {context}"
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            return response.text
        except Exception as e:
            return f"Error en análisis: {str(e)}"
    
    def generate_detailed_response(self, question: str, depth: str = "standard") -> str:
        """
        Generar una respuesta detallada a una pregunta
        
        Args:
            question: Pregunta a responder
            depth: "brief", "standard", o "deep"
            
        Returns:
            Respuesta detallada
        """
        depth_instructions = {
            "brief": "Responde de forma concisa en 2-3 oraciones.",
            "standard": "Proporciona una respuesta equilibrada de 1-2 párrafos.",
            "deep": "Realiza un análisis profundo con ejemplos y explicaciones detalladas."
        }
        
        instruction = depth_instructions.get(depth, depth_instructions["standard"])
        full_prompt = f"{instruction}\n\nPregunta: {question}"
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=full_prompt
            )
            return response.text
        except Exception as e:
            return f"Error generando respuesta: {str(e)}"
    
    def identify_attack_vectors(self, scenario: str) -> str:
        """
        Identificar vectores de ataque potenciales en un escenario
        (Para propósitos educativos y de red teaming defensivo)
        
        Args:
            scenario: Descripción del escenario a analizar
            
        Returns:
            Análisis de vectores de ataque potenciales
        """
        prompt = f"""Con fines educativos de red teaming defensivo, identifica los posibles 
vectores de ataque en este escenario. Proporciona sugerencias de defensa para cada uno.

Escenario: {scenario}

Formato:
1. Vector de Ataque 1
   - Tipo: [tipo]
   - Riesgo: [nivel]
   - Defensa: [estrategia]
"""
        
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text
        except Exception as e:
            return f"Error en análisis: {str(e)}"


def main():
    """Demostración del Analyst"""
    print("🔬 Inicializando Analyst...\n")
    
    try:
        analyst = Analyst()
        print(f"✓ Analyst activo con modelo: {analyst.model}\n")
        
        # Ejemplo 1: Respuesta breve
        print("=" * 60)
        print("PRUEBA 1: Respuesta Breve")
        print("=" * 60)
        question = "¿Qué es el Machine Learning?"
        result = analyst.generate_detailed_response(question, depth="brief")
        print(f"\nPregunta: {question}")
        print(f"\nRespuesta:\n{result}\n")
        
        # Ejemplo 2: Respuesta detallada
        print("=" * 60)
        print("PRUEBA 2: Respuesta Profunda")
        print("=" * 60)
        question = "¿Cuáles son los desafíos principales del IA?"
        result = analyst.generate_detailed_response(question, depth="deep")
        print(f"\nPregunta: {question}")
        print(f"\nRespuesta:\n{result}\n")
        
        # Ejemplo 3: Análisis de vectores de ataque
        print("=" * 60)
        print("PRUEBA 3: Análisis de Vectores de Ataque (Educativo)")
        print("=" * 60)
        scenario = "Un chatbot público que interactúa sin filtros"
        result = analyst.identify_attack_vectors(scenario)
        print(f"\nEscenario: {scenario}")
        print(f"\nAnálisis:\n{result}\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
