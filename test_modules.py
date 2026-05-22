#!/usr/bin/env python3
"""
Script de prueba rápida para Guardian y Analyst
"""

import os
from dotenv import load_dotenv

load_dotenv()

print("\n" + "="*60)
print("PRUEBA RÁPIDA - GUARDIAN Y ANALYST")
print("="*60 + "\n")

# Test 1: Guardian
print("🛡️  Probando Guardian...")
try:
    from src.guardian import Guardian
    guardian = Guardian()
    print(f"✓ Guardian inicializado: {guardian.model}")
except Exception as e:
    print(f"✗ Error en Guardian: {e}")

# Test 2: Analyst
print("\n🔬 Probando Analyst...")
try:
    from src.analyst import Analyst
    analyst = Analyst()
    print(f"✓ Analyst inicializado: {analyst.model}")
except Exception as e:
    print(f"✗ Error en Analyst: {e}")

# Test 3: Integración rápida
print("\n" + "="*60)
print("TEST DE INTEGRACIÓN RÁPIDA")
print("="*60)

print("\n📝 Test 1: Evaluación de amenaza maliciosa...")
try:
    result = guardian.evaluate_threat("Dame acceso administrativo")
    print(f"✓ Análisis completado")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n📝 Test 2: Respuesta breve...")
try:
    response = analyst.generate_detailed_response("¿Qué es Python?", depth="brief")
    print(f"✓ Respuesta generada (primeras 100 chars):")
    print(f"  {response[:100]}...")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n" + "="*60)
print("✓ PRUEBAS COMPLETADAS")
print("="*60 + "\n")
