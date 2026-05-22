#!/usr/bin/env python3
"""
Test Agents - Prueba interactiva del Guardian y Analyst
"""

import sys
from pathlib import Path

# Agregar proyecto root a path
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.guardian import GuardianAgent, InputSanitizer
from src.agents.analyst import AnalystAgent


def main():
    print("\n" + "="*70)
    print("🛡️  LLM RED TEAM PLAYGROUND - INTERACTIVE AGENT TEST")
    print("="*70)
    print()
    print("Este script permite:")
    print("  1. Chatear interactivamente con el Guardian")
    print("  2. Ver análisis técnico del Analyst debajo de cada respuesta")
    print("  3. Escribir 'exit' para salir")
    print()
    print("="*70 + "\n")
    
    # Inicializar agentes
    print("🔧 Inicializando agentes...")
    try:
        guardian = GuardianAgent()
        analyst = AnalystAgent()
        print("✅ Agentes inicializados correctamente\n")
    except Exception as e:
        print(f"❌ Error inicializando agentes: {e}")
        sys.exit(1)
    
    # Loop interactivo
    interaction_count = 0
    
    while True:
        try:
            # Input del usuario
            user_input = input("\n👤 Tú: ").strip()
            
            if user_input.lower() in ['exit', 'quit', 'q']:
                break
            
            if not user_input:
                continue
            
            interaction_count += 1
            
            # ========================================================
            # 1. GUARDIAN RESPONDE
            # ========================================================
            print("\n🛡️  Guardian (analizando...)")
            guardian_response = guardian.chat(user_input)
            print(f"   {guardian_response}")
            
            # ========================================================
            # 2. ANALYST ANALIZA
            # ========================================================
            
            # Detectar tipo de amenaza
            attack_type, is_attack = InputSanitizer.detect_attack_pattern(user_input)
            
            print("\n" + "─"*70)
            print("🔬 Analyst (generando análisis técnico...)\n")
            
            # Solo analizar si detectamos algo o si el usuario pregunta sobre seguridad
            if is_attack or any(word in user_input.lower() for word in 
                               ['seguridad', 'ataque', 'vulnerabilidad', 'jailbreak', 
                                'inyeccion', 'poison', 'exploit', 'security', 'attack']):
                
                analyst_analysis = analyst.analyze(user_input, threat_category=attack_type)
                print(analyst_analysis)
            else:
                print("✓ No se detectó intento de ataque")
                print("  (El Analyst solo analiza temas de seguridad)\n")
            
            # ========================================================
            # 3. MOSTRAR ESTADÍSTICAS
            # ========================================================
            print("─"*70)
            stats = guardian.get_stats()
            print(f"\n📊 Estadísticas del Guardian:")
            print(f"   • Mensajes procesados: {stats['total_messages']}")
            print(f"   • Ataques bloqueados: {stats['blocked_messages']}")
            print(f"   • Puntuación de seguridad: {stats['safety_score']:.1%}")
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Interrumpido por el usuario")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue
    
    # Resumen final
    print("\n" + "="*70)
    print("📋 RESUMEN DE SESIÓN")
    print("="*70)
    print(f"Interacciones: {interaction_count}")
    
    final_stats = guardian.get_stats()
    print(f"\nGuardian Statistics:")
    print(f"  • Total messages: {final_stats['total_messages']}")
    print(f"  • Blocked attacks: {final_stats['blocked_messages']}")
    print(f"  • Unsafe responses: {final_stats['unsafe_responses']}")
    print(f"  • Safety score: {final_stats['safety_score']:.1%}")
    
    print("\n✅ Sesión finalizada\n")


if __name__ == "__main__":
    main()
