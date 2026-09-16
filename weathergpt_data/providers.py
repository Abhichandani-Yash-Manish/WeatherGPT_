"""Model access: one interface, three providers, a recorded choice.

The engine asks for a structured completion and gets back parsed data plus a trace of who
produced it. Providers are an enhancement, never the floor: the rule planner answers the
core problem-statement shapes with no model at all, Ollama answers locally, and OpenRouter
answers from a curated free-model pool when a key is configured in local backend
configuration. A paid OpenRouter id is refused with a recorded reason, never routed: this
workspace must not be able to bill an account by configuration accident.

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
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .transport import SourceError, stamp

ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG = ROOT / 'data' / 'runtime' / 'model-config.json'
FREE_MODEL_REGISTRY = ROOT / 'data' / 'registry' / 'openrouter-free-models.json'
OPENROUTER_BASE = 'https://openrouter.ai/api/v1'
OPENROUTER_MODELS_URL = OPENROUTER_BASE + '/models'
OPENROUTER_CHAT_URL = OPENROUTER_BASE + '/chat/completions'
# DeepSeek's OpenAI-compatible endpoint. It accepts a JSON object reply, not a JSON schema on the
# wire, so the schema travels in the prompt and the reply is parsed and checked exactly as the
# OpenRouter client's is. It is a paid endpoint billed to the key configured on this machine: the
# reader chose it on 16 September 2026, and every call records its model, tokens and latency.
DEEPSEEK_BASE = 'https://api.deepseek.com'
DEEPSEEK_MODELS = ('deepseek-chat',)
# Free-tier ids this workspace has itself observed in the OpenRouter catalogue, most recent
# observation first. The curated ranking in FREE_MODEL_REGISTRY is the routing order and names
# more; this tuple is the floor used only when that registry is missing. Re-measured on
# 15 September 2026: the earlier floor named ids the catalogue no longer publishes, so a
# fallback built on them would have failed over to the local model every time.
DEFAULT_FREE_MODELS = (
    'nvidia/nemotron-3-super-120b-a12b:free',
    'nex-agi/nex-n2.5-pro:free',
    'google/gemma-4-31b-it:free',
    'dots-studio/dots-3-note-preview:free',
    'nex-agi/nex-n2.5-mini:free',
)
PAID_MODEL_REFUSAL = 'refused: this id does not end in :free, and a paid id could bill the account'
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


def deepseek_key():
    """The DeepSeek key from the environment first, then local configuration."""
    key = os.getenv('DEEPSEEK_API_KEY') or local_config().get('deepseek_api_key') or ''
    return str(key).strip()


def key_source():
    if os.getenv('OPENROUTER_API_KEY'):
        return 'environment OPENROUTER_API_KEY'
    if str(local_config().get('openrouter_api_key') or '').strip():
        return str(LOCAL_CONFIG.relative_to(ROOT))
    return 'not configured'


def is_free_model(model_id):
    """Only ids OpenRouter publishes on its free tier. Anything else is refused, never routed."""
    return str(model_id or '').strip().endswith(':free')


def free_model_ranking(path=None):
    """The curated free-model ranking, most capable first, from the registry or the observed floor.

    The registry is the editable order and the workspace's own catalogue observations are the
    fallback; a registry that does not parse or names no free id is treated as missing rather
    than silently replaced by a shorter list.
    """
    path = Path(path or FREE_MODEL_REGISTRY)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8')) or {}
        except ValueError:
            data = {}
        data = data if isinstance(data, dict) else {}
        ranked = []
        for entry in data.get('models') or []:
            model_id = str((entry or {}).get('model_id') or '').strip() if isinstance(entry, dict) else ''
            if is_free_model(model_id) and model_id not in ranked:
                ranked.append(model_id)
        if ranked:
            return tuple(ranked)
    return DEFAULT_FREE_MODELS


def configured_models():
    """The ids this machine asks for explicitly, from the environment or local configuration."""
    configured = os.getenv('WEATHERGPT_MODELS') or local_config().get('models')
    if isinstance(configured, str):
        configured = [item.strip() for item in configured.split(',') if item.strip()]
    return tuple(str(item).strip() for item in (configured or ()) if str(item).strip())


def free_model_choices(ranking=None, configured=None):
    """The routing order, the curated ranking and every id refused because it is not free.

    A configured id that does not end in ':free' is skipped and recorded in 'refused' with a
    reason. Skipping is deliberate: one bad configuration entry must not remove the provider,
    and no caller can then reach a paid model through this function or through free_models().
    """
    ranked = free_model_ranking() if ranking is None else tuple(ranking)
    extra = configured_models() if configured is None else tuple(configured)
    accepted, refused = [], []
    for model_id in [str(item or '').strip() for item in tuple(ranked) + tuple(extra)]:
        if not model_id:
            continue
        if not is_free_model(model_id):
            refused.append({'model_id': model_id, 'reason': PAID_MODEL_REFUSAL})
        elif model_id not in accepted:
            accepted.append(model_id)
    return {'routing_order': tuple(accepted), 'ranking': tuple(str(item).strip() for item in ranked),
            'configured': tuple(extra), 'refused': tuple(refused)}


def free_models():
    """The router's model order: the curated free ranking first, then any configured extra.

    A configured id that does not end in ':free' is skipped with a reason recorded by
    free_model_choices()['refused'] rather than raising, so configuration cannot take the
    provider away and cannot put a billable id in front of a caller.
    """
    return free_model_choices()['routing_order']


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


def route_failure(data):
    """A reply body that carries no usable choice, named rather than collapsed into one message.

    OpenRouter can answer HTTP 200 and put an upstream failure in the body
    (``{"error": {"message": ..., "code": ..., "metadata": {"error_type": ...}}}``). Measured
    15 September 2026: the highest-ranked free model answered that way with "Upstream error from
    Nvidia: Service temporarily overloaded", which this client used to report as a generic missing
    completion and then abandon the provider instead of trying the next free model in the order.
    """
    error = data.get('error') if isinstance(data, dict) else None
    if isinstance(error, dict) and error:
        code = error.get('code')
        metadata = error.get('metadata') if isinstance(error.get('metadata'), dict) else {}
        detail = str(error.get('message') or metadata.get('error_type') or 'the provider reported an error').strip()
        return 'upstream error' + ((' ' + str(code)) if code else '') + ': ' + (detail or 'unnamed')[:160]
    if not isinstance(data, dict) or not data.get('choices'):
        return 'the provider returned no completion'
    return ''


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

    def catalogue(self):
        """The installed model names, read from the local /api/tags endpoint.

        Service reachability and model availability are different facts: a reachable
        service that does not carry the configured model is reported unavailable by
        ``available`` with the model named, rather than being treated as a usable
        provider. No secret is read or returned.
        """
        request = urllib.request.Request(self.base + '/api/tags', headers={'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=min(2, self.timeout)) as response:
                data = json.loads(response.read(200000))
        except (urllib.error.URLError, OSError, ValueError) as error:
            raise ProviderUnavailable('The local model service did not answer: ' + type(error).__name__) from error
        rows = data.get('models') if isinstance(data, dict) else data
        return [str(row.get('name')) for row in (rows or []) if isinstance(row, dict) and row.get('name')]

    def available(self):
        """True only when the service answers and the configured model is installed.

        Returns ``(available, reason)`` like the OpenRouter client, so the router can
        report a missing model by name instead of attempting an inference that cannot
        succeed. Previously the startup check called this method and it did not exist
        (measured 15 September 2026).
        """
        try:
            names = self.catalogue()
        except ProviderUnavailable as error:
            return False, str(error)
        if self.model not in names:
            installed = ', '.join(names[:5]) if names else 'none reported'
            return False, ('the local service is reachable but the configured model ' + str(self.model) +
                           ' is not installed (installed: ' + installed + '); set WEATHERGPT_MODEL or run '
                           '"ollama pull ' + str(self.model) + '"')
        return True, ''

    def complete(self, system, user, schema, max_tokens=1100, timeout=None):
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
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
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
    """OpenRouter over HTTPS, restricted to :free models and to the ones a caller allows.

    Every failure mode is named rather than retried blindly: a refused key disables the
    provider for the process, a model-level refusal moves to the next model, and a rate limit
    or transport error is retried once with a short backoff before moving on.

    A model id that does not end in ':free' is never placed in the request list, whatever the
    caller asked for: it is recorded in refused_models, and a client left with no free model
    reports itself unavailable instead of falling back to a billable id.
    """

    name = 'openrouter'

    def __init__(self, key=None, models=None, timeout=DEFAULT_TIMEOUT, opener=None, base=OPENROUTER_BASE):
        self.key = (key if key is not None else openrouter_key()).strip()
        choices = free_model_choices(ranking=tuple(models), configured=()) if models is not None else free_model_choices()
        self.models = choices['routing_order']
        self.refused_models = choices['refused']
        self.timeout = timeout
        self.base = base.rstrip('/')
        self.opener = opener or urllib.request.urlopen
        self.disabled_reason = None
        if not self.models:
            self.disabled_reason = ('no :free model is configured, and a paid model is never routed')

    def available(self):
        if not self.key:
            return False, 'no OpenRouter key is configured'
        if self.disabled_reason:
            return False, self.disabled_reason
        return True, ''

    def http(self, url, body=None, headers=None, timeout=None):
        request = urllib.request.Request(url, body, headers or {})
        return self.opener(request, timeout=timeout or self.timeout)

    def catalogue(self, with_key=False):
        """The public model list. No key is needed to read it; with_key sends the configured one."""
        headers = {'Accept': 'application/json'}
        if with_key and self.key:
            headers['Authorization'] = 'Bearer ' + self.key
        with self.http(self.base + '/models', headers=headers) as response:
            data = json.loads(response.read(2000000))
        rows = data.get('data') if isinstance(data, dict) else data
        return [row for row in (rows or []) if isinstance(row, dict) and row.get('id')]

    def complete(self, system, user, schema, max_tokens=1100, timeout=None):
        """One bounded call. A per-call timeout lets a composition step keep its own budget."""
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
                    with self.http(self.base + '/chat/completions', json.dumps(payload).encode(), headers,
                                   timeout=timeout) as response:
                        data = json.loads(response.read(400000))
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
                failure = route_failure(data)
                if failure:
                    # A body-level failure belongs to this model, not to the provider: retrying the
                    # same id once and then moving down the free order is what makes failover real.
                    last_error = model + ' ' + failure
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
        self.last_failure = {'provider': self.name, 'reason': str(last_error or 'no model was tried')[:300],
                             'at_utc': stamp(datetime.now(timezone.utc))}
        raise ProviderUnavailable('OpenRouter could not answer: ' + str(last_error or 'no model was tried'))


# The whole-step budget when a caller does not set one: a refusal from a free endpoint must reach
# the reader as an honest error in a reasonable time, not as a two-minute wait through retries.
PROVIDER_BUDGET_SECONDS=float(os.getenv('WEATHERGPT_PROVIDER_BUDGET') or 45.0)
PLANNER_POLICY_ENV='WEATHERGPT_PLANNER'

def planner_policy():
    """Which planner answers a turn: the model by default, the deterministic rules only on request.

    The rules floor is never a silent substitute for a model call. An offline machine or a benchmark
    can ask for it explicitly, and the trace records that it was asked for.
    """
    policy=str(os.getenv(PLANNER_POLICY_ENV) or local_config().get('planner_policy') or 'model').strip().lower()
    return policy if policy in {'model','rules'} else 'model'


class DeepSeekClient:
    """DeepSeek in JSON-object mode: the schema travels in the prompt, the reply is parsed as JSON.

    Paid and billed to the configured key, so every reply records its model, its tokens and its
    latency. An invalid key disables the client for this process rather than retrying it, a missing
    balance is named as such, and a rate limit or a server error is retried once before the router
    moves on.
    """

    name = 'deepseek'

    def __init__(self, key=None, models=None, timeout=DEFAULT_TIMEOUT, opener=None, base=DEEPSEEK_BASE):
        self.key = (key if key is not None else deepseek_key()).strip()
        self.models = tuple(models or DEEPSEEK_MODELS)
        self.timeout = timeout
        self.opener = opener or urllib.request.urlopen
        self.base = base.rstrip('/')
        self.disabled_reason = ''

    def available(self):
        if not self.key:
            return False, 'no DeepSeek key is configured'
        if self.disabled_reason:
            return False, self.disabled_reason
        return True, ''

    def http(self, url, body=None, headers=None, timeout=None):
        request = urllib.request.Request(url, body, headers or {})
        return self.opener(request, timeout=timeout or self.timeout)

    def complete(self, system, user, schema, max_tokens=1100, timeout=None):
        available, reason = self.available()
        if not available:
            raise ProviderUnavailable(reason)
        instruction = ('Return only one JSON object, and nothing else, that validates against this JSON '
                       'schema: ' + json.dumps(schema, ensure_ascii=False))
        last_error = None
        attempts = 0
        for model in self.models:
            for attempt in range(MAX_ATTEMPTS_PER_MODEL):
                attempts += 1
                began = time.monotonic()
                payload = {'model': model, 'temperature': 0, 'max_tokens': max_tokens,
                           'response_format': {'type': 'json_object'},
                           'messages': [{'role': 'system', 'content': system + ' ' + instruction},
                                        {'role': 'user', 'content': user}]}
                headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key}
                try:
                    with self.http(self.base + '/chat/completions', json.dumps(payload).encode(), headers,
                                   timeout=timeout) as response:
                        data = json.loads(response.read(400000))
                except urllib.error.HTTPError as error:
                    detail = ''
                    try:
                        detail = (json.loads(error.read(4000)) or {}).get('error', {}).get('message', '')
                    except Exception:  # noqa: BLE001 - the status is what matters
                        detail = ''
                    if error.code in (401, 403):
                        self.disabled_reason = 'the DeepSeek key was refused (HTTP ' + str(error.code) + ')'
                        raise ProviderUnavailable(self.disabled_reason) from error
                    if error.code == 402:
                        self.disabled_reason = 'the DeepSeek account has no balance for this call'
                        raise ProviderUnavailable(self.disabled_reason) from error
                    last_error = 'HTTP ' + str(error.code) + ' ' + str(detail)[:120]
                    if error.code == 429 or error.code >= 500:
                        time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
                        continue
                    break
                except (urllib.error.URLError, OSError, ValueError) as error:
                    last_error = type(error).__name__ + ' ' + str(error)[:100]
                    continue
                failure = route_failure(data)
                if failure:
                    last_error = model + ': ' + failure
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
                                'cache_hit_tokens': usage.get('prompt_cache_hit_tokens')}
        self.last_failure = {'provider': self.name, 'reason': str(last_error or 'no model was tried')[:300],
                             'at_utc': stamp(datetime.now(timezone.utc))}
        raise ProviderUnavailable('DeepSeek could not answer: ' + str(last_error or 'no model was tried'))


class ModelRouter:
    """Let the model plan the turn, or the deterministic rules when the policy asks for them.

    A client presenting itself as OpenRouter while holding a non-free model is refused at
    construction: the router is the last place before the network, so the paid-id guard is
    checked here as well as inside the client.
    """

    def __init__(self, clients=None, rules=True, policy=None, router=None):
        self.policy = policy or planner_policy()
        self.provider_policy = provider_policy()
        from .chat_router import router_enabled
        self.router = router_enabled() if router is None else bool(router)
        # The last time every provider failed, with the reason, so a reader can see why a turn was
        # refused rather than guessing from a single error message.
        self.last_failure = None
        self.clients = []
        for client in clients or default_clients():
            if getattr(client, 'name', '') == OpenRouterClient.name:
                paid = [str(model) for model in (getattr(client, 'models', ()) or ()) if not is_free_model(model)]
                if paid:
                    raise ValueError('ModelRouter refuses a paid OpenRouter model: ' + ', '.join(paid))
            self.clients.append(client)
        self.rules = rules
        self.trace = []

    def state(self):
        """The provider policy, the planner policy, the first look, availability and the last failure."""
        return {'provider_policy': self.provider_policy, 'planner_policy': self.policy,
                'chat_router': self.router, 'providers': self.describe(),
                'last_failure': self.last_failure}

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

    def complete(self, system, user, schema, max_tokens=1100, timeout=None):
        """Ask each provider in order; the first parsed reply wins, with its trace.

        A timeout is the budget for the whole step, not for one attempt: a composition step that has
        spent it stops trying, because a slow tail on a free endpoint must not hold a turn that
        already has the retrieved facts to state. Without a timeout the clients keep their own.
        """
        errors = []
        began = time.monotonic()
        timeout = PROVIDER_BUDGET_SECONDS if timeout is None else timeout

        def remaining():
            return timeout - (time.monotonic() - began)

        for client in self.clients:
            available, reason = (client.available() if hasattr(client, 'available') else (True, ''))
            if not available:
                errors.append(client.name + ': ' + reason)
                continue
            left = remaining()
            if left is not None and left <= 1.0:
                errors.append('the %.0f s budget for this step was spent before ' % timeout + client.name + ' answered')
                break
            try:
                try:
                    data, meta = client.complete(system, user, schema, max_tokens=max_tokens,
                                                 timeout=left if left is not None else None)
                except TypeError:
                    data, meta = client.complete(system, user, schema, max_tokens=max_tokens)
                meta = dict(meta or {})
                meta.setdefault('provider', client.name)
                meta['provider_policy'] = self.provider_policy
                meta['failover'] = list(errors)
                self.trace.append(meta)
                return data, meta
            except ProviderUnavailable as error:
                errors.append(client.name + ': ' + str(error))
                self.last_failure = {'provider': client.name, 'reason': str(error)[:300],
                                     'at_utc': stamp(datetime.now(timezone.utc))}
        self.last_failure = self.last_failure or {'provider': 'all', 'reason': ' | '.join(errors)[:300],
                                                 'at_utc': stamp(datetime.now(timezone.utc))}
        raise ProviderUnavailable('No model provider could answer. ' + ' | '.join(errors))

    def plan(self, question, now, history):
        """Plan a turn. The model plans by default; the rules plan only when the policy asks.

        A provider outage names every provider that was tried and is never quietly answered from the
        rules floor. The floor exists for an explicit offline policy, and the trace says which policy
        and which planner answered, so a reader never has to infer why an answer looks the way it does.
        """
        from .language import interpret_plan
        from .rule_planner import rule_request
        if self.policy == 'rules':
            if not self.rules:
                raise SourceError('This router has no rule planner and its policy is rules-only.')
            seed = rule_request(question, now, history)
            if seed is None:
                raise SourceError('The deterministic rules cannot read this question and this workspace '
                                  'is in rules-only mode (' + PLANNER_POLICY_ENV + '=rules).')
            plan, meta = interpret_plan(None, question, now, history, seed=seed)
            meta = dict(meta or {})
            meta.update(provider='deterministic_rules', model=RULE_MODEL, planner_policy='rules',
                        attempts=0, latency_ms=0, failover=[])
            self.trace.append(meta)
            return plan, meta
        if self.router:
            from .chat_router import route
            try:
                routed = route(self, question, now, history)
            except (ProviderUnavailable, SourceError, OSError, TimeoutError, TypeError, KeyError, ValueError):
                # A first look that fails changes nothing: the full planner still owns the turn.
                routed = None
            if routed is not None:
                plan, meta = routed
                meta = dict(meta or {})
                meta['planner_policy'] = 'model'
                return plan, meta
        try:
            plan, meta = interpret_plan(self.complete, question, now, history)
        except ProviderUnavailable as error:
            raise SourceError('No model provider could answer: ' + str(error) +
                              ' The rules planner is not used as a silent substitute; set ' +
                              PLANNER_POLICY_ENV + '=rules to run this workspace offline.') from error
        meta = dict(meta or {})
        meta['planner_policy'] = 'model'
        return plan, meta


class DeterministicClient:
    """The floor: no schema completions, but the rule planner always exists."""

    name = 'deterministic'
    model = RULE_MODEL


PROVIDER_POLICY_ENV='WEATHERGPT_PROVIDERS'

def provider_policy():
    """Which providers may answer: the curated free cloud models, or the frozen local fallback.

    The reader chose the free cloud models on 16 September 2026 and froze everything else, so
    'cloud_free' is the default: only the curated free OpenRouter ids answer, and a provider outage is
    reported rather than quietly served by a different machine. 'local' is kept so an offline machine
    can still be diagnosed; it is not a fallback that runs by itself.
    """
    default='deepseek_first' if deepseek_key() else 'cloud_free'
    policy=str(os.getenv(PROVIDER_POLICY_ENV) or local_config().get('provider_policy') or default).strip().lower()
    return policy if policy in {'deepseek_first','deepseek','cloud_free','local'} else default


def default_clients():
    """The configured providers: the curated free cloud models, or the frozen local model on request.

    Free-cloud policy: OpenRouter only, with the curated free ids, ordered most capable first and
    failing over between them on any refusal. A planning failure never loses the turn while another
    free id can answer, and the failover is recorded in the trace. With no key configured there is no
    provider at all, which the planner reports rather than routing around.
    """
    policy=provider_policy()
    if policy=='local':
        try:
            return [OllamaClient()]
        except ValueError:
            return []
    if policy=='deepseek':
        return [DeepSeekClient()] if deepseek_key() else []
    if policy=='cloud_free':
        return [OpenRouterClient()] if openrouter_key() else []
    # deepseek_first: the endpoint the reader configured, then the free ids as failover. The
    # paid key answers when it is there, and a free model still carries the turn if it is not.
    clients=[]
    if deepseek_key():clients.append(DeepSeekClient())
    if openrouter_key():clients.append(OpenRouterClient())
    return clients


def default_model():
    """The engine's default: rules plus whatever providers this machine has."""
    return ModelRouter()
