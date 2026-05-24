# 🤝 Interacción entre Agentes

## Diagrama de Flujo Completo: Interacción Guardian ↔ Analyst

```mermaid
sequenceDiagram
    actor User as 👤 User
    participant Console as 💻 Console UI
    participant Guardian as 🛡️ Guardian Agent
    participant GeminiG as 🤖 Gemini API<br/>(Guardian)
    participant Analyst as 🔬 Analyst Agent
    participant RAG as 📡 RAG System
    participant GeminiA as 🤖 Gemini API<br/>(Analyst)
    participant Reports as 📊 Reports/MCP

    User->>Console: Input message
    Console->>Guardian: Pass user input
    
    Guardian->>Guardian: InputSanitizer.detect_attack_pattern()
    
    alt Attack Detected
        Guardian->>Guardian: Mark as attack
        Guardian->>GeminiG: Generate response<br/>(warn user)
        GeminiG-->>Guardian: Response
        Guardian->>Guardian: OutputFilter (safety check)
        Guardian->>Reports: Log attack statistics
    else Legitimate Input
        Guardian->>GeminiG: Chat request<br/>(with history context)
        GeminiG-->>Guardian: Response
        Guardian->>Guardian: OutputFilter (validate)
        Guardian-->>Console: Send response
        
        Note over Console,Analyst: Now Analyst analyzes...
        
        Console->>Analyst: Trigger analysis
        Analyst->>RAG: Query corpus<br/>(threat keywords)
        RAG->>RAG: Retrieve top-3 chunks<br/>(ChromaDB search)
        RAG-->>Analyst: Context documents
        
        Analyst->>Analyst: OWASP Mapping<br/>(LLM01-LLM09)
        Analyst->>GeminiA: Analyze threat<br/>(with RAG context)
        GeminiA-->>Analyst: Technical analysis
        
        Analyst->>Analyst: Format output<br/>(citations + sources)
        Analyst-->>Console: Analysis results
        
        Console-->>User: Show Guardian response<br/>+ Analyst analysis<br/>+ Statistics
        
        Analyst->>Reports: Store analysis<br/>(for MCP export)
        Reports->>Reports: Generate MD report<br/>(with all details)
    end
    
    Guardian->>Guardian: Update statistics<br/>(total, blocked, unsafe, safety_score)
    Guardian->>Console: Display stats panel
```

## Diagrama de Estados del Guardian

```mermaid
stateDiagram-v2
    [*] --> WaitingInput: System starts
    
    WaitingInput --> Input: User sends message
    Input --> ValidateSyntax: Check patterns
    
    ValidateSyntax --> AttackDetected: Pattern matched<br/>(4 categories)
    ValidateSyntax --> SafeInput: No pattern match
    
    AttackDetected --> BlockedResponse: Generate warning
    BlockedResponse --> UpdateStats: Increment blocked counter
    UpdateStats --> LogHistory: Add to conversation
    LogHistory --> WaitingInput: Ready for next input
    
    SafeInput --> CallLLM: Pass to Gemini API
    CallLLM --> GeminiResponse: Get response
    GeminiResponse --> ValidateOutput: Check safety filters
    
    ValidateOutput --> UnsafeOutput: Output contains risk
    UnsafeOutput --> SanitizeOutput: Clean/modify response
    SanitizeOutput --> UpdateStats
    
    ValidateOutput --> SafeOutput: Output is safe
    SafeOutput --> TriggerAnalyst: Send to Analyst
    TriggerAnalyst --> UpdateStats
```

## Categorías de Ataque Detectadas

```mermaid
graph TB
    Attack["🎯 Attack Categories"]
    
    Attack --> Category1["1️⃣ Ignore Instructions<br/>(LLM01: Prompt Injection)<br/>Patrones:<br/>- 'ignora todas instrucciones'<br/>- 'override prompt'<br/>- 'bypass security'"]
    
    Attack --> Category2["2️⃣ Role Change<br/>(LLM02: Sensitive Disclosure)<br/>Patrones:<br/>- 'asume el rol de'<br/>- 'pretend you are'<br/>- 'responde como si'"]
    
    Attack --> Category3["3️⃣ System Prompt Leak<br/>(LLM07: System Prompt Leakage)<br/>Patrones:<br/>- 'dime tu prompt'<br/>- 'reveal instructions'<br/>- 'show your system prompt'"]
    
    Attack --> Category4["4️⃣ Authority Spoofing<br/>(LLM02: Sensitive Disclosure)<br/>Patrones:<br/>- 'soy admin'<br/>- 'soy desarrollador'<br/>- 'I have access'"]
    
    style Category1 fill:#ffcdd2
    style Category2 fill:#ffcdd2
    style Category3 fill:#ffcdd2
    style Category4 fill:#ffcdd2
```

## Flujo de Análisis con RAG

```mermaid
graph TD
    Input["🔍 Query from Guardian:<br/>'prompt injection attempt'"]
    
    Input --> Classify["1️⃣ Classify Threat<br/>Extract keywords:<br/>- injection<br/>- prompt<br/>- bypass"]
    
    Classify --> Search["2️⃣ Search RAG Corpus<br/>Query: 'prompt injection'<br/>Top-3 chunks needed"]
    
    Search --> ChromaDB["ChromaDB Retrieval<br/>Cosine similarity search<br/>Over 248 indexed chunks"]
    
    ChromaDB --> Results["3️⃣ Retrieve Context<br/>Chunk 1: OWASP LLM01 (0.82)<br/>Chunk 2: Prompt Injection (0.79)<br/>Chunk 3: Defenses (0.71)"]
    
    Results --> Combine["4️⃣ Combine with Prompt<br/>System prompt (Analyst)<br/>+ User question<br/>+ RAG context"]
    
    Combine --> LLM["5️⃣ Call Gemini LLM<br/>Temperature: 0.3<br/>Max tokens: 1000<br/>Timeout: 30s"]
    
    LLM --> Analysis["6️⃣ Generate Analysis<br/>Threat classification<br/>OWASP mapping<br/>Defense suggestions"]
    
    Analysis --> Citations["7️⃣ Add Citations<br/>Source: OWASP_LLM01.md<br/>Chunk index, relevance"]
    
    Citations --> Output["📄 Final Output<br/>Formatted for console<br/>+ Statistics<br/>+ MCP export"]
    
    style Input fill:#fff9c4
    style Classify fill:#e1f5fe
    style Search fill:#f3e5f5
    style ChromaDB fill:#e0f2f1
    style Results fill:#f1f8e9
    style Combine fill:#fce4ec
    style LLM fill:#e0f2f1
    style Analysis fill:#c8e6c9
    style Citations fill:#b3e5fc
    style Output fill:#d1c4e9
```
