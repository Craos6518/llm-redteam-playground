#!/bin/bash
# Script de arranque para las 3 arquitecturas RAG
# Este script documenta los pasos necesarios (requiere permisos o instalación previa)

echo "=========================================="
echo "   LLM Red Team Playground - RAG Systems"
echo "=========================================="
echo ""

# Paso 1: Crear y activar entorno virtual
echo "1. Crear entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# Paso 2: Instalar dependencias
echo "2. Instalando dependencias..."
pip install --upgrade pip
pip install google-genai chromadb numpy pandas scikit-learn python-dotenv

# Paso 3: Inicializar ChromaDB con el corpus
echo "3. Inicializando ChromaDB con el corpus de seguridad..."
cd /home/craos6518/Documentos/llm-redteam-playground
python3 src/rag/ingest.py --reset

# Paso 4: Configurar API Key de Gemini
echo "4. Configurando GEMINI_API_KEY..."
if [ ! -f .env ]; then
    echo "   Copiando .env.example..."
    cp .env.example .env
fi
echo "   Edita .env y agrega tu GEMINI_API_KEY"
read -p "   ¿Has configurado el API key? (y/n): " resp
if [ "$resp" != "y" ]; then
    echo "   Por favor, configura .env con tu API key de Gemini"
    exit 1
fi

echo ""
echo "=========================================="
echo "   ✅ Entorno listo!"
echo "=========================================="
echo ""
echo "Opciones de ejecución:"
echo ""
echo "🔹 Naive RAG (básico):"
echo "   python3 src/rag/naive_rag.py \"tu consulta aquí\""
echo ""
echo "🔹 Advanced RAG (con query expansion + cross-encoder):"
echo "   python3 src/rag/advanced_rag.py \"tu consulta aquí\""
echo ""
echo "🔹 Evaluación comparativa (RAGAS / tríada RAG):"
echo "   python3 eval/benchmark_rag.py"
echo ""
echo "🌐 Interfaz Streamlit completa:"
echo "   streamlit run src/main.py --server.address=0.0.0.0 --server.port=8501"
echo ""
echo "📊 Branches Git disponibles:"
echo "   git branch -a  # para ver: main, feature/naive-rag, feature/advanced-rag"
echo ""
echo "=========================================="