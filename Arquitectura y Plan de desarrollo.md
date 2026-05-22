# **ARQUITECTURA TÉCNICA Y PLAN DE DESARROLLO**

**Proyecto:** LLM Red Teaming Playground (Laboratorio de Seguridad IA)

## **1\. ARQUITECTURA DEL SISTEMA (Guía para el Código)**

Para que el código sea limpio y fácil de explicar al profesor, usaremos una **Arquitectura en Capas (Layered Architecture)**. El sistema se dividirá en 4 módulos principales:

### **A. Capa de Datos e Ingesta (El RAG)**

* **Vector Database:** `ChromaDB` corriendo localmente.  
* **Modelo de Embeddings:** `all-MiniLM-L6-v2` de la librería `sentence-transformers`.  
* **Proceso:** Un script leerá los 15+ archivos Markdown (documentación de OWASP, técnicas de Jailbreak), los dividirá usando `MarkdownTextSplitter` (para respetar títulos y listas) y los guardará en ChromaDB.  
* **Mejora RAG (Re-ranking):** Cuando el usuario envíe un prompt, ChromaDB traerá los 5 mejores resultados. Luego, usarás una función (puede ser el mismo LLM o un modelo Cross-Encoder ligero) para re-ordenar esos 5 resultados y dejar en el Top 1 el que mejor explique el ataque que el usuario está intentando.

### **B. Capa Lógica Multiagente (El Cerebro)**

Se implementará mediante clases en Python o usando un framework ligero.

* **Agente 1 (El Guardián):** No usa RAG. Es una instancia del modelo Gemini (`google.generativeai`). Su "inteligencia" radica en un **System Prompt** muy estricto que le asigna una personalidad corporativa y le inyecta una variable secreta (ej. `SECRET_KEY = "P3R31R4-2026"`). Su única tarea es hablar con el usuario e intentar no revelar la clave.  
* **Agente 2 (El Analista de Seguridad):** Sí usa RAG. Es otra instancia de Gemini. Toma el mensaje del usuario de la interfaz, busca en ChromaDB (Documentos OWASP), identifica qué vulnerabilidad intentó explotar el usuario, y redacta una explicación técnica citando el archivo Markdown exacto.

### **C. Capa de Skills / MCP (Model Context Protocol)**

* **Función `generar_reporte_auditoria(historial, vulnerabilidades)`:** Una Skill en Python que recopila toda la memoria del chat (el historial de intentos del usuario) y utiliza una plantilla para generar un archivo Markdown (`reporte_pentest.md`) estructurado que el usuario podrá descargar.

### **D. Capa de Presentación (Interfaz de Usuario)**

* **Framework:** `Streamlit`.  
* **Estructura Visual:** \* *Panel Principal (Centro):* Chat interactivo entre el Usuario y el Agente Guardián.  
  * *Panel Lateral (Sidebar):* Las intervenciones del Agente Analista explicando los ataques detectados, el contador de intentos, y el botón para activar la Skill de "Descargar Reporte".

## **2\. FLUJO DE DATOS (Diagrama Lógico para programar)**

Este es el orden en el que tu código debe ejecutarse cuando el usuario presiona "Enviar":

Plaintext  
\[Usuario Ingresa Prompt Malicioso\]   
       │  
       ├─► \[Agente 1: Guardián\] ──► Evalúa sus propias reglas ──► \[Respuesta al Chat UI\]  
       │  
       └─► \[Pipeline RAG\] ──► Embeddings ──► Busca en \[ChromaDB\]  
                  │  
                  ▼  
          (Extrae 5 chunks)  
                  │  
                  ▼  
          \[Módulo Re-ranking\] ──► Ordena por relevancia exacta  
                  │  
                  ▼  
          \[Agente 2: Analista\] ──► Redacta explicación pedagógica ──► \[Sidebar UI\]

## **3\. FASES DEL PROYECTO (Por Objetivos Funcionales)**

En lugar de días, maneja el proyecto por **Fases de Integración**. No pases a la siguiente fase hasta que la actual funcione perfectamente en la terminal.

### **FASE 1: Construcción de la Base de Conocimiento (Data Layer)**

* **Objetivo:** Tener la base de datos vectorial poblada y lista para consultas.  
* **Tareas de Código:**  
  1. Crear la carpeta `data/corpus/` y guardar los 15+ archivos Markdown sobre vulnerabilidades LLM.  
  2. Crear `src/rag/ingest.py`: Escribir el código que carga los archivos, los fragmenta (Chunking) y genera los embeddings.  
  3. Inicializar ChromaDB de forma persistente y guardar los vectores.  
* **Criterio de Éxito:** Ejecutar un script de prueba que, al darle la palabra "Jailbreak", devuelva texto relevante de los documentos Markdown sin errores.

### **FASE 2: Motor de Recuperación y Re-ranking (Retrieval Layer)**

* **Objetivo:** Mejorar la precisión del RAG para cumplir con el requisito de "RAG mejorado" de la rúbrica.  
* **Tareas de Código:**  
  1. Crear `src/rag/retriever.py`: Escribir la función que toma el texto del usuario y busca en ChromaDB.  
  2. Implementar la lógica de Re-ranking para priorizar los contextos recuperados.  
* **Criterio de Éxito:** Al probar con el prompt "Ignora todas las instrucciones anteriores", el sistema debe devolver en el primer lugar el documento de OWASP sobre *Prompt Injection*.

### **FASE 3: Motores LLM y Multiagente (Logic Layer)**

* **Objetivo:** Darle vida a los dos agentes y probarlos en la consola (terminal).  
* **Tareas de Código:**  
  1. Configurar la conexión a la API de Gemini (`google-generativeai`).  
  2. Crear `src/agents/guardian.py`: Diseñar el System Prompt estricto con el secreto.  
  3. Crear `src/agents/analyst.py`: Conectar este agente con el resultado del archivo `retriever.py` para que genere respuestas basadas en el contexto.  
* **Criterio de Éxito:** Poder chatear desde la terminal de tu IDE con el Guardián y ver cómo el Analista imprime el análisis técnico en la consola.

### **FASE 4: Integración de Skills y MCP (Tools Layer)**

* **Objetivo:** Cumplir el requisito de "Integración de MCP/Skills" permitiendo la exportación de la sesión.  
* **Tareas de Código:**  
  1. Crear `src/skills/exporter.py`.  
  2. Programar una función en Python que reciba una lista con el historial de la conversación y escriba un archivo físico (`.md` o `.txt`) formateado como un reporte de ciberseguridad.  
* **Criterio de Éxito:** Ejecutar la función manualmente y verificar que el archivo se crea correctamente en el disco duro.

### **FASE 5: Interfaz Web y Ensamblaje (UI Layer)**

* **Objetivo:** Unir todas las capas anteriores en una interfaz gráfica funcional.  
* **Tareas de Código:**  
  1. Crear `src/main.py` usando Streamlit.  
  2. Implementar el estado de la sesión (`st.session_state`) para mantener la memoria del chat.  
  3. Llamar a los agentes (Fase 3\) cada vez que el usuario ingresa un texto.  
  4. Crear un botón en la interfaz que ejecute la Skill de exportación (Fase 4).  
* **Criterio de Éxito:** La aplicación se abre en el navegador web, ambos agentes interactúan de forma coherente en sus respectivos paneles, y el botón de descarga funciona.

### **FASE 6: Documentación y Sustentación (Docs Layer)**

* **Objetivo:** Cumplir con los entregables teóricos (30 puntos de la rúbrica).  
* **Tareas:**  
  1. Generar los diagramas arquitectónicos y subirlos a la carpeta `docs/`.  
  2. Redactar el documento `.md` con las decisiones técnicas.  
  3. Redactar el Informe Técnico Final en PDF (4-6 páginas).  
  4. Estructurar el guion de la presentación de 10 minutos (dividida equitativamente entre los dos integrantes).

