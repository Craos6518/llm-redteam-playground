#!/usr/bin/env python3
"""
Skill: Exportador de Reportes de Auditoría
Genera reportes MD estructurados con hallazgos, análisis y evidencia
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import hashlib


@dataclass
class Vulnerability:
    """Representación de una vulnerabilidad encontrada"""
    category: str  # OWASP LLM01, LLM02, etc.
    severity: str  # "low", "medium", "high", "critical"
    title: str
    description: str
    source: str  # Archivo fuente del corpus
    found_at: str  # Timestamp o índice en historial


class ReportExporter:
    """Exportador de reportes de auditoría con validaciones de seguridad"""
    
    # Categorías OWASP válidas
    VALID_OWASP_CATEGORIES = {
        "LLM01": "Prompt Injection",
        "LLM02": "Insecure Output Handling",
        "LLM03": "Training Data Poisoning",
        "LLM04": "Model DoS",
        "LLM05": "Supply Chain Vulnerabilities",
        "LLM06": "Sensitive Information Disclosure",
        "LLM07": "Insecure Plugin Integration",
        "LLM08": "Excessive Agency",
        "LLM09": "Overreliance on LLM-generated Content",
        "LLM10": "Model Theft",
    }
    
    VALID_SEVERITIES = {"low", "medium", "high", "critical"}
    MAX_REPORT_SIZE = 5 * 1024 * 1024  # 5 MB
    REPORTS_DIR = Path("reports")
    
    def __init__(self):
        """Inicializar exportador"""
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitizar nombre de archivo para prevenir path traversal
        
        Args:
            filename: Nombre original
            
        Returns:
            Nombre sanitizado
        """
        # Remover caracteres peligrosos
        sanitized = re.sub(r'[^\w\s\-_.]', '', filename)
        # Remover ../ y ./
        sanitized = re.sub(r'[./\\]+', '', sanitized)
        # Limitar longitud
        sanitized = sanitized[:50]
        return sanitized or "report"
    
    def _validate_vulnerability(self, vuln: Vulnerability) -> bool:
        """
        Validar estructura de vulnerabilidad
        
        Args:
            vuln: Objeto Vulnerability a validar
            
        Returns:
            True si es válido
        """
        if not isinstance(vuln, Vulnerability):
            return False
        
        if vuln.category not in self.VALID_OWASP_CATEGORIES and \
           not vuln.category.startswith("LLM"):
            return False
        
        if vuln.severity not in self.VALID_SEVERITIES:
            return False
        
        if not (0 < len(vuln.title) <= 200):
            return False
        
        if not (0 < len(vuln.description) <= 5000):
            return False
        
        return True
    
    def _validate_session_data(
        self,
        session_id: str,
        chat_history: List[Dict],
        vulnerabilities: List[Vulnerability]
    ) -> Tuple[bool, str]:
        """
        Validar datos de sesión
        
        Args:
            session_id: ID de sesión
            chat_history: Historial de chat
            vulnerabilities: Lista de vulnerabilidades
            
        Returns:
            Tupla (válido, mensaje_error)
        """
        # Validar session_id
        if not re.match(r'^[a-zA-Z0-9\-_]{1,50}$', session_id):
            return False, "Invalid session_id format"
        
        # Validar chat_history
        if not isinstance(chat_history, list):
            return False, "chat_history must be a list"
        
        if len(chat_history) > 1000:
            return False, "chat_history too long (max 1000 messages)"
        
        for msg in chat_history:
            if not isinstance(msg, dict):
                return False, "Each message must be a dict"
            if "role" not in msg or "content" not in msg:
                return False, "Each message must have 'role' and 'content'"
            if len(msg.get("content", "")) > 10000:
                return False, "Message content too long"
        
        # Validar vulnerabilidades
        if not isinstance(vulnerabilities, list):
            return False, "vulnerabilities must be a list"
        
        for vuln in vulnerabilities:
            if not self._validate_vulnerability(vuln):
                return False, f"Invalid vulnerability: {vuln}"
        
        return True, ""
    
    def _estimate_size(
        self,
        session_id: str,
        chat_history: List[Dict],
        vulnerabilities: List[Vulnerability]
    ) -> int:
        """
        Estimar tamaño del reporte antes de generarlo
        
        Args:
            session_id: ID de sesión
            chat_history: Historial de chat
            vulnerabilities: Lista de vulnerabilidades
            
        Returns:
            Tamaño estimado en bytes
        """
        size = len(str(session_id))
        
        for msg in chat_history:
            size += len(msg.get("content", "")) + 100  # Overhead
        
        for vuln in vulnerabilities:
            size += len(vuln.title) + len(vuln.description) + 200
        
        return size + 2000  # Overhead de estructura MD
    
    def generate_report(
        self,
        session_id: str,
        chat_history: List[Dict],
        vulnerabilities: List[Vulnerability],
        title: str = "Red Teaming Audit Report"
    ) -> Optional[Path]:
        """
        Generar reporte MD estructurado
        
        Args:
            session_id: ID único de sesión
            chat_history: Lista de mensajes del chat
            vulnerabilities: Lista de vulnerabilidades encontradas
            title: Título del reporte
            
        Returns:
            Path al archivo generado, o None si falla
        """
        # Validar entrada
        valid, error_msg = self._validate_session_data(
            session_id, chat_history, vulnerabilities
        )
        if not valid:
            print(f"❌ Validación fallida: {error_msg}")
            return None
        
        # Estimar tamaño
        estimated_size = self._estimate_size(session_id, chat_history, vulnerabilities)
        if estimated_size > self.MAX_REPORT_SIZE:
            print(f"❌ Reporte demasiado grande: {estimated_size} bytes")
            return None
        
        # Generar nombre de archivo seguro
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pentest_report_{self._sanitize_filename(session_id)}_{timestamp}.md"
        report_path = self.REPORTS_DIR / filename
        
        # Construir contenido del reporte
        content = self._build_report_content(
            session_id, chat_history, vulnerabilities, title
        )
        
        # Escribir archivo
        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            print(f"✅ Reporte generado: {report_path}")
            print(f"📊 Tamaño: {len(content)} bytes")
            return report_path
        
        except Exception as e:
            print(f"❌ Error escribiendo reporte: {e}")
            return None
    
    def _build_report_content(
        self,
        session_id: str,
        chat_history: List[Dict],
        vulnerabilities: List[Vulnerability],
        title: str
    ) -> str:
        """
        Construir contenido MD del reporte
        
        Args:
            session_id: ID de sesión
            chat_history: Historial de chat
            vulnerabilities: Vulnerabilidades
            title: Título del reporte
            
        Returns:
            Contenido MD completo
        """
        lines = []
        
        # Portada
        lines.append(f"# {title}")
        lines.append("")
        lines.append(f"**Session ID:** `{session_id}`")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")
        
        # Tabla de contenidos
        lines.append("## Table of Contents")
        lines.append("1. [Executive Summary](#executive-summary)")
        lines.append("2. [Findings by Category](#findings-by-category)")
        lines.append("3. [Severity Distribution](#severity-distribution)")
        lines.append("4. [Chat History](#chat-history)")
        lines.append("5. [Recommendations](#recommendations)")
        lines.append("")
        
        # Resumen ejecutivo
        lines.append("## Executive Summary")
        lines.append("")
        critical = sum(1 for v in vulnerabilities if v.severity == "critical")
        high = sum(1 for v in vulnerabilities if v.severity == "high")
        medium = sum(1 for v in vulnerabilities if v.severity == "medium")
        low = sum(1 for v in vulnerabilities if v.severity == "low")
        
        lines.append(f"**Total Vulnerabilities Found:** {len(vulnerabilities)}")
        lines.append("")
        lines.append("| Severity | Count |")
        lines.append("|----------|-------|")
        lines.append(f"| 🔴 Critical | {critical} |")
        lines.append(f"| 🟠 High | {high} |")
        lines.append(f"| 🟡 Medium | {medium} |")
        lines.append(f"| 🟢 Low | {low} |")
        lines.append("")
        
        if vulnerabilities:
            lines.append(f"**Session Duration:** {len(chat_history)} interactions")
            lines.append("")
            lines.append("### Risk Assessment")
            if critical > 0:
                lines.append("⚠️ **CRITICAL FINDINGS DETECTED** - Immediate action required")
            elif high > 0:
                lines.append("⚠️ **HIGH-RISK FINDINGS** - Prioritize remediation")
            elif medium > 0:
                lines.append("ℹ️ **Medium-risk findings detected** - Plan mitigation")
            else:
                lines.append("✅ No critical or high-severity vulnerabilities found")
        
        lines.append("")
        
        # Hallazgos por categoría OWASP
        lines.append("## Findings by Category")
        lines.append("")
        
        # Agrupar por categoría
        by_category = {}
        for vuln in vulnerabilities:
            if vuln.category not in by_category:
                by_category[vuln.category] = []
            by_category[vuln.category].append(vuln)
        
        # Ordenar categorías
        sorted_categories = sorted(by_category.keys())
        
        for category in sorted_categories:
            category_vulns = by_category[category]
            category_name = self.VALID_OWASP_CATEGORIES.get(category, category)
            
            lines.append(f"### {category}: {category_name}")
            lines.append("")
            lines.append(f"**Count:** {len(category_vulns)}")
            lines.append("")
            
            for i, vuln in enumerate(category_vulns, 1):
                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢"
                }.get(vuln.severity, "⚪")
                
                lines.append(f"#### Finding {category}-{i}")
                lines.append("")
                lines.append(f"**Title:** {vuln.title}")
                lines.append(f"**Severity:** {severity_emoji} {vuln.severity.upper()}")
                lines.append(f"**Source:** `{vuln.source}`")
                lines.append(f"**Detected at:** {vuln.found_at}")
                lines.append("")
                lines.append(f"**Description:**")
                lines.append("")
                # Indentar descripción
                for line in vuln.description.split('\n'):
                    lines.append(f"> {line}")
                lines.append("")
        
        # Distribución de severidad
        lines.append("## Severity Distribution")
        lines.append("")
        lines.append("```")
        lines.append(f"Critical: {'█' * critical}  ({critical})")
        lines.append(f"High:     {'█' * high}  ({high})")
        lines.append(f"Medium:   {'█' * medium}  ({medium})")
        lines.append(f"Low:      {'█' * low}  ({low})")
        lines.append("```")
        lines.append("")
        
        # Historial de chat (resumen)
        lines.append("## Chat History")
        lines.append("")
        lines.append(f"**Total Messages:** {len(chat_history)}")
        lines.append("")
        
        # Mostrar primeros y últimos mensajes como muestra
        if chat_history:
            lines.append("### First 3 Interactions")
            for i, msg in enumerate(chat_history[:3], 1):
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")[:200]  # Truncar
                lines.append(f"**{i}. [{role}]** {content}...")
                lines.append("")
            
            if len(chat_history) > 6:
                lines.append("_(... {} messages omitted ...)_".format(len(chat_history) - 6))
                lines.append("")
            
            if len(chat_history) > 3:
                lines.append("### Last 3 Interactions")
                for i, msg in enumerate(chat_history[-3:], len(chat_history) - 2):
                    role = msg.get("role", "unknown").upper()
                    content = msg.get("content", "")[:200]  # Truncar
                    lines.append(f"**{i}. [{role}]** {content}...")
                    lines.append("")
        
        # Recomendaciones
        lines.append("## Recommendations")
        lines.append("")
        
        if vulnerabilities:
            lines.append("### Immediate Actions (if Critical/High)")
            lines.append("")
            if critical > 0 or high > 0:
                lines.append("1. **Review System Prompts:** Ensure strict guardrails are in place")
                lines.append("2. **Input Validation:** Implement robust input sanitization")
                lines.append("3. **Output Filtering:** Add detection for sensitive information leakage")
                lines.append("4. **Rate Limiting:** Apply rate limits to prevent DoS attempts")
                lines.append("")
            
            lines.append("### General Recommendations")
            lines.append("")
            lines.append("- Conduct regular red teaming sessions")
            lines.append("- Implement continuous monitoring and logging")
            lines.append("- Train teams on LLM security best practices")
            lines.append("- Keep the LLM model and dependencies updated")
            lines.append("- Consider using ensemble approaches for critical decisions")
        
        lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*Report generated by LLM Red Teaming Playground*")
        lines.append(f"*Hash: {hashlib.md5(str(session_id).encode()).hexdigest()[:16]}*")
        
        return "\n".join(lines)


# Función de conveniencia
def generate_report(
    session_id: str,
    chat_history: List[Dict],
    vulnerabilities: List[Vulnerability],
    title: str = "Red Teaming Audit Report"
) -> Optional[Path]:
    """
    Función de conveniencia para generar reportes
    
    Args:
        session_id: ID único de sesión
        chat_history: Lista de mensajes del chat
        vulnerabilities: Lista de vulnerabilidades
        title: Título del reporte
        
    Returns:
        Path al archivo generado
    """
    exporter = ReportExporter()
    return exporter.generate_report(session_id, chat_history, vulnerabilities, title)
