#!/usr/bin/env python3
"""
Script de prueba para verificar la configuración del proyecto
"""

import sys
from pathlib import Path

# Colores para output
GREEN = '\033[92m'
RED = '\033[91m'
RESET = '\033[0m'


def test_python_version():
    """Verifica que Python 3.11+ esté instalado"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 11:
        print(f"{GREEN}✓{RESET} Python {version.major}.{version.minor}.{version.micro}")
        return True
    print(f"{RED}✗{RESET} Se requiere Python 3.11+, tienes {version.major}.{version.minor}")
    return False


def test_imports():
    """Verifica que los módulos principales se pueden importar"""
    modules = [
        ("python-dotenv", "dotenv"),
        ("requests", "requests"),
        ("google.generativeai", "google.generativeai"),
    ]
    
    all_ok = True
    for package, module in modules:
        try:
            __import__(module)
            print(f"{GREEN}✓{RESET} {package}")
        except ImportError:
            print(f"{RED}✗{RESET} {package} - no instalado")
            all_ok = False
    
    return all_ok


def test_env_file():
    """Verifica que el archivo .env existe"""
    env_file = Path(".env")
    if env_file.exists():
        print(f"{GREEN}✓{RESET} Archivo .env existe")
        return True
    print(f"{RED}✗{RESET} Archivo .env no encontrado")
    return False


def test_structure():
    """Verifica que la estructura de carpetas existe"""
    required_dirs = ["src", "docs", "tests", "data", "reports", "logs"]
    all_ok = True
    
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"{GREEN}✓{RESET} Carpeta: {dir_name}/")
        else:
            print(f"{RED}✗{RESET} Carpeta faltante: {dir_name}/")
            all_ok = False
    
    return all_ok


def main():
    print("\n" + "="*50)
    print("VERIFICACIÓN DE CONFIGURACIÓN DEL PROYECTO")
    print("="*50 + "\n")
    
    results = {
        "Python Version": test_python_version(),
        "Estructura": test_structure(),
        "Archivo .env": test_env_file(),
        "Dependencias": test_imports(),
    }
    
    print("\n" + "="*50)
    print("RESUMEN")
    print("="*50)
    
    all_passed = all(results.values())
    for test, passed in results.items():
        status = f"{GREEN}PASS{RESET}" if passed else f"{RED}FAIL{RESET}"
        print(f"{test}: {status}")
    
    print("="*50)
    
    if all_passed:
        print(f"\n{GREEN}¡Entorno configurado correctamente!{RESET}")
        print("\nPróximos pasos:")
        print("1. Agregar tu API Key de Gemini en el archivo .env")
        print("   GEMINI_API_KEY=tu_clave_aqui")
        print("2. Comenzar el desarrollo en src/")
        return 0
    else:
        print(f"\n{RED}Hay problemas en la configuración.{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
