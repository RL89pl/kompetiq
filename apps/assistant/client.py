"""Warstwa dostępu do modeli językowych — niezależna od dostawcy.

Dostawcę wybiera konfiguracja (ASSISTANT_PROVIDER):
- ``openai_compat`` — dowolny serwer zgodny z OpenAI Chat Completions: Groq, Google Gemini (endpoint
  zgodny z OpenAI), Mistral, OpenRouter, a także modele uruchomione u siebie przez vLLM / Ollama
  (np. PLLuM, Bielik). Wymaga LLM_BASE_URL, LLM_MODEL i zwykle LLM_API_KEY.
- ``anthropic`` — Claude API (ANTHROPIC_API_KEY).

Każdy dostawca udostępnia dwie operacje: odpowiedź ustrukturyzowaną (walidowaną schematem Pydantic)
oraz odpowiedź na podstawie dokumentów z identyfikacją źródeł.
"""
import json
import logging
import re
import time
from dataclasses import dataclass, field
from functools import lru_cache

from django.conf import settings
from pydantic import ValidationError

log = logging.getLogger(__name__)

FALLBACK_BETA = 'server-side-fallback-2026-07-01'


class AssistantError(Exception):
    status = 502
    public_message = 'Asystent AI jest chwilowo niedostępny. Spróbuj ponownie za chwilę.'


class AssistantInputError(AssistantError):
    status = 400


class AssistantDisabled(AssistantError):
    status = 503
    public_message = 'Asystent AI nie jest skonfigurowany. Administrator musi wskazać dostawcę modelu (ASSISTANT_PROVIDER).'


class AssistantBusy(AssistantError):
    status = 429
    public_message = 'Asystent AI jest przeciążony lub wyczerpano limit zapytań. Spróbuj ponownie za minutę.'


class AssistantRefused(AssistantError):
    status = 422
    public_message = 'Asystent odmówił odpowiedzi na to zapytanie. Przeformułuj treść.'


@dataclass
class LLMResult:
    parsed: object = None
    text: str = ''
    citations: list = field(default_factory=list)
    model: str = ''
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    duration_ms: int = 0


class LLMProvider:
    name = 'base'

    def structured(self, *, system, prompt, schema, effort='medium', max_tokens=16000) -> LLMResult:
        raise NotImplementedError

    def answer_with_citations(self, *, system, prompt, documents, history=None, effort='medium',
                              max_tokens=8000) -> LLMResult:
        """documents: [{'title', 'text'}]; history: [{'role': 'user'|'assistant', 'content': str}]"""
        raise NotImplementedError


# --- Claude -----------------------------------------------------------------------------------------------

class AnthropicProvider(LLMProvider):
    name = 'anthropic'

    def __init__(self, api_key, model):
        import anthropic
        self.anthropic = anthropic
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=120.0)
        self.model = model

    @staticmethod
    def _system_blocks(system):
        # Stały prefiks (zasady + model kompetencji) — oznaczony do cache'owania.
        return [{'type': 'text', 'text': s} for s in system[:-1]] + [
            {'type': 'text', 'text': system[-1], 'cache_control': {'type': 'ephemeral'}}]

    def _call(self, fn, **kwargs):
        a = self.anthropic
        t0 = time.monotonic()
        try:
            resp = fn(model=self.model, betas=[FALLBACK_BETA], fallbacks='default', **kwargs)
        except a.RateLimitError as e:
            log.warning('Claude rate limit: %s', e)
            raise AssistantBusy() from e
        except a.APIStatusError as e:
            log.error('Claude API error %s: %s', e.status_code, e)
            raise AssistantError() from e
        except a.APIConnectionError as e:
            log.error('Claude connection error: %s', e)
            raise AssistantError() from e
        if resp.stop_reason == 'refusal':
            raise AssistantRefused()
        if resp.stop_reason == 'max_tokens':
            raise AssistantError('Odpowiedź została ucięta (max_tokens).')
        u = resp.usage
        return resp, LLMResult(
            model=resp.model, input_tokens=u.input_tokens or 0, output_tokens=u.output_tokens or 0,
            cache_read_tokens=getattr(u, 'cache_read_input_tokens', 0) or 0,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    def structured(self, *, system, prompt, schema, effort='medium', max_tokens=16000):
        resp, result = self._call(
            self.client.beta.messages.parse,
            max_tokens=max_tokens,
            system=self._system_blocks(system),
            messages=[{'role': 'user', 'content': prompt}],
            output_format=schema,
            output_config={'effort': effort},
        )
        if resp.parsed_output is None:
            raise AssistantError('Nie udało się odczytać odpowiedzi asystenta.')
        result.parsed = resp.parsed_output
        return result

    def answer_with_citations(self, *, system, prompt, documents, history=None, effort='medium', max_tokens=8000):
        content = [
            {'type': 'document', 'source': {'type': 'text', 'media_type': 'text/plain', 'data': d['text']},
             'title': d['title'], 'citations': {'enabled': True}}
            for d in documents
        ] + [{'type': 'text', 'text': prompt}]
        messages = [{'role': h['role'], 'content': h['content']} for h in (history or [])]
        messages.append({'role': 'user', 'content': content})
        resp, result = self._call(
            self.client.beta.messages.create,
            max_tokens=max_tokens,
            system=self._system_blocks(system),
            messages=messages,
            output_config={'effort': effort},
        )
        parts, cites = [], []
        for block in resp.content:
            if block.type != 'text':
                continue
            parts.append(block.text)
            for c in getattr(block, 'citations', None) or []:
                cites.append({'document_title': getattr(c, 'document_title', ''),
                              'cited_text': getattr(c, 'cited_text', ''),
                              'document_index': getattr(c, 'document_index', None)})
        result.text = ''.join(parts).strip()
        result.citations = cites
        return result


# --- serwery zgodne z OpenAI (Groq, Gemini, Mistral, OpenRouter, vLLM/PLLuM, Ollama/Bielik) ----------------

FENCE = re.compile(r'^\s*```(?:json)?\s*|\s*```\s*$', re.S)
CITE = re.compile(r'\[(\d{1,2})\]')


def _extract_json(text):
    text = FENCE.sub('', text or '').strip()
    if not text.startswith('{'):
        start, end = text.find('{'), text.rfind('}')
        if start != -1 and end > start:
            text = text[start:end + 1]
    return text


class OpenAICompatibleProvider(LLMProvider):
    name = 'openai_compat'

    def __init__(self, base_url, api_key, model, json_mode='json_object', timeout=120.0):
        import openai
        self.openai = openai
        self.client = openai.OpenAI(base_url=base_url, api_key=api_key or 'brak-klucza', timeout=timeout,
                                    max_retries=2)
        self.model = model
        self.json_mode = json_mode

    def _complete(self, messages, *, max_tokens, response_format=None):
        o = self.openai
        kwargs = {'model': self.model, 'messages': messages, 'max_tokens': max_tokens, 'temperature': 0.2}
        if response_format:
            kwargs['response_format'] = response_format
        t0 = time.monotonic()
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except o.RateLimitError as e:
            log.warning('LLM rate limit: %s', e)
            raise AssistantBusy() from e
        except o.APIStatusError as e:
            log.error('LLM API error %s: %s', e.status_code, e)
            raise AssistantError() from e
        except o.APIConnectionError as e:
            log.error('LLM connection error: %s', e)
            raise AssistantError() from e
        choice = resp.choices[0]
        if choice.finish_reason == 'content_filter':
            raise AssistantRefused()
        if choice.finish_reason == 'length':
            raise AssistantError('Odpowiedź została ucięta (limit długości).')
        u = resp.usage
        return (choice.message.content or ''), LLMResult(
            model=resp.model or self.model,
            input_tokens=getattr(u, 'prompt_tokens', 0) or 0,
            output_tokens=getattr(u, 'completion_tokens', 0) or 0,
            duration_ms=int((time.monotonic() - t0) * 1000),
        )

    def _response_format(self, schema):
        if self.json_mode == 'json_schema':
            return {'type': 'json_schema',
                    'json_schema': {'name': schema.__name__, 'schema': schema.model_json_schema()}}
        if self.json_mode == 'json_object':
            return {'type': 'json_object'}
        return None

    def structured(self, *, system, prompt, schema, effort='medium', max_tokens=16000):
        max_tokens = min(max_tokens, settings.LLM_MAX_TOKENS)
        schema_text = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        messages = [
            {'role': 'system', 'content': '\n\n'.join(system)},
            {'role': 'user', 'content': (
                f'{prompt}\n\nOdpowiedz WYŁĄCZNIE jednym obiektem JSON zgodnym z tym schematem JSON '
                f'(bez komentarzy i bez bloku kodu):\n{schema_text}')},
        ]
        total = LLMResult()
        for attempt in range(2):
            text, res = self._complete(messages, max_tokens=max_tokens, response_format=self._response_format(schema))
            total.model = res.model
            total.input_tokens += res.input_tokens
            total.output_tokens += res.output_tokens
            total.duration_ms += res.duration_ms
            try:
                total.parsed = schema.model_validate_json(_extract_json(text))
                return total
            except ValidationError as e:
                log.warning('Niepoprawny JSON od modelu (próba %s): %s', attempt + 1, e)
                messages += [{'role': 'assistant', 'content': text},
                             {'role': 'user', 'content': f'Odpowiedź nie jest zgodna ze schematem: {e.errors()[:5]}. '
                                                         'Zwróć poprawiony, kompletny obiekt JSON.'}]
        raise AssistantError('Model zwrócił odpowiedź w nieprawidłowym formacie.')

    def answer_with_citations(self, *, system, prompt, documents, history=None, effort='medium', max_tokens=8000):
        max_tokens = min(max_tokens, settings.LLM_MAX_TOKENS)
        sources = '\n\n'.join(f'[{i}] {d["title"]}\n{d["text"]}' for i, d in enumerate(documents, start=1))
        user = (f'ŹRÓDŁA (numerowane):\n<zrodla>\n{sources}\n</zrodla>\n\n{prompt}\n\n'
                'Po każdym zdaniu opartym na źródle wskaż jego numer w nawiasie kwadratowym, np. [2]. '
                'Nie powołuj się na źródła spoza listy.')
        messages = [{'role': 'system', 'content': '\n\n'.join(system)}]
        messages += [{'role': h['role'], 'content': h['content']} for h in (history or [])]
        messages.append({'role': 'user', 'content': user})
        text, result = self._complete(messages, max_tokens=max_tokens)
        cites, seen = [], set()
        for m in CITE.finditer(text):
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(documents) and idx not in seen:
                seen.add(idx)
                cites.append({'document_title': documents[idx]['title'],
                              'cited_text': documents[idx]['text'][:280].strip() + '…',
                              'document_index': idx})
        result.text = text.strip()
        result.citations = cites
        return result


# --- wybór dostawcy ------------------------------------------------------------------------------------------

_override = None


def set_provider(provider):
    """Do testów: podmiana dostawcy."""
    global _override
    _override = provider


@lru_cache(maxsize=4)
def _build(provider, model, base_url, json_mode):
    if provider == 'anthropic':
        return AnthropicProvider(settings.ANTHROPIC_API_KEY, model)
    return OpenAICompatibleProvider(base_url, settings.LLM_API_KEY, model, json_mode, timeout=settings.LLM_TIMEOUT)


def provider_info():
    p = settings.ASSISTANT_PROVIDER
    if p == 'anthropic':
        return {'provider': p, 'model': settings.ASSISTANT_MODEL, 'enabled': bool(settings.ANTHROPIC_API_KEY)}
    if p == 'openai_compat':
        url = settings.LLM_BASE_URL or ''
        internal = any(h in url for h in ('://127.0.0.1', '://localhost', '://llm:', '://host.docker.internal'))
        ok = bool(url and settings.LLM_MODEL and (settings.LLM_API_KEY or internal))
        return {'provider': p, 'model': settings.LLM_MODEL, 'enabled': ok}
    return {'provider': '', 'model': '', 'enabled': False}


def get_provider() -> LLMProvider:
    if _override is not None:
        return _override
    info = provider_info()
    if not settings.ASSISTANT_ENABLED or not info['enabled']:
        raise AssistantDisabled()
    if info['provider'] == 'anthropic':
        return _build('anthropic', settings.ASSISTANT_MODEL, '', '')
    return _build('openai_compat', settings.LLM_MODEL, settings.LLM_BASE_URL, settings.LLM_JSON_MODE)
