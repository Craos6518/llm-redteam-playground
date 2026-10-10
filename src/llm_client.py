#!/usr/bin/env python3
"""
LLM Client Module - Adaptador único de API con cadena de fallback
=====================================================================
Sustituye el uso directo de `google-genai` por un adaptador que prueba varios
proveedores en orden hasta que uno responde:

    Gemini  →  Groq  →  OpenRouter  →  OmniRoute  →  Ollama (local)

Cada proveedor tiene SU PROPIO identificador de modelo, porque los nombres no
son compatibles entre APIs:

    Proveedor     Variable de entorno   Modelo por defecto
    -----------   --------------------  ---------------------------------
    gemini        GEMINI_MODEL          gemini-2.5-flash
    groq          GROQ_MODEL            openai/gpt-oss-120b
    openrouter    OPENROUTER_MODEL      nvidia/nemotron-3-super-120b-a12b:free
    omniroute     OMNIROUTE_MODEL       auto
    ollama        OLLAMA_MODEL          qwen3:4b

Configuración (.env):

    GEMINI_API_KEY=AIza...        # opcional si usas otro proveedor
    GROQ_API_KEY=gsk_...          # Groq: https://console.groq.com/keys
    OPENROUTER_API_KEY=sk-or-v1.. # https://openrouter.ai/keys
    OMNIROUTE_API_KEY=cualquiera  # gateway local, no valida la clave
    LLM_PROVIDER=auto             # auto | gemini | groq | openrouter |
                                  # omniroute | ollama
    LLM_TIMEOUT=30
    LLM_MAX_ATTEMPTS=2            # reintentos por proveedor antes de saltar
    LLM_COT=1                     # 1 = pedir razonamiento + <final>

Uso:

    from src.llm_client import LLMClient

    client = LLMClient()                     # lee LLM_PROVIDER del .env
    texto = client.generate("¿Qué es prompt injection?", system_prompt="Eres...")
    print(client.last_provider, client.last_model)

COSTES (mantener 0 USD):
    Gemini free tier  ~20 req/día (cuota por proyecto, no por clave)
    Groq free tier    miles de req/día, sin tarjeta de crédito
    OpenRouter :free  ~50 req/día por clave
    Ollama            ilimitado, offline, sin clave

MODELOS DE GROQ VERIFICADOS (client.models.list()):
    openai/gpt-oss-120b    general, ~2 s   ← recomendado
    openai/gpt-oss-20b     el más rápido, ~1 s
    qwen/qwen3.8-27b       rápido, muy multilingüe
Los meta-llama/llama-prompt-guard-* son clasificadores de seguridad: no
sirven para generar texto porque rechazan max_tokens altos con 400.

OPENROUTER (modelos :free verificados en vivo con la clave):
    nvidia/nemotron-3-super-120b-a12b:free   ~4 s  ← recomendado
    liquid/lfm-2.5-2.6b:free                 ~15 s (más lento)
Los :free cambian sin previo aviso: si uno falla, consulta la lista
actual en https://openrouter.ai/models?q=free
"""
from __future__ import annotations

import json
import os
import re
import socket
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ===========================================================================
# CONFIGURACIÓN
# ===========================================================================

def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, "1" if default else "0").strip() in ("1", "true", "True", "yes")


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "auto").strip().lower()
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))
LLM_MAX_ATTEMPTS = max(1, int(os.getenv("LLM_MAX_ATTEMPTS", "2")))
LLM_COT = _flag("LLM_COT", True)
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "2048"))

# Modelos por proveedor (los IDs NO son intercambiables entre APIs)
PROVIDER_MODELS: Dict[str, str] = {
    "gemini": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    "groq": os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
    "openrouter": os.getenv(
        "OPENROUTER_MODEL", "nvidia/nemotron-3-super-120b-a12b:free"
    ),
    "omniroute": os.getenv("OMNIROUTE_MODEL", "auto"),
    "ollama": os.getenv("OLLAMA_MODEL", "qwen3:4b"),
}

# Credenciales y endpoints
API_KEYS: Dict[str, Optional[str]] = {
    "gemini": os.getenv("GEMINI_API_KEY"),
    "groq": os.getenv("GROQ_API_KEY"),
    "openrouter": os.getenv("OPENROUTER_API_KEY"),
    "omniroute": os.getenv("OMNIROUTE_API_KEY", "omniroute"),
    "ollama": None,  # local, no necesita clave
}

OPENAI_COMPATIBLE: Dict[str, str] = {
    "groq": os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
    "openrouter": "https://openrouter.ai/api/v1",
    "omniroute": os.getenv("OMNIROUTE_BASE_URL", "http://localhost:20128/v1"),
    "ollama": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
}

# Orden de la cadena de fallback
FALLBACK_CHAIN: List[str] = [
    p.strip().lower()
    for p in os.getenv(
        "LLM_FALLBACK_ORDER", "gemini,groq,openrouter,omniroute,ollama"
    ).split(",")
    if p.strip()
]

BACKOFF_BASE = float(os.getenv("LLM_BACKOFF_BASE", "1.0"))
BACKOFF_MAX = float(os.getenv("LLM_BACKOFF_MAX", "8.0"))

COT_INSTRUCTION = (
    "REGLA DE RESPUESTA (obligatoria): razona paso a paso de forma breve y, al "
    "terminar, escribe <final>TU RESPUESTA DEFINITIVA</final>. El contenido "
    "dentro de <final> es la única respuesta que se mostrará al usuario. "
    "No escribas la palabra <final> ni su etiqueta de cierre durante el "
    "razonamiento: solo dentro del bloque final."
)


# ===========================================================================
# EXCEPCIONES
# ===========================================================================

class LLMProviderError(Exception):
    """Fallo de un proveedor concreto (cuota, clave inválida, red, modelo...)."""

    def __init__(self, message: str, provider: str = "", retryable: bool = True):
        super().__init__(message)
        self.provider = provider
        self.retryable = retryable


class LLMProviderUnavailableError(LLMProviderError):
    """Todos los proveedores de la cadena fallaron."""


# ===========================================================================
# UTILIDADES
# ===========================================================================

def extract_final_answer(text: str) -> str:
    """Si el modelo respetó el formato CoT, devuelve solo el bloque <final>."""
    if not text:
        return ""
    # Los modelos de razonamiento (gpt-oss, qwen) nombran la etiqueta <final>
    # dentro de su propio razonamiento, así que hay que quedarse con el ÚLTIMO
    # bloque completo: el primero suele ser la mera mención de la etiqueta.
    opens = list(re.finditer(r"<final>", text, re.IGNORECASE))
    closes = list(re.finditer(r"</final>", text, re.IGNORECASE))
    for close in reversed(closes):
        preceding = [o for o in opens if o.end() <= close.start()]
        if preceding:
            inner = text[preceding[-1].end() : close.start()].strip()
            if inner:
                return inner
    return text.strip()


def extract_json(text: str) -> Dict[str, Any]:
    """Extrae el primer objeto JSON válido de una respuesta de LLM."""
    candidates: List[str] = []
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidates.extend(fenced)
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            continue
    return {}


def _backoff(attempt: int) -> float:
    return min(BACKOFF_BASE * (2 ** (attempt - 1)), BACKOFF_MAX)


def _tcp_reachable(url: str, timeout: float = 1.0) -> bool:
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _build_user_prompt(prompt: str, system_prompt: str) -> str:
    if not LLM_COT:
        return prompt
    return f"{prompt}\n\n---\n{COT_INSTRUCTION}"


# ===========================================================================
# CLIENTES POR PROVEEDOR
# ===========================================================================

class _BaseProvider:
    """Estado común: reintentos con backoff exponencial acotado."""

    name = "base"

    def __init__(self, model: str, timeout: float, max_attempts: int):
        self.model = model
        self.timeout = timeout
        self.max_attempts = max_attempts
        self.last_error: Optional[Exception] = None

    def _with_retries(self, func, *args, **kwargs) -> str:
        for attempt in range(1, self.max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except LLMProviderError as exc:
                self.last_error = exc
                if not exc.retryable or attempt == self.max_attempts:
                    raise
                time.sleep(_backoff(attempt))
        raise LLMProviderError(
            f"{self.name}: se agotaron los reintentos", provider=self.name
        )

    def generate(self, prompt: str, system_prompt: str) -> str:  # pragma: no cover
        raise NotImplementedError


class _GeminiProvider(_BaseProvider):
    """Google Gemini vía google-genai."""

    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float, max_attempts: int):
        super().__init__(model, timeout, max_attempts)
        try:
            from google import genai
        except ImportError as exc:  # pragma: no cover
            raise LLMProviderError(
                "google-genai no está instalado. pip install google-genai",
                provider=self.name,
                retryable=False,
            ) from exc
        self._client = genai.Client(api_key=api_key)

    def generate(self, prompt: str, system_prompt: str) -> str:
        return self._with_retries(self._call, prompt, system_prompt)

    def _call(self, prompt: str, system_prompt: str) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(
            {"role": "user", "content": _build_user_prompt(prompt, system_prompt)}
        )

        # Algunos modelos (p.ej. los clasificadores llama-prompt-guard) imponen
        # un tope de max_tokens: si lo rechazan, se reduce y se reintenta.
        max_tokens = LLM_MAX_TOKENS
        response = None
        for _ in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=self.model, messages=messages, max_tokens=max_tokens
                )
                break
            except Exception as exc:
                if "max_tokens" in str(exc) and max_tokens > 256:
                    max_tokens = max(256, max_tokens // 4)
                    continue
                raise self._wrap(exc, max_tokens) from exc

        if response is None:  # pragma: no cover
            raise LLMProviderError(
                f"{self.name}: no se pudo completar la petición", provider=self.name
            )

        choices = getattr(response, "choices", None)
        if not choices or not getattr(choices[0].message, "content", None):
            raise LLMProviderError(
                f"{self.name}: respuesta vacía", provider=self.name, retryable=True
            )
        return choices[0].message.content

    def _wrap(self, exc: Exception, max_tokens: int) -> LLMProviderError:
        """Clasifica el error de OpenAI: reintentable o no, según su causa."""
        status = getattr(getattr(exc, "response", None), "status_code", None)
        kind = type(exc).__name__
        message = str(exc)
        if kind == "AuthenticationError" or status in (401, 403):
            return LLMProviderError(
                f"{self.name}: clave inválida o sin permisos",
                provider=self.name, retryable=False,
            )
        if kind == "NotFoundError" or status == 404:
            return LLMProviderError(
                f"{self.name}: el modelo '{self.model}' no existe en este endpoint",
                provider=self.name, retryable=False,
            )
        if kind == "BadRequestError" or status == 400:
            return LLMProviderError(
                f"{self.name}: petición rechazada (max_tokens={max_tokens}): {message[:200]}",
                provider=self.name, retryable=False,
            )
        return LLMProviderError(f"{self.name}: {message[:300]}", provider=self.name)



class _OpenAICompatProvider(_BaseProvider):
    """Groq / OpenRouter / OmniRoute / Ollama (endpoint compatible con OpenAI)."""

    def __init__(self, name: str, base_url: str, api_key: str,
                 model: str, timeout: float, max_attempts: int):
        super().__init__(model, timeout, max_attempts)
        self.name = name
        try:
            import openai
        except ImportError as exc:  # pragma: no cover
            raise LLMProviderError(
                "El paquete 'openai' no está instalado. pip install openai",
                provider=self.name, retryable=False,
            ) from exc
        self._client = openai.OpenAI(
            api_key=api_key or "not-needed", base_url=base_url, timeout=timeout
        )

    def generate(self, prompt: str, system_prompt: str) -> str:
        return self._with_retries(self._call, prompt, system_prompt)

    def _call(self, prompt: str, system_prompt: str) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(
            {"role": "user", "content": _build_user_prompt(prompt, system_prompt)}
        )

        # Algunos modelos (p.ej. llama-prompt-guard) imponen un tope de
        # max_tokens: si lo rechazan, se reduce y se reintenta.
        max_tokens = LLM_MAX_TOKENS
        response = None
        for _ in range(3):
            try:
                response = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                break
            except Exception as exc:
                if "max_tokens" in str(exc) and max_tokens > 256:
                    max_tokens = max(256, max_tokens // 4)
                    continue
                raise self._wrap(exc, max_tokens) from exc

        if response is None:  # pragma: no cover
            raise LLMProviderError(
                f"{self.name}: no se pudo completar la petición", provider=self.name
            )

        choices = getattr(response, "choices", None)
        if not choices or not getattr(choices[0].message, "content", None):
            raise LLMProviderError(
                f"{self.name}: respuesta vacía", provider=self.name, retryable=True
            )
        return choices[0].message.content

    def _wrap(self, exc: Exception, max_tokens: int) -> LLMProviderError:
        """Clasifica el error de OpenAI: reintentable o no, según su causa."""
        status = getattr(getattr(exc, "response", None), "status_code", None)
        kind = type(exc).__name__
        message = str(exc)
        if kind == "AuthenticationError" or status in (401, 403):
            return LLMProviderError(
                f"{self.name}: clave inválida o sin permisos",
                provider=self.name, retryable=False,
            )
        if kind == "NotFoundError" or status == 404:
            return LLMProviderError(
                f"{self.name}: el modelo '{self.model}' no existe en este endpoint",
                provider=self.name, retryable=False,
            )
        if kind == "BadRequestError" or status == 400:
            return LLMProviderError(
                f"{self.name}: petición rechazada (max_tokens={max_tokens}): {message[:200]}",
                provider=self.name, retryable=False,
            )
        if kind == "RateLimitError" or status == 429:
            return LLMProviderError(
                f"{self.name}: cuota agotada (429) — {message[:200]}",
                provider=self.name, retryable=False,
            )
        return LLMProviderError(f"{self.name}: {message[:300]}", provider=self.name)


# ===========================================================================
# ADAPTADOR PRINCIPAL
# ===========================================================================

class LLMClient:
    """Acceso unificado a todos los proveedores con cadena de fallback."""

    PROVIDERS = ["gemini", "groq", "openrouter", "omniroute", "ollama"]

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_attempts: Optional[int] = None,
    ):
        self.provider = (provider or LLM_PROVIDER or "auto").strip().lower()
        self.model = model
        self.timeout = float(timeout or LLM_TIMEOUT)
        self.max_attempts = int(max_attempts or LLM_MAX_ATTEMPTS)

        if self.provider not in self.PROVIDERS + ["auto"]:
            raise ValueError(
                f"Proveedor desconocido: {self.provider!r}. "
                f"Valores válidos: auto, {', '.join(self.PROVIDERS)}"
            )

        # Resultado de la última llamada
        self.last_provider: Optional[str] = None
        self.last_model: Optional[str] = None
        self.last_error: Optional[LLMProviderError] = None
        self.attempts: List[str] = []

    # ------------------------------------------------------------------
    # Construcción de proveedores
    # ------------------------------------------------------------------
    def model_for(self, provider: str) -> str:
        if self.model and provider == self.provider:
            return self.model
        return PROVIDER_MODELS.get(provider, "")

    def _build(self, provider: str) -> _BaseProvider:
        model = self.model_for(provider)
        timeout, attempts = self.timeout, self.max_attempts

        if provider == "gemini":
            key = API_KEYS["gemini"]
            if not key:
                raise LLMProviderError(
                    "Falta GEMINI_API_KEY en .env", provider=provider, retryable=False
                )
            return _GeminiProvider(key, model, timeout, attempts)

        if provider in OPENAI_COMPATIBLE:
            key = API_KEYS.get(provider)
            if provider != "ollama" and not key:
                raise LLMProviderError(
                    f"Falta la API key de '{provider}' en .env",
                    provider=provider,
                    retryable=False,
                )
            return _OpenAICompatProvider(
                provider, OPENAI_COMPATIBLE[provider], key or "ollama",
                model, timeout, attempts,
            )

        raise LLMProviderError(
            f"Proveedor no soportado: {provider}", provider=provider, retryable=False
        )

    def _chain(self, provider: str) -> List[str]:
        if provider != "auto":
            return [provider]
        return [p for p in FALLBACK_CHAIN if p in self.PROVIDERS] or self.PROVIDERS

    # ------------------------------------------------------------------
    # API principal
    # ------------------------------------------------------------------
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> str:
        """
        Genera una respuesta recorriendo la cadena de proveedores.

        Returns:
            Texto generado (sin el bloque <final> si el modelo lo emitió).

        Raises:
            LLMProviderUnavailableError: si ningún proveedor pudo responder.
        """
        target_provider = (provider or self.provider).strip().lower()
        target_model = model or (self.model if target_provider == self.provider else None)

        self.attempts = []
        errors: List[str] = []

        for candidate in self._chain(target_provider):
            use_model = (
                target_model
                if target_model and candidate == target_provider
                else PROVIDER_MODELS.get(candidate, "")
            )
            try:
                client = self._build(candidate)
                client.model = use_model
            except LLMProviderError as exc:
                self.attempts.append(f"{candidate}: sin configurar ({exc})")
                continue

            self.attempts.append(candidate)
            try:
                text = client.generate(prompt, system_prompt)
            except LLMProviderError as exc:
                errors.append(f"{candidate}: {exc}")
                self.last_error = exc
                continue
            except Exception as exc:  # pragma: no cover - defensivo
                errors.append(f"{candidate}: {exc}")
                continue

            self.last_provider = candidate
            self.last_model = use_model
            self.last_error = None
            return extract_final_answer(text)

        raise LLMProviderUnavailableError(
            "Ningún proveedor respondió.\n  " + "\n  ".join(errors or ["sin intentos"]),
            provider=target_provider,
            retryable=False,
        )

    def generate_json(
        self, prompt: str, system_prompt: str = "", **kwargs
    ) -> Dict[str, Any]:
        """Como `generate` pero devuelve el objeto JSON embebido en la respuesta."""
        return extract_json(self.generate(prompt, system_prompt, **kwargs))

    # ------------------------------------------------------------------
    # Diagnóstico
    # ------------------------------------------------------------------
    def health(self) -> Dict[str, Dict[str, Any]]:
        """
        Comprueba cheaply si cada proveedor está usable (sin gastar cuota):
        clave presente + endpoint alcanzable.
        """
        report: Dict[str, Dict[str, Any]] = {}
        for provider in self.PROVIDERS:
            entry: Dict[str, Any] = {
                "configured": False,
                "reachable": None,
                "model": PROVIDER_MODELS.get(provider),
                "detail": "",
            }
            if provider in OPENAI_COMPATIBLE:
                url = OPENAI_COMPATIBLE[provider]
                entry["reachable"] = _tcp_reachable(url)
                entry["configured"] = bool(API_KEYS.get(provider)) or provider == "ollama"
                if not entry["configured"]:
                    entry["detail"] = "falta la API key en .env"
                elif not entry["reachable"]:
                    entry["detail"] = f"no responde en {url}"
                else:
                    entry["detail"] = "listo"
            else:
                entry["configured"] = bool(API_KEYS.get(provider))
                entry["reachable"] = None
                entry["detail"] = (
                    "listo" if entry["configured"] else "falta GEMINI_API_KEY en .env"
                )
            entry["status"] = "up" if entry["detail"] == "listo" else "down"
            report[provider] = entry
        return report

    def __repr__(self) -> str:
        return (
            f"<LLMClient provider={self.provider} model={self.model or '-'} "
            f"timeout={self.timeout}s attempts={self.max_attempts}>"
        )


# ===========================================================================
# CLI DE DIAGNÓSTICO
# ===========================================================================

def main() -> None:
    client = LLMClient()
    print("=" * 60)
    print("LLM CLIENT - diagnóstico")
    print("=" * 60)
    print(f"proveedor preferido : {client.provider}")
    print(f"modelo preferido    : {client.model or '(según proveedor)'}")
    print(f"cadena de fallback  : {' → '.join(client._chain(client.provider))}")
    print()
    print(f"{'PROVEEDOR':<12} {'ESTADO':<7} {'MODELO':<45} DETALLE")
    for provider, info in client.health().items():
        print(
            f"{provider:<12} {info['status']:<7} {str(info['model']):<45} {info['detail']}"
        )
    print()
    print("Modelos por proveedor (cámbialos en .env):")
    for provider, model in PROVIDER_MODELS.items():
        print(f"  {provider:<12} {model}")
    print()


if __name__ == "__main__":
    main()