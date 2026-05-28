#!/usr/bin/env python3
"""
MCP Server: Servidor Model Context Protocol para auditoría y reportes
Proporciona herramientas para generar reportes de auditoría y análisis
"""

from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
import json
import logging
from dataclasses import asdict
from datetime import datetime

try:
    from skills.exporter import ReportExporter, Vulnerability
except ImportError:
    from src.skills.exporter import ReportExporter, Vulnerability

# Configurar logging
logger = logging.getLogger(__name__)


class ReportMCPServer:
    """
    Servidor MCP para gestión de reportes y auditorías
    Implementa herramientas reutilizables bajo el protocolo MCP
    """
    
    def __init__(self):
        """Inicializar servidor MCP"""
        self.exporter = ReportExporter()
        self.tools_registry = {}
        self._register_tools()
        
    def _register_tools(self) -> None:
        """Registrar herramientas disponibles"""
        self.tools_registry = {
            "generate_audit_report": {
                "description": "Generate a comprehensive audit report from session data",
                "handler": self._tool_generate_audit_report,
                "parameters": {
                    "session_id": "string - Unique session identifier",
                    "chat_history": "array - Chat messages with role and content",
                    "vulnerabilities": "array - Detected vulnerabilities",
                    "title": "string - Report title (optional)"
                }
            },
            "validate_session": {
                "description": "Validate session data before report generation",
                "handler": self._tool_validate_session,
                "parameters": {
                    "session_id": "string",
                    "chat_history": "array",
                    "vulnerabilities": "array"
                }
            },
            "get_report_status": {
                "description": "Get status of generated reports",
                "handler": self._tool_get_report_status,
                "parameters": {}
            }
        }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Retornar lista de herramientas disponibles en formato MCP
        
        Returns:
            Lista de herramientas con esquema MCP
        """
        tools = []
        for tool_name, tool_config in self.tools_registry.items():
            tools.append({
                "name": tool_name,
                "description": tool_config["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        param: {"type": "string", "description": desc}
                        for param, desc in tool_config.get("parameters", {}).items()
                    }
                }
            })
        return tools
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecutar una herramienta del servidor MCP
        
        Args:
            tool_name: Nombre de la herramienta
            arguments: Argumentos de la herramienta
            
        Returns:
            Resultado de la ejecución
        """
        if tool_name not in self.tools_registry:
            return {
                "status": "error",
                "message": f"Tool '{tool_name}' not found",
                "available_tools": list(self.tools_registry.keys())
            }
        
        handler = self.tools_registry[tool_name]["handler"]
        
        try:
            result = handler(**arguments)
            return {
                "status": "success",
                "data": result
            }
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    # ===== Herramientas (Tool Handlers) =====
    
    def _tool_generate_audit_report(
        self,
        session_id: str,
        chat_history: List[Dict],
        vulnerabilities: List[Dict],
        title: str = "Red Teaming Audit Report"
    ) -> Dict[str, Any]:
        """
        Herramienta MCP: Generar reporte de auditoría
        
        Args:
            session_id: ID de sesión
            chat_history: Historial de chat
            vulnerabilities: Vulnerabilidades detectadas
            title: Título del reporte
            
        Returns:
            Información del reporte generado
        """
        # Convertir vulnerabilidades de dict a objetos Vulnerability
        vuln_objects = []
        for vuln_dict in vulnerabilities:
            try:
                vuln = Vulnerability(
                    category=vuln_dict.get("category", "UNKNOWN"),
                    severity=vuln_dict.get("severity", "low"),
                    title=vuln_dict.get("title", ""),
                    description=vuln_dict.get("description", ""),
                    source=vuln_dict.get("source", "unknown"),
                    found_at=vuln_dict.get("found_at", "")
                )
                vuln_objects.append(vuln)
            except Exception as e:
                logger.warning(f"Failed to parse vulnerability: {e}")
        
        # Generar reporte
        report_path = self.exporter.generate_report(
            session_id=session_id,
            chat_history=chat_history,
            vulnerabilities=vuln_objects,
            title=title
        )
        
        if report_path:
            return {
                "success": True,
                "report_path": str(report_path),
                "size_bytes": report_path.stat().st_size,
                "vulnerabilities_count": len(vuln_objects),
                "message": f"Report generated at {report_path}"
            }
        else:
            return {
                "success": False,
                "message": "Failed to generate report"
            }
    
    def _tool_validate_session(
        self,
        session_id: str,
        chat_history: List[Dict],
        vulnerabilities: List[Dict]
    ) -> Dict[str, Any]:
        """
        Herramienta MCP: Validar datos de sesión
        
        Args:
            session_id: ID de sesión
            chat_history: Historial de chat
            vulnerabilities: Vulnerabilidades
            
        Returns:
            Resultado de validación
        """
        # Validar usando ReportExporter
        valid, error_msg = self.exporter._validate_session_data(
            session_id=session_id,
            chat_history=chat_history,
            vulnerabilities=[
                Vulnerability(
                    category=v.get("category", "UNKNOWN"),
                    severity=v.get("severity", "low"),
                    title=v.get("title", ""),
                    description=v.get("description", ""),
                    source=v.get("source", "unknown"),
                    found_at=v.get("found_at", "")
                )
                for v in vulnerabilities
            ]
        )
        
        return {
            "valid": valid,
            "error": error_msg if not valid else "",
            "session_id": session_id,
            "message_count": len(chat_history),
            "vulnerability_count": len(vulnerabilities)
        }
    
    def _tool_get_report_status(self) -> Dict[str, Any]:
        """
        Herramienta MCP: Obtener estado de reportes
        
        Returns:
            Información sobre reportes generados
        """
        reports_dir = Path("reports")
        
        if not reports_dir.exists():
            return {
                "total_reports": 0,
                "reports": []
            }
        
        reports = []
        for report_file in sorted(reports_dir.glob("pentest_report_*.md"), reverse=True):
            stat = report_file.stat()
            reports.append({
                "filename": report_file.name,
                "size_bytes": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                "path": str(report_file)
            })
        
        return {
            "total_reports": len(reports),
            "reports_directory": str(reports_dir.resolve()),
            "reports": reports[:10]  # Últimos 10
        }


class MCPToolExecutor:
    """
    Ejecutor de herramientas MCP con validación adicional
    Proporciona una interfaz consistente para llamar herramientas MCP
    """
    
    def __init__(self, server: ReportMCPServer):
        """
        Inicializar ejecutor
        
        Args:
            server: Servidor MCP
        """
        self.server = server
    
    def execute(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ejecutar herramienta con validación
        
        Args:
            tool_name: Nombre de herramienta
            arguments: Argumentos
            
        Returns:
            Resultado de ejecución
        """
        # Log de ejecución
        logger.info(f"Executing MCP tool: {tool_name}")
        
        # Ejecutar herramienta
        result = self.server.call_tool(tool_name, arguments)
        
        # Log de resultado
        if result.get("status") == "success":
            logger.info(f"Tool {tool_name} executed successfully")
        else:
            logger.error(f"Tool {tool_name} failed: {result.get('message')}")
        
        return result
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Listar herramientas disponibles
        
        Returns:
            Lista de herramientas con esquema
        """
        return self.server.get_tools()
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtener información detallada de una herramienta
        
        Args:
            tool_name: Nombre de herramienta
            
        Returns:
            Información de la herramienta o None
        """
        tools = self.server.get_tools()
        for tool in tools:
            if tool["name"] == tool_name:
                return tool
        return None
