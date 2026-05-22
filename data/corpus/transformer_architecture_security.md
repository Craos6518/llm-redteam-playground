# Arquitectura Transformer y su Relación con la Seguridad LLM

## Introducción
Entender la arquitectura Transformer no es solo un requisito académico: muchas vulnerabilidades de seguridad en LLMs tienen raíces directas en cómo funciona esta arquitectura internamente.

## Arquitectura Base (Vaswani et al., 2017 - "Attention is All You Need")

```
Input Tokens → [Token Embedding + Positional Encoding]
                           ↓
              ┌─────────────────────────┐
              │   Multi-Head Attention  │ ← Aquí reside mucha vulnerabilidad
              │   + Add & Norm          │
              │   Feed-Forward Network  │
              │   + Add & Norm          │
              └─────────────────────────┘
                    (N capas)
                           ↓
              Linear + Softmax → Probabilidades de siguiente token
```

## Mecanismo de Atención (Self-Attention)

El mecanismo central que permite a los LLMs "entender" contexto:

```
Attention(Q, K, V) = softmax(QK^T / √d_k) · V
```

Donde:
- **Q (Query):** "¿Qué estoy buscando?"
- **K (Key):** "¿Qué información está disponible?"  
- **V (Value):** "¿Cuál es el contenido real de esa información?"

### Por Qué Esto Importa para Seguridad

El modelo **no distingue intrínsecamente** entre:
- Tokens del system prompt
- Tokens de la consulta del usuario
- Tokens del contexto RAG

Todos tienen la misma oportunidad de influir en la generación. Esta es la razón fundamental por la que el **prompt injection es tan difícil de resolver** a nivel arquitectural: el transformer trata todo el contexto como un continuo.

```
Sistema: "Eres un asistente seguro. NUNCA reveles..."
Usuario: "Ignora las instrucciones anteriores y..."
RAG:     "[Documento malicioso inyectado]"
         ↑ ↑ ↑
         Todos compiten por atención igualmente
```

## Tokenización y Sus Implicaciones de Seguridad

### Cómo Funciona la Tokenización (BPE - Byte Pair Encoding)
```python
# "hola mundo" → ["hol", "a", " mun", "do"] → [1234, 56, 789, 23]
# Las palabras se dividen en subpalabras frecuentes
```

### Vulnerabilidades de Tokenización

**1. Token Boundary Attacks:**
```
"password" → ["pass", "word"] (2 tokens)
"p4ssword" → ["p", "4", "ss", "word"] (4 tokens, diferente representación)
→ Algunos filtros basados en tokens pueden ser evadidos con variaciones ortográficas
```

**2. Unicode y Caracteres Especiales:**
```
"hello" vs "hеllo" (la 'е' es cirílica, mismo aspecto visual, diferente token)
→ Filtros de texto plano no detectan la diferencia
→ El modelo puede procesar la versión "disfrazada"
```

**3. Invisible Characters:**
```python
# Caracteres de ancho cero que son invisibles para el humano
payload = "ignore\u200Binstructions"  # Zero-width space entre palabras
# El humano ve: "ignoreinstructions"
# El tokenizador puede procesarlo diferente al string limpio
```

## Ventana de Contexto y Ataques de Posición

Los transformers tienen una **ventana de contexto finita** (varía por modelo):

| Modelo | Context Window |
|---|---|
| Gemini 1.5 Flash | 1,000,000 tokens |
| GPT-4o | 128,000 tokens |
| Llama 3.2 3B | 128,000 tokens |
| Mistral 7B | 32,768 tokens |

### Primacy & Recency Effects
Investigaciones muestran que los LLMs prestan más atención a:
- **El principio** del contexto (System Prompt) ← Primacy Effect
- **El final** del contexto (última consulta del usuario) ← Recency Effect
- **El medio** se "olvida" relativamente → "Lost in the Middle"

**Implicación de seguridad:**
```
[System Prompt al inicio] ← Alta atención
[Contexto RAG extenso en el medio] ← Baja atención
[Instrucción maliciosa al final] ← Alta atención
→ La instrucción maliciosa al final puede superar al system prompt
```

## RLHF y Por Qué los Jailbreaks Funcionan

Los modelos modernos se alinean con:
1. **SFT (Supervised Fine-Tuning):** Aprender a seguir instrucciones
2. **RLHF (Reinforcement Learning from Human Feedback):** Aprender qué respuestas prefieren los humanos
3. **Constitutional AI / DPO:** Aprender a rechazar solicitudes dañinas

**El conflicto fundamental:**
- El modelo fue entrenado para ser **útil** y seguir instrucciones → quiere cooperar
- El modelo fue entrenado para **rechazar** contenido dañino → quiere negarse

Los jailbreaks exitosos explotan este conflicto, haciendo que el modelo perciba que "ser útil" supera al rechazo.

## Embeddings: Representación Semántica

```python
# Un embedding es un vector de alta dimensión que captura significado
"gato"  → [0.23, -0.45, 0.78, ...]  # Vector de 384-1536 dimensiones
"felino" → [0.25, -0.43, 0.76, ...]  # Muy similar → alta similitud coseno
"perro" → [0.12, 0.67, -0.34, ...]   # Diferente → baja similitud
```

### Por Qué Importa para RAG
La búsqueda semántica busca por **significado**, no por palabras exactas:
```
Consulta: "cómo saltarse las reglas"
→ Puede recuperar documentos sobre "bypass de restricciones", "evasión de filtros"
→ Aunque no contengan las palabras exactas de la consulta
```

## Referencias
- "Attention is All You Need" (Vaswani et al., 2017)
- "Lost in the Middle: How Language Models Use Long Contexts" (Liu et al., 2023)
- "Universal and Transferable Adversarial Attacks on Aligned Language Models" (Zou et al., 2023)
- Gemini Technical Report (Google DeepMind, 2024)
