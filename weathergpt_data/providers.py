"""Model access: one interface, three providers, a recorded choice.

The engine asks for a structured completion and gets back parsed data plus a trace of who
produced it. Providers are an enhancement, never the floor: the rule planner answers the
core problem-statement shapes with no model at all, Ollama answers locally, and OpenRouter
answers from a free-model pool when a key is configured in local backend configuration.

Invariants that no provider may bend: model output never executes code or SQL, never supplies
a measurement, and never decides an entity, window, unit or source. This module returns
candidate plans only; the governed tools do the rest.
"""
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit

from .transport import SourceError

ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG = ROOT / 'data' / 'runtime' / 'model-config.json'
OPENROUTER_BASE = 'https://openrouter.ai/api/v1'
OPENROUTER_MODELS_URL = OPENROUTER_BASE + '/models'
OPENROUTER_CHAT_URL = OPENROUTER_BASE + '/chat/completions'
# Free-tier ids seen in the OpenRouter catalogue. The router prefers these in order and
# falls back to any other id the key can reach only if a caller asks for it explicitly.
DEFAULT_FREE_MODELS = (
    'deepseek/deepseek-chat-v3.1:free',
    'z-ai/glm-4.5-air:free',
    'qwen/qwen3-235b-a22b:free',
    'meta-llama/llama-3.3-70b-instruct:free',
    'mistralai/mistral-small-3.2-24b-instruct:free',
    'google/gemini-2.0-flash-exp:free',
)
MAX_ATTEMPTS_PER_MODEL = 2
DEFAULT_TIMEOUT = 90.0
RETRY_BACKOFF_SECONDS = 1.5
RULE_MODEL = 'rule-planner-v1'
FENCE = chr(96) * 3


class ProviderUnavailable(SourceError):
    """Raised when a provider cannot answer: no key, refused, rate limited or unreachable."""


def local_config():
    """Local backend configuration. Never logged, never committed, never returned whole."""
    data = {}
    if LOCAL_CONFIG.exists():
        try:
            data = json.loads(LOCAL_CONFIG.read_text(encoding='utf-8')) or {}
        except ValueError:
            data = {}
    return data


def openrouter_key():
    """The OpenRouter key from the environment first, then local configuration."""
    key = os.getenv('OPENROUTER_API_KEY') or local_config().get('openrouter_api_key') or ''
    return str(key).strip()


def key_source():
    if os.getenv('OPENROUTER_API_KEY'):
        return 'environment OPENROUTER_API_KEY'
    if str(local_config().get('openrouter_api_key') or '').strip():
        return str(LOCAL_CONFIG.relative_to(ROOT))
    return 'not configured'


def free_models():
    """The model ids the router may use, free-tier first, from configuration or the default list."""
    configured = os.getenv('WEATHERGPT_MODELS') or local_config().get('models')
    if isinstance(configured, str):
        configured = [item.strip() for item in configured.split(',') if item.strip()]
    if configured:
        return tuple(str(item) for item in configured)
    return DEFAULT_FREE_MODELS


def extract_json(text):
    """The first JSON object in a model reply, tolerating prose and code fences."""
    if not isinstance(text, str) or not text.strip():
        raise ProviderUnavailable('The provider returned no content')
    body = text.strip()
    if body.startswith(FENCE):
        body = re.sub(r'^' + FENCE + r'[a-zA-Z]*\s*|' + FENCE + r'\s*$', '', body)
    try:
        return json.loads(body)
    except ValueError:
        pass
    start = body.find('{')
    while start != -1:
        depth, in_string, escape = 0, False, False
        for position in range(start, len(body)):
            character = body[position]
            if in_string:
                if escape:
                    escape = False
                elif character == '\\':
                    escape = True
                elif character == '"':
                    in_string = False
                continue
            if character == '"':
                in_string = True
            elif character == '{':
                depth += 1
            elif character == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(body[start:position + 1])
                    except ValueError:
                        break
        start = body.find('{', start + 1)
    raise ProviderUnavailable('The provider reply was not JSON')


class OllamaClient:
    """A local Ollama endpoint. Loopback only: this adapter never reaches off the machine."""

    name = 'ollama'

    def __init__(self, model=None, base=None, timeout=DEFAULT_TIMEOUT, lock=None):
        self.model = model or os.getenv('WEATHERGPT_MODEL', 'qwen3.6:latest')
        self.base = (base or os.getenv('WEATHERGPT_OLLAMA_URL', 'http://127.0.0.1:11434')).rstrip('/')
        self.timeout = timeout
        self.lock = lock or threading.Lock()
        parts = urlsplit(self.base)
        if parts.scheme != 'http' or parts.hostname not in {'127.0.0.1', 'localhost', '::1'}:
            raise ValueError('This adapter only uses a local Ollama endpoint')

    def complete(self, system, user, schema, max_tokens=1100):
        payload = {'model': self.model, 'messages': [{'role': 'system', 'content': system},
                                                     {'role': 'user', 'content': user}],
                   'stream': False, 'think': False, 'format': schema, 'keep_alive': '20m',
                   'options': {'temperature': 0, 'num_predict': max_tokens, 'num_ctx': 8192}}
        request = urllib.request.Request(self.base + '/api/chat', json.dumps(payload).encode(),
                                         {'Content-Type': 'application/json'})
        if not self.lock.acquire(timeout=2):
            raise ProviderUnavailable('The local model is answering another question. Try again shortly.')
        began = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read(200000))
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise ProviderUnavailable('The local model did not answer: ' + type(error).__name__) from error
        finally:
            self.lock.release()
        if not isinstance(data, dict):
            # Measured on 15 September 2026: a bare null answer crashed the planning turn.
            raise ProviderUnavailable('The local model returned no structured response. Please retry.')
        if data.get('done_reason') == 'length':
            raise ProviderUnavailable('The model response was incomplete. Please shorten the question.')
        content = (data.get('message') or {}).get('content', '')
        return extract_json(content), {'provider': self.name, 'model': self.model,
                                       'latency_ms': round((time.monotonic() - began) * 1000),
                                       'input_tokens': data.get('prompt_eval_count'),
                                       'output_tokens': data.get('eval_count')}


class OpenRouterClient:
    """OpenRouter over HTTPS, restricted to the models a caller allows.

    Every failure mode is named rather than retried blindly: a refused key disables the
    provider for the process, a model-level refusal moves to the next model, and a rate limit
    or transport error is retried once with a short backoff before moving on.
    """

    name = 'openrouter'

    def __init__(self, key=None, models=None, timeout=DEFAULT_TIMEOUT, opener=None, base=OPENROUTER_BASE):
        self.key = (key if key is not None else openrouter_key()).strip()
        self.models = tuple(models or free_models())
        self.timeout = timeout
        self.base = base.rstrip('/')
        self.opener = opener or urllib.request.urlopen
        self.disabled_reason = None

    def available(self):
        if not self.key:
            return False, 'no OpenRouter key is configured'
        if self.disabled_reason:
            return False, self.disabled_reason
        return True, ''

    def http(self, url, body=None, headers=None):
        request = urllib.request.Request(url, body, headers or {})
        return self.opener(request, timeout=self.timeout)

    def catalogue(self):
        """The public model list. No key is needed to read it."""
        with self.http(self.base + '/models', headers={'Accept': 'application/json'}) as response:
            data = json.loads(response.read(2000000))
        rows = data.get('data') if isinstance(data, dict) else data
        return [row for row in (rows or []) if isinstance(row, dict) and row.get('id')]

    def complete(self, system, user, schema, max_tokens=1100):
        available, reason = self.available()
        if not available:
            raise ProviderUnavailable(reason)
        last_error = None
        attempts = 0
        for model in self.models:
            for attempt in range(MAX_ATTEMPTS_PER_MODEL):
                attempts += 1
                began = time.monotonic()
                payload = {'model': model, 'temperature': 0, 'max_tokens': max_tokens,
                           'messages': [{'role': 'system', 'content': system},
                                        {'role': 'user', 'content': user}],
                           'response_format': {'type': 'json_schema',
                                               'json_schema': {'name': 'plan', 'strict': True, 'schema': schema}},
                           'provider': {'require_parameters': True}}
                headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key,
                           'HTTP-Referer': 'http://127.0.0.1:8790', 'X-Title': 'WeatherGPT local prototype'}
                try:
                    with self.http(self.base + '/chat/completions', json.dumps(payload).encode(), headers) as response:
                        data = json.loads(response.read(400000))
                        if not isinstance(data, dict) or not data.get('choices'):
                            raise ProviderUnavailable('The model provider returned no completion. Try again or switch model.')
                except urllib.error.HTTPError as error:
                    detail = ''
                    try:
                        detail = (json.loads(error.read(4000)) or {}).get('error', {}).get('message', '')
                    except Exception:  # noqa: BLE001 - the status is what matters
                        detail = ''
                    if error.code in (401, 403):
                        self.disabled_reason = ('the OpenRouter key was refused (HTTP ' + str(error.code) + ')')
                        raise ProviderUnavailable(self.disabled_reason) from error
                    if error.code in (402, 404):
                        last_error = 'model ' + model + ' unavailable (HTTP ' + str(error.code) + ') ' + str(detail)[:80]
                        break
                    last_error = 'HTTP ' + str(error.code) + ' ' + str(detail)[:80]
                    if error.code == 429 or error.code >= 500:
                        time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                        continue
                    break
                except (urllib.error.URLError, OSError, ValueError) as error:
                    last_error = type(error).__name__ + ' ' + str(error)[:80]
                    continue
                latency = round((time.monotonic() - began) * 1000)
                content = ((data.get('choices') or [{}])[0].get('message') or {}).get('content', '')
                usage = data.get('usage') or {}
                try:
                    parsed = extract_json(content)
                except ProviderUnavailable as error:
                    last_error = str(error) + ' from ' + model
                    continue
                return parsed, {'provider': self.name, 'model': model, 'attempts': attempts,
                                'latency_ms': latency, 'input_tokens': usage.get('prompt_tokens'),
                                'output_tokens': usage.get('completion_tokens'),
                                'route': data.get('provider')}
        raise ProviderUnavailable('OpenRouter could not answer: ' + str(last_error or 'no model was tried'))


class ModelRouter:
    """Try the rule planner, then each provider in order, recording every attempt."""

    def __init__(self, clients=None, rules=True):
        self.clients = list(clients or default_clients())
        self.rules = rules
        self.trace = []

    def describe(self):
        rows = []
        for client in self.clients:
            available, reason = True, ''
            if hasattr(client, 'available'):
                available, reason = client.available()
            rows.append({'provider': client.name, 'model': getattr(client, 'model', None),
                         'models': list(getattr(client, 'models', ()) or []),
                         'available': available, 'reason': reason})
        return rows

    def complete(self, system, user, schema, max_tokens=1100):
        """Ask each provider in order; the first parsed reply wins, with its trace."""
        errors = []
        for client in self.clients:
            available, reason = (client.available() if hasattr(client, 'available') else (True, ''))
            if not available:
                errors.append(client.name + ': ' + reason)
                continue
            try:
                data, meta = client.complete(system, user, schema, max_tokens=max_tokens)
                meta = dict(meta or {})
                meta.setdefault('provider', client.name)
                meta['failover'] = list(errors)
                self.trace.append(meta)
                return data, meta
            except ProviderUnavailable as error:
                errors.append(client.name + ': ' + str(error))
        raise ProviderUnavailable('No model provider could answer. ' + ' | '.join(errors))

    def plan(self, question, now, history):
        """Rules first, then providers. The rule path needs nothing and says so."""
        from .language import interpret_plan
        from .rule_planner import rule_request
        if self.rules:
            seed = rule_request(question, now, history)
            if seed is not None:
                try:
                    plan, meta = interpret_plan(None, question, now, history, seed=seed)
                    meta = dict(meta or {})
                    meta.update(provider='deterministic_rules', model=RULE_MODEL, attempts=0, latency_ms=0,
                                failover=[])
                    self.trace.append(meta)
                    return plan, meta
                except (SourceError, TypeError, KeyError):
                    pass
        try:
            return interpret_plan(self.complete, question, now, history)
        except ProviderUnavailable as error:
            raise SourceError('The question could not be interpreted: ' + str(error)) from error


class DeterministicClient:
    """The floor: no schema completions, but the rule planner always exists."""

    name = 'deterministic'
    model = RULE_MODEL


def default_clients():
    clients = []
    try:
        clients.append(OllamaClient())
    except ValueError:
        pass
    if openrouter_key():
        clients.append(OpenRouterClient())
    return clients


def default_model():
    """The engine's default: rules plus whatever providers this machine has."""
    return ModelRouter()
