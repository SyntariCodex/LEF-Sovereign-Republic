"""
LLMRouter — Provider-Agnostic LLM Abstraction Layer (Phase 39)

Central routing infrastructure for all LLM calls in the Republic.
Supports Gemini, Claude, and Ollama with per-provider circuit breakers,
config-driven model selection, and fallback chains.

Usage:
    from system.llm_router import get_router
    router = get_router()
    response = router.generate(prompt, agent_name='LEF', context_label='METACOGNITION')
"""

import os
import json
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent        # republic/
PROJECT_DIR = BASE_DIR.parent                  # LEF Ai/
CONFIG_PATH = BASE_DIR / 'config' / 'config.json'


class LLMRouter:
    """Provider-agnostic LLM routing with circuit breaker, fallback, and audit trail."""

    def __init__(self, config_path=None):
        self._lock = threading.Lock()
        self._config = self._load_config(config_path or CONFIG_PATH)
        self._llm_cfg = self._config.get('llm', {})

        # Provider clients — lazy init
        self._gemini_client = None
        self._claude_client = None

        # Per-provider state
        self._provider_failures = {'gemini': 0, 'claude': 0, 'ollama': 0}
        self._provider_call_counts = {'gemini': 0, 'claude': 0, 'ollama': 0}
        self._provider_circuit_open = {'gemini': False, 'claude': False, 'ollama': False}
        self._provider_circuit_opened_at = {'gemini': 0.0, 'claude': 0.0, 'ollama': 0.0}

        # Circuit breaker config
        cb = self._llm_cfg.get('circuit_breaker', {})
        self._failure_threshold = cb.get('failure_threshold', 3)
        self._cooldown_seconds = cb.get('cooldown_seconds', 300)

    # ── Config ──────────────────────────────────────────────────────────────

    def _load_config(self, config_path) -> dict:
        """Load config.json."""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[LLMRouter] Config load failed: {e} — using defaults")
            return {}

    def _resolve_model(self, agent_name: str, model_override: str = None) -> str:
        """Resolve model: override > per-agent config > primary_model."""
        if model_override:
            return model_override
        overrides = self._llm_cfg.get('agent_overrides', {})
        if agent_name and agent_name in overrides:
            return overrides[agent_name]
        return self._llm_cfg.get('primary_model', 'gemini-2.0-flash')

    def _get_fallback_model(self) -> str:
        """Return configured fallback model."""
        return self._llm_cfg.get('fallback_model', 'gemini-1.5-flash')

    def _get_provider_for_model(self, model_id: str) -> str:
        """Determine provider from model_id prefix/substring."""
        m = model_id.lower()
        if 'gemini' in m:
            return 'gemini'
        if 'claude' in m or 'anthropic' in m:
            return 'claude'
        if 'ollama' in m or 'llama' in m or 'mistral' in m or 'phi' in m:
            return 'ollama'
        # Default to gemini
        return 'gemini'

    # ── Token Budget ─────────────────────────────────────────────────────────

    def _check_token_budget(self, model_id: str, agent_name: str) -> bool:
        """Return True if call is permitted by token budget."""
        try:
            from system.token_budget import get_budget
            budget = get_budget()
            return budget.can_call(model=model_id, agent_name=agent_name)
        except Exception:
            return True  # Don't block calls if budget unavailable

    def _record_token_usage(self, model_id: str, agent_name: str, tokens: int = 500):
        """Record token usage in budget."""
        try:
            from system.token_budget import get_budget
            budget = get_budget()
            budget.record_usage(model=model_id, tokens_used=tokens, agent_name=agent_name)
        except Exception:
            pass

    # ── Circuit Breaker ───────────────────────────────────────────────────────

    def _is_circuit_open(self, provider: str) -> bool:
        """Check if provider circuit is open (in cooldown)."""
        with self._lock:
            if not self._provider_circuit_open[provider]:
                return False
            elapsed = time.time() - self._provider_circuit_opened_at[provider]
            if elapsed >= self._cooldown_seconds:
                # Reset circuit
                self._provider_circuit_open[provider] = False
                self._provider_failures[provider] = 0
                logger.info(f"[LLMRouter] Circuit reset for {provider} (cooldown expired)")
                return False
            return True

    def _record_failure(self, provider: str):
        """Increment failure count; open circuit if threshold exceeded."""
        with self._lock:
            self._provider_failures[provider] += 1
            if self._provider_failures[provider] >= self._failure_threshold:
                self._provider_circuit_open[provider] = True
                self._provider_circuit_opened_at[provider] = time.time()
                logger.warning(f"[LLMRouter] Circuit OPEN for {provider} "
                                f"({self._failure_threshold} failures)")

    def _record_success(self, provider: str):
        """Reset failure count on success."""
        with self._lock:
            self._provider_failures[provider] = 0
            self._provider_call_counts[provider] += 1

    # ── Provider Calls ────────────────────────────────────────────────────────

    def _get_gemini_client(self):
        """Lazy-init Gemini client."""
        with self._lock:
            if self._gemini_client is None:
                try:
                    from google import genai
                    keys_cfg = self._llm_cfg.get('provider_keys', {})
                    key_ref = keys_cfg.get('gemini', 'ENV:GEMINI_API_KEY')
                    api_key = None
                    if isinstance(key_ref, str) and key_ref.startswith('ENV:'):
                        api_key = os.getenv(key_ref[4:])
                    if api_key:
                        self._gemini_client = genai.Client(api_key=api_key)
                    else:
                        self._gemini_client = genai.Client()
                except Exception as e:
                    logger.warning(f"[LLMRouter] Gemini client init failed: {e}")
            return self._gemini_client

    def _get_claude_client(self):
        """Lazy-init Claude client."""
        with self._lock:
            if self._claude_client is None:
                try:
                    import anthropic
                    keys_cfg = self._llm_cfg.get('provider_keys', {})
                    key_ref = keys_cfg.get('claude', 'ENV:ANTHROPIC_API_KEY')
                    api_key = None
                    if isinstance(key_ref, str) and key_ref.startswith('ENV:'):
                        api_key = os.getenv(key_ref[4:])
                    if api_key:
                        self._claude_client = anthropic.Anthropic(api_key=api_key)
                    else:
                        self._claude_client = anthropic.Anthropic()
                except Exception as e:
                    logger.warning(f"[LLMRouter] Claude client init failed: {e}")
            return self._claude_client

    def _call_gemini(self, prompt: str, model_id: str, timeout_seconds: int) -> str:
        """Call Gemini via ThreadPoolExecutor with timeout. Matches agent_lef pattern."""
        client = self._get_gemini_client()
        if not client:
            return None
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    client.models.generate_content,
                    model=model_id,
                    contents=prompt
                )
                result = future.result(timeout=timeout_seconds)
                if result and result.text:
                    return result.text.strip()
                return None
        except FuturesTimeoutError:
            logger.warning(f"[LLMRouter] Gemini timeout ({timeout_seconds}s) for {model_id}")
            return None
        except Exception as e:
            logger.warning(f"[LLMRouter] Gemini error ({model_id}): {e}")
            return None

    def _call_claude(self, prompt: str, model_id: str, timeout_seconds: int) -> str:
        """Call Claude (Anthropic) API."""
        client = self._get_claude_client()
        if not client:
            return None
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    client.messages.create,
                    model=model_id,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}]
                )
                result = future.result(timeout=timeout_seconds)
                if result and result.content:
                    return result.content[0].text.strip()
                return None
        except FuturesTimeoutError:
            logger.warning(f"[LLMRouter] Claude timeout ({timeout_seconds}s) for {model_id}")
            return None
        except Exception as e:
            logger.warning(f"[LLMRouter] Claude error ({model_id}): {e}")
            return None

    def _call_ollama(self, prompt: str, model_id: str, timeout_seconds: int) -> str:
        """Call Ollama local model via HTTP POST."""
        try:
            import urllib.request
            payload = json.dumps({"model": model_id, "prompt": prompt, "stream": False}).encode()
            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                data = json.loads(resp.read().decode())
                return data.get("response", "").strip() or None
        except Exception as e:
            logger.warning(f"[LLMRouter] Ollama error ({model_id}): {e}")
            return None

    # ── Failure Logging ───────────────────────────────────────────────────────

    def _log_failure_to_feed(self, provider: str, model_id: str, agent_name: str, err: str):
        """Write LLM failure to consciousness_feed (non-crashing)."""
        try:
            from db.db_helper import db_connection
            base_dir = str(BASE_DIR / 'republic.db')
            with db_connection(base_dir) as conn:
                conn.execute(
                    "INSERT INTO consciousness_feed (agent_name, content, category) VALUES (?, ?, ?)",
                    ('LLMRouter', json.dumps({
                        'provider': provider, 'model': model_id,
                        'agent': agent_name, 'error': str(err)[:200]
                    }), 'llm_failure')
                )
                conn.commit()
        except Exception:
            pass  # Never crash on logging failure

    # ── Core Generate ─────────────────────────────────────────────────────────

    def generate(self, prompt: str, agent_name: str = 'UNKNOWN',
                 context_label: str = 'UNKNOWN', timeout_seconds: int = 90,
                 model_override: str = None) -> str:
        """
        Central generation method. All agents call this.
        Returns response text string or None on failure.
        """
        model_id = self._resolve_model(agent_name, model_override)
        provider = self._get_provider_for_model(model_id)

        # 1. Check token budget
        if not self._check_token_budget(model_id, agent_name):
            logger.warning(f"[LLMRouter] Token budget exhausted for {model_id} ({agent_name})")
            return None

        # 2. Try primary provider
        response = None
        if not self._is_circuit_open(provider):
            t0 = time.time()
            if provider == 'gemini':
                response = self._call_gemini(prompt, model_id, timeout_seconds)
            elif provider == 'claude':
                response = self._call_claude(prompt, model_id, timeout_seconds)
            elif provider == 'ollama':
                response = self._call_ollama(prompt, model_id, timeout_seconds)

            latency_ms = int((time.time() - t0) * 1000)
            if response:
                self._record_success(provider)
                self._record_token_usage(model_id, agent_name)
                logger.debug(f"[LLMRouter] {context_label} via {provider}/{model_id} "
                             f"({latency_ms}ms) → {len(response)} chars")
                return response
            else:
                self._record_failure(provider)
                self._log_failure_to_feed(provider, model_id, agent_name, 'empty_or_error')

        # 3. Fallback model
        fallback_id = self._get_fallback_model()
        if fallback_id != model_id:
            fallback_provider = self._get_provider_for_model(fallback_id)
            if not self._is_circuit_open(fallback_provider):
                logger.info(f"[LLMRouter] Falling back to {fallback_id} for {context_label}")
                if fallback_provider == 'gemini':
                    response = self._call_gemini(prompt, fallback_id, timeout_seconds)
                elif fallback_provider == 'claude':
                    response = self._call_claude(prompt, fallback_id, timeout_seconds)
                if response:
                    self._record_success(fallback_provider)
                    self._record_token_usage(fallback_id, agent_name)
                    return response
                else:
                    self._record_failure(fallback_provider)

        logger.error(f"[LLMRouter] All providers failed for {context_label} ({agent_name})")
        return None

    # ── Stats ─────────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return per-provider call counts, failure counts, circuit state."""
        with self._lock:
            return {
                'providers': {
                    p: {
                        'calls': self._provider_call_counts[p],
                        'failures': self._provider_failures[p],
                        'circuit_open': self._provider_circuit_open[p]
                    }
                    for p in ['gemini', 'claude', 'ollama']
                },
                'primary_model': self._llm_cfg.get('primary_model', 'gemini-2.0-flash'),
                'fallback_model': self._llm_cfg.get('fallback_model', 'gemini-1.5-flash'),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────

_router_instance = None
_router_lock = threading.Lock()


def get_router() -> LLMRouter:
    """Module-level singleton accessor."""
    global _router_instance
    with _router_lock:
        if _router_instance is None:
            _router_instance = LLMRouter()
    return _router_instance


def call_with_timeout(fn, *args, timeout_seconds: int = 120, **kwargs):
    """
    Call any LLM API callable with a hard wall-clock timeout.

    Wraps fn(*args, **kwargs) in a ThreadPoolExecutor so a hung network
    connection cannot block the calling thread indefinitely.  Returns the
    function's return value on success, or None on timeout / exception.

    Usage (Gemini fallback):
        response = call_with_timeout(
            client.models.generate_content,
            timeout_seconds=120,
            model=model_id, contents=prompt
        )
        text = response.text.strip() if response and response.text else None

    Usage (Claude fallback):
        result = call_with_timeout(
            client.messages.create,
            timeout_seconds=120,
            model=model_id, max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )
        text = result.content[0].text.strip() if result and result.content else None
    """
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn, *args, **kwargs)
            return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError:
        logger.warning(
            "[LLMRouter] call_with_timeout: %s timed out after %ds",
            getattr(fn, '__name__', str(fn)), timeout_seconds
        )
        return None
    except Exception as e:
        logger.warning(
            "[LLMRouter] call_with_timeout: %s raised %s: %s",
            getattr(fn, '__name__', str(fn)), type(e).__name__, e
        )
        return None
