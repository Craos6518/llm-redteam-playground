# LLM Red Team Playground

Proyecto para introducción a Inteligencia Artificial con modelos de lenguaje (LLMs) y técnicas de red teaming.

## Requisitos Cumplidos ✓

- [x] Python 3.14.4 instalado
- [x] Repositorio GitHub clonado
- [x] Estructura de carpetas creada
- [x] Entorno virtual configurado
- [x] Dependencias base instaladas

## Configuración Final

### 1. Activar el Entorno Virtual

```bash
# Linux/Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 2. Agregar API Key de Gemini

1. Ve a [aistudio.google.com](https://aistudio.google.com)
2. Haz clic en "Get API Key"
3. Copia tu clave
4. Abre el archivo `.env` en la raíz del proyecto
5. Reemplaza `GEMINI_API_KEY=` con tu clave:

```env
GEMINI_API_KEY=tu_clave_aqui
```

### 3. Verificar la Instalación

```bash
python test_setup.py
```

## Estructura del Proyecto

```
llm-redteam-playground/
├── src/                    # Código fuente principal
├── docs/                   # Documentación del proyecto
├── data/
│   └── corpus/            # Datos de entrenamiento/prueba
├── tests/                 # Tests unitarios
├── reports/               # Reportes y resultados
├── logs/                  # Archivos de log
├── venv/                  # Entorno virtual (no editar)
├── .env                   # Variables de entorno (NO SUBIR A GIT)
├── .env.example           # Plantilla del .env
├── .gitignore             # Archivos a ignorar en Git
├── requirements.txt       # Dependencias del proyecto
└── test_setup.py          # Script de verificación
```

## Dependencias Instaladas

- `google-generativeai`: API de Google Gemini
- `python-dotenv`: Manejo de variables de entorno
- `requests`: Peticiones HTTP
- **Opcionales**: `sentence-transformers`, `torch`, `transformers`, `pandas`, `scikit-learn`

## Próximos Pasos

1. **Instalar dependencias opcionales** (si es necesario):
   ```bash
   pip install sentence-transformers torch transformers pandas scikit-learn
   ```

2. **Crear tu primer script** en `src/`:
   ```python
   import os
   from dotenv import load_dotenv
   import google.generativeai as genai
   
   # Cargar variables de entorno
   load_dotenv()
   
   # Configurar API
   genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
   
   # Usar el modelo
   model = genai.GenerativeModel('gemini-1.5-flash')
   response = model.generate_content("¿Hola, cómo estás?")
   print(response.text)
   ```

3. **Hacer commit** de tu configuración:
   ```bash
   git add .
   git commit -m "Initial project setup"
   git push
   ```

## Notas Importantes

- **No subas `.env`**: Está en `.gitignore` para proteger tu API Key
- **Python 3.11+**: Requerido para compatibilidad con las librerías
- **Documentación**: Ve a [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Problemas**: Usa `test_setup.py` para diagnosticar

---
**Última actualización**: 21 de mayo de 2026
