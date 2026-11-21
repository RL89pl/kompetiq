"""Dostawca zgodny z OpenAI (Groq / Gemini / Mistral / vLLM-PLLuM) — na lokalnej atrapie serwera."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from apps.assistant import schemas
from apps.assistant.client import AssistantBusy, OpenAICompatibleProvider


class Server:
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        srv = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['content-length'])))
                srv.requests.append(body)
                code, content = srv.replies.pop(0)
                data = json.dumps({'id': 'x', 'object': 'chat.completion', 'created': 0, 'model': 'pllum-test',
                                   'choices': [{'index': 0, 'finish_reason': 'stop',
                                                'message': {'role': 'assistant', 'content': content}}],
                                   'usage': {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18}}
                                  if code == 200 else {'error': {'message': 'limit'}}).encode()
                self.send_response(code)
                self.send_header('content-type', 'application/json')
                self.send_header('content-length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.httpd = HTTPServer(('127.0.0.1', 0), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f'http://127.0.0.1:{self.httpd.server_port}/v1'

    def provider(self, **kw):
        p = OpenAICompatibleProvider(self.url, 'k', 'pllum-test', **kw)
        p.client = p.client.with_options(max_retries=0)
        return p


def test_structured_with_retry_on_invalid_json():
    good = json.dumps({'draft': 'Projekt', 'consistency_warnings': [], 'missing_points': []})
    s = Server([(200, 'To nie jest JSON'), (200, f'```json\n{good}\n```')])
    r = s.provider().structured(system=['zasady', 'model'], prompt='p', schema=schemas.JustificationDraft)
    assert r.parsed.draft == 'Projekt' and r.input_tokens == 22
    assert s.requests[0]['response_format'] == {'type': 'json_object'}
    assert s.requests[0]['messages'][0]['role'] == 'system' and 'zasady' in s.requests[0]['messages'][0]['content']
    assert len(s.requests[1]['messages']) == 4  # korekta po błędzie


def test_citations_parsed_from_numbers():
    s = Server([(200, 'Sprzeciw wnosi się w 7 dni [2]. Zob. też [9].')])
    r = s.provider().answer_with_citations(system=['s'], prompt='q', history=[{'role': 'user', 'content': 'wcześniej'}],
                                           documents=[{'title': 'A', 'text': 'aaa'}, {'title': 'B', 'text': 'sprzeciw 7 dni'}])
    assert [c['document_title'] for c in r.citations] == ['B']
    assert [m['role'] for m in s.requests[0]['messages']] == ['system', 'user', 'user']


def test_rate_limit_maps_to_busy():
    s = Server([(429, '')])
    with pytest.raises(AssistantBusy):
        s.provider().structured(system=['s'], prompt='p', schema=schemas.JustificationDraft)


def test_json_schema_mode():
    good = json.dumps({'draft': 'x', 'consistency_warnings': [], 'missing_points': []})
    s = Server([(200, good)])
    s.provider(json_mode='json_schema').structured(system=['s'], prompt='p', schema=schemas.JustificationDraft)
    assert s.requests[0]['response_format']['type'] == 'json_schema'
