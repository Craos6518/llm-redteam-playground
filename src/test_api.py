#!/usr/bin/env python3
"""
Ejemplo de uso de la API de Google Gemini
Este script demuestra cómo configurar y usar la API
"""

import os
from pathlib import Path

# Verificar que estamos en el directorio correcto
if not Path('.env').exists():
    print("❌ Error: No se encuentra el archivo .env")
    print("   Crea el archivo .env con tu API Key")
    exit(1)

try:
    from dotenv import load_dotenv
    from google import genai
except ImportError as e:
    print(f"❌ Error al importar dependencias: {e}")
    print("   Ejecuta: pip install -r requirements.txt")
    exit(1)

# Cargar variables de entorno
load_dotenv()

# Obtener API Key
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("❌ Error: GEMINI_API_KEY no está configurada en .env")
    exit(1)

# Obtener modelo de configuración
model_name = os.getenv('GUARDIAN_MODEL', 'gemini-2.5-flash')

# Configurar el cliente
print("🔧 Configurando cliente de Gemini...")
client = genai.Client(api_key=api_key)

print(f"📦 Usando modelo: {model_name}")

# Hacer una prueba simple
print("\n" + "="*50)
print("PRUEBA DE API")
print("="*50 + "\n")

try:
    print("📝 Enviando mensaje de prueba...")
    response = client.models.generate_content(
        model=model_name,
        contents="Hola, ¿cuál es tu nombre? Responde brevemente."
    )
    
    print(f"\n✅ Respuesta de la API:\n")
    print(response.text)
    print("\n" + "="*50)
    print("✓ ¡API configurada correctamente!")
    print("="*50 + "\n")
    
except Exception as e:
    print(f"\n❌ Error al llamar la API: {e}")
    print("\n   Posibles causas:")
    print("   - API Key inválida o expirada")
    print("   - Problema de conectividad")
    print("   - Límite de cuota alcanzado")
    exit(1)
