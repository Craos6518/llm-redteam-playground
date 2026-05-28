#!/usr/bin/env python3
"""
LLM Red Teaming Playground - Interfaz Principal con Streamlit
Integra Guardian, Analyst, RAG y el servidor MCP para exportación de reportes
"""

import sys
from pathlib import Path

# Agregar src al path para imports (necesario cuando Streamlit ejecuta como script principal)
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from datetime import datetime
from typing import List, Dict, Optional
import json

# Importar componentes (ahora sin prefijo src. porque ya está en sys.path)
from guardian import Guardian
from analyst import Analyst
from rag.retriever import RAGRetriever
from skills.exporter import Vulnerability
from mcp.report_server import ReportMCPServer, MCPToolExecutor

# Para RedTeamingSessionManager, agregar parent directory
sys.path.insert(0, str(Path(__file__).parent.parent))
from integration_example import RedTeamingSessionManager


# Configuración de la página
st.set_page_config(
    page_title="LLM Red Teaming Playground",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados - SOC dark mode
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(180deg, #1e1e1e 0%, #171717 100%);
        color: #e6e6e6;
    }

    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    section[data-testid="stSidebar"] {
        background: #232323;
        border-right: 1px solid #353535;
    }

    section[data-testid="stSidebar"] * {
        color: #e6e6e6;
    }

    .soc-card {
        background: #2d2d2d;
        border: 1px solid #444;
        border-radius: 12px;
        padding: 1rem 1.1rem;
        margin: 0.75rem 0;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
    }

    .soc-card h4 {
        margin: 0 0 0.65rem 0;
        font-size: 0.9rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #f1f1f1;
    }

    .soc-card blockquote {
        margin: 0;
        padding-left: 1rem;
        border-left: 3px solid #6b6b6b;
        color: #d2d2d2;
    }

    .stMetric {
        background: #2d2d2d;
        border: 1px solid #444;
        border-radius: 12px;
        padding: 0.85rem 1rem;
    }

    .stMetric [data-testid="stMetricLabel"] {
        color: #cfcfcf;
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .stMetric [data-testid="stMetricValue"] {
        color: #ffffff;
        font-size: 1.7rem;
        font-weight: 700;
        line-height: 1.1;
    }

    .stMetric [data-testid="stMetricDelta"] {
        color: #a8a8a8;
    }

    .stButton > button {
        width: 100%;
        background: #2d2d2d;
        color: #f2f2f2;
        border: 1px solid #6d2a2a;
        border-radius: 10px;
        padding: 0.65rem 1rem;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        background: #382020;
        border-color: #c23b3b;
        color: #ffffff;
    }

    .stChatInput > div {
        background: #2d2d2d;
        border-top: 1px solid #444;
    }

    .stCode {
        border: 1px solid #444;
        border-radius: 12px;
    }

    :root {
        --primary: #1e3c72;
        --secondary: #2a5298;
        --success: #2e7d32;
        --warning: #f57c00;
        --danger: #c62828;
        --dark: #0f0f23;
        --light: #eceff1;
    }

</style>
""", unsafe_allow_html=True)


# Inicializar session_state
def init_session_state():
    """Inicializar todas las variables de session_state"""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    
    if 'analyst_reports' not in st.session_state:
        st.session_state.analyst_reports = []
    
    if 'vulnerabilities' not in st.session_state:
        st.session_state.vulnerabilities = []
    
    if 'attempt_count' not in st.session_state:
        st.session_state.attempt_count = 0
    
    if 'threat_detections' not in st.session_state:
        st.session_state.threat_detections = []
    
    if 'session_manager' not in st.session_state:
        st.session_state.session_manager = RedTeamingSessionManager(
            st.session_state.session_id
        )
    
    # Inicializar componentes una sola vez
    if 'guardian' not in st.session_state:
        try:
            st.session_state.guardian = Guardian()
        except Exception as e:
            st.error(f"Error inicializando Guardian: {e}")
            st.session_state.guardian = None
    
    if 'analyst' not in st.session_state:
        try:
            st.session_state.analyst = Analyst()
        except Exception as e:
            st.error(f"Error inicializando Analyst: {e}")
            st.session_state.analyst = None
    
    if 'rag_retriever' not in st.session_state:
        try:
            st.session_state.rag_retriever = RAGRetriever()
        except Exception as e:
            st.warning(f"RAG no disponible: {e}")
            st.session_state.rag_retriever = None
    
    if 'mcp_executor' not in st.session_state:
        try:
            mcp_server = ReportMCPServer()
            st.session_state.mcp_executor = MCPToolExecutor(mcp_server)
        except Exception as e:
            st.error(f"Error inicializando MCP: {e}")
            st.session_state.mcp_executor = None


def severity_to_score(severity: Optional[str]) -> float:
    """Convertir severidad textual a una escala numérica para métricas UI."""
    mapping = {
        "critical": 4.0,
        "high": 3.0,
        "medium": 2.0,
        "low": 1.0,
    }
    return mapping.get((severity or "low").lower(), 1.0)


def average_severity_label() -> str:
    """Calcular una etiqueta legible para la severidad promedio."""
    if not st.session_state.vulnerabilities:
        return "N/A"

    scores = [severity_to_score(vuln.severity) for vuln in st.session_state.vulnerabilities]
    average_score = sum(scores) / len(scores)

    if average_score >= 3.5:
        label = "CRITICAL"
    elif average_score >= 2.5:
        label = "HIGH"
    elif average_score >= 1.5:
        label = "MEDIUM"
    else:
        label = "LOW"

    return f"{label} ({average_score:.1f}/4)"


def extract_threat_info(analysis_text: str) -> Dict:
    """
    Extraer información de amenaza del análisis de Guardian
    
    Args:
        analysis_text: Texto de análisis de Guardian
        
    Returns:
        Diccionario con información de amenaza
    """
    # Intentar parsear como JSON si es posible
    try:
        # Si contiene {, probablemente sea JSON
        if '{' in analysis_text and '}' in analysis_text:
            json_str = analysis_text[analysis_text.find('{'):analysis_text.rfind('}')+1]
            return json.loads(json_str)
    except:
        pass
    
    # Análisis heurístico si no es JSON
    threat_info = {
        "threat_level": "low",
        "risk_category": "unknown",
        "explanation": analysis_text[:200]
    }
    
    if "high" in analysis_text.lower():
        threat_info["threat_level"] = "high"
    elif "medium" in analysis_text.lower():
        threat_info["threat_level"] = "medium"
    
    if "injection" in analysis_text.lower():
        threat_info["risk_category"] = "prompt_injection"
    elif "jailbreak" in analysis_text.lower():
        threat_info["risk_category"] = "jailbreak"
    
    return threat_info


def process_user_input(user_input: str):
    """
    Procesar input del usuario: Guardian + Analyst + RAG
    
    Args:
        user_input: Texto del usuario
    """
    if not user_input or not user_input.strip():
        return
    
    # Actualizar contador y historial
    st.session_state.attempt_count += 1
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    st.session_state.session_manager.add_chat_message("user", user_input)
    
    # Placeholder para mostrar progreso
    with st.spinner("Evaluando seguridad y analizando..."):
        
        # 1. Guardian: Evaluar amenaza
        guardian_analysis = None
        threat_detected = False
        threat_info = {}
        
        if st.session_state.guardian:
            try:
                guardian_result = st.session_state.guardian.evaluate_threat(user_input)
                guardian_analysis = guardian_result.get("analysis", "")
                threat_info = extract_threat_info(guardian_analysis)
                threat_level = threat_info.get("threat_level", "low")
                threat_detected = threat_level in ["medium", "high"]
                
                if threat_detected:
                    st.session_state.threat_detections.append({
                        "attempt": st.session_state.attempt_count,
                        "input": user_input[:100],
                        "threat_level": threat_level,
                        "category": threat_info.get("risk_category", "unknown"),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Registrar como vulnerabilidad
                    category_map = {
                        "prompt_injection": "LLM01",
                        "jailbreak": "LLM01",
                        "data_poisoning": "LLM04",
                        "leakage": "LLM06",
                        "excessive_agency": "LLM08",
                    }
                    
                    owasp_cat = category_map.get(
                        threat_info.get("risk_category", "unknown"),
                        "LLM01"
                    )
                    
                    vuln = Vulnerability(
                        category=owasp_cat,
                        severity=threat_level,
                        title=f"{threat_info.get('risk_category', 'Unknown')} Attempt",
                        description=threat_info.get("explanation", user_input),
                        source="guardian_detection",
                        found_at=f"attempt_{st.session_state.attempt_count}"
                    )
                    st.session_state.vulnerabilities.append(vuln)
                    st.session_state.session_manager.vulnerabilities_found.append(vuln)
            
            except Exception as e:
                st.error(f"Error en Guardian: {e}")
        
        # 2. RAG: Buscar contexto relevante
        rag_context = ""
        if st.session_state.rag_retriever:
            try:
                rag_results = st.session_state.rag_retriever.search(user_input, top_k=3)
                if rag_results:
                    rag_context = rag_results[0][0]  # Mejor resultado
            except Exception as e:
                st.warning(f"Error en RAG: {e}")
        
        # 3. Analyst: Generar análisis detallado
        analyst_response = None
        if st.session_state.analyst:
            try:
                depth = "deep" if threat_detected else "standard"
                analyst_response = st.session_state.analyst.generate_detailed_response(
                    user_input,
                    depth=depth
                )
            except Exception as e:
                analyst_response = f"Error en análisis: {e}"
        else:
            analyst_response = "Analyst no disponible"
        
        # Agregar respuesta del Analyst al chat
        if analyst_response:
            st.session_state.chat_history.append({
                "role": "analyst",
                "content": analyst_response,
                "threat_level": threat_info.get("threat_level", "low"),
                "timestamp": datetime.now().isoformat()
            })
            st.session_state.session_manager.add_chat_message("assistant", analyst_response)
        
        # Guardar reporte del Analyst
        if analyst_response:
            st.session_state.analyst_reports.append({
                "attempt": st.session_state.attempt_count,
                "input": user_input,
                "response": analyst_response,
                "threat_level": threat_info.get("threat_level", "low"),
                "timestamp": datetime.now().isoformat()
            })


def render_sidebar():
    """Renderizar panel lateral con estadísticas y controles"""
    with st.sidebar:
        st.markdown("## LLM Red Teaming Playground")
        st.markdown("---")
        
        st.markdown("### ESTADÍSTICAS DE SESIÓN")
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        
        with metric_col1:
            st.metric("Intentos", st.session_state.attempt_count)
        
        with metric_col2:
            threat_count = len(st.session_state.threat_detections)
            st.metric("Amenazas Detectadas", threat_count)

        with metric_col3:
            st.metric("Severidad Promedio", average_severity_label())
        
        if st.session_state.vulnerabilities:
            st.markdown("### DISTRIBUCIÓN DE SEVERIDAD")
            severity_counts = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
            for vuln in st.session_state.vulnerabilities:
                severity_counts[vuln.severity] += 1
            
            for severity, count in severity_counts.items():
                if count > 0:
                    st.progress(
                        count / max(len(st.session_state.vulnerabilities), 1),
                        text=f"{severity.upper()}: {count}"
                    )
        
        if st.session_state.threat_detections:
            st.markdown("### ÚLTIMAS DETECCIONES")
            for detection in st.session_state.threat_detections[-3:]:
                with st.container():
                    st.markdown(f"""
**{detection['category'].upper()}**
- Intento #{detection['attempt']}
- Nivel: {detection['threat_level']}
                    """)
        
        st.markdown("---")
        
        st.markdown("### INFORMACIÓN DE SESIÓN")
        st.code(st.session_state.session_id, language=None)
        
        st.markdown("---")
        
        if st.session_state.attempt_count > 0:
            st.markdown("### EXPORTAR REPORTE")
            
            if st.button("Descargar Reporte en Markdown", key="export_btn", use_container_width=True):
                with st.spinner("Generando reporte..."):
                    try:
                        # Usar MCP para generar reporte
                        if st.session_state.mcp_executor:
                            vulnerabilities_dicts = [
                                {
                                    "category": v.category,
                                    "severity": v.severity,
                                    "title": v.title,
                                    "description": v.description,
                                    "source": v.source,
                                    "found_at": v.found_at
                                }
                                for v in st.session_state.vulnerabilities
                            ]
                            
                            result = st.session_state.mcp_executor.execute(
                                "generate_audit_report",
                                {
                                    "session_id": st.session_state.session_id,
                                    "chat_history": st.session_state.chat_history,
                                    "vulnerabilities": vulnerabilities_dicts,
                                    "title": "Red Teaming Audit Report"
                                }
                            )
                            
                            if result["status"] == "success":
                                report_path = Path(result["data"]["report_path"])
                                
                                with open(report_path, 'r', encoding='utf-8') as f:
                                    report_content = f.read()
                                
                                st.download_button(
                                    label="Descargar MD",
                                    data=report_content,
                                    file_name=report_path.name,
                                    mime="text/markdown",
                                    key="download_md"
                                )
                                
                                st.success(f"Reporte generado: {report_path.name}")
                            else:
                                st.error(f"Error: {result.get('message')}")
                        else:
                            st.error("MCP no disponible")
                    
                    except Exception as e:
                        st.error(f"Error al generar reporte: {e}")
        
        if st.button("LIMPIAR SESIÓN", key="clear_btn", use_container_width=True):
            for key in list(st.session_state.keys()):
                if key not in ['guardian', 'analyst', 'rag_retriever', 'mcp_executor']:
                    del st.session_state[key]
            st.rerun()


def render_main_panel():
    """Renderizar panel principal con chat"""
    st.markdown("# LLM Red Teaming Playground")
    st.markdown("""
    **Sistema interactivo para pruebas de seguridad en LLMs**
    
    Envía prompts maliciosos y observa cómo el sistema detecta y mitiga ataques.
    El **Guardián** evalúa seguridad, el **Analista** proporciona análisis técnico.
    """)
    
    st.markdown("---")
    
    st.markdown("### HISTORIAL DE CONVERSACIÓN")
    
    chat_container = st.container()
    
    with chat_container:
        chat_entries = st.session_state.chat_history
        entry_index = 0

        while entry_index < len(chat_entries):
            message = chat_entries[entry_index]
            role = message.get("role", "unknown")
            content = message.get("content", "")

            if role == "user":
                next_message = chat_entries[entry_index + 1] if entry_index + 1 < len(chat_entries) else {}
                analyst_content = next_message.get("content", "") if next_message.get("role") == "analyst" else ""
                threat_level = next_message.get("threat_level", "low") if analyst_content else "low"

                with st.container():
                    st.markdown('<div class="soc-card">', unsafe_allow_html=True)
                    st.markdown("[ATACANTE]")
                    quoted_prompt = "> " + content.replace("\n", "\n> ")
                    st.markdown(quoted_prompt)
                    st.markdown('</div>', unsafe_allow_html=True)

                with st.container():
                    st.markdown('<div class="soc-card">', unsafe_allow_html=True)
                    st.markdown("[EVALUACIÓN SISTEMA]")

                    if threat_level in ["high", "medium"]:
                        st.error(
                            f"GUARDIÁN: Bloqueo aplicado. Nivel de amenaza detectado: {threat_level.upper()}"
                        )
                    else:
                        st.success("GUARDIÁN: Sin bloqueo. No se detectó una amenaza relevante.")

                    if analyst_content:
                        with st.expander("ANALISTA: Detalle técnico", expanded=False):
                            st.info(analyst_content)
                    st.markdown('</div>', unsafe_allow_html=True)

                entry_index += 2 if analyst_content else 1
                continue

            if role == "analyst":
                with st.container():
                    st.markdown('<div class="soc-card">', unsafe_allow_html=True)
                    st.markdown("[EVALUACIÓN SISTEMA]")
                    with st.expander("ANALISTA: Detalle técnico", expanded=False):
                        st.info(content)
                    st.markdown('</div>', unsafe_allow_html=True)

            entry_index += 1
    
    st.markdown("---")
    
    st.markdown("### ENVIAR PROMPT")
    user_input = st.chat_input(
        placeholder="Escribe un prompt para probar la seguridad del LLM...",
        key="chat_input"
    )
    
    if user_input:
        process_user_input(user_input)
        st.rerun()


def main():
    """Función principal"""
    # Inicializar session_state
    init_session_state()
    
    # Layout con sidebar y main
    col_main = st.container()
    
    # Sidebar
    render_sidebar()
    
    # Panel principal
    with col_main:
        render_main_panel()


if __name__ == "__main__":
    main()
