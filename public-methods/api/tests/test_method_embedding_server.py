"""Contract tests for the bounded public-only method embedding server."""
import asyncio
import importlib.util
import json
from pathlib import Path
import unittest

PATH = Path(__file__).parents[1] / 'scripts' / 'method_embedding_server.py'
SPEC = importlib.util.spec_from_file_location('method_embedding_server', PATH)
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


class ValidationTests(unittest.TestCase):
    def test_query_prefix_and_document_no_prefix(self):
        raw = '제약을 고려한 실행 방법'
        texts, kind = server.validate_request({'texts': [raw], 'input_type': 'query'})
        self.assertEqual(texts, ['Instruct: ' + server.QUERY_INSTRUCTION + '\nQuery:' + raw])
        self.assertEqual(server.validate_request({'texts': [raw], 'input_type': 'document'})[0], [raw])

    def test_bge_has_no_query_prefix(self):
        self.assertEqual(server.validate_request({'texts': ['goal'], 'input_type': 'query'}, 'bge-m3')[0], ['goal'])

    def test_caps_and_instruction_drift_rejected(self):
        for payload in [
            {'texts': [], 'input_type': 'query'},
            {'texts': ['x'] * 9, 'input_type': 'document'},
            {'texts': ['x' * 6001], 'input_type': 'document'},
            {'texts': ['x'], 'input_type': 'other'},
            {'texts': ['x'], 'input_type': 'query', 'instruction': 'different'},
            {'texts': ['x'], 'input_type': 'document', 'instruction': server.QUERY_INSTRUCTION},
            {'texts': ['x'], 'input_type': 'query', 'model': 'untrusted'},
        ]:
            with self.subTest(payload=str(payload)[:30]), self.assertRaises(server.InputError):
                server.validate_request(payload)


class FakeEngine:
    family = 'qwen3'
    calls = 0
    actual_tokens = 0
    last_encode_ms = None
    def metadata(self):
        return {'model': server.QWEN_MODEL, 'revision': server.QWEN_REVISION,
                'dimensions': 2, 'normalized': True, 'embedding_spec': 'fake'}
    def embed(self, payload):
        return self.metadata() | {'embeddings': [[1.0, 0.0]]}


class ASGITests(unittest.IsolatedAsyncioTestCase):
    async def request(self, payload=None, body=None, headers=None, path='/embed', method='POST'):
        app = server.EmbeddingApp(FakeEngine())
        sent = []
        events = [{'type': 'http.request', 'body': json.dumps(payload).encode() if body is None else body, 'more_body': False}]
        async def receive():
            return events.pop(0)
        async def send(message):
            sent.append(message)
        await app({'type': 'http', 'path': path, 'method': method,
                   'headers': headers or [(b'content-type', b'application/json')]}, receive, send)
        app.executor.shutdown(wait=True)
        return sent[0]['status'], json.loads(sent[1]['body'])

    async def test_health_and_embed(self):
        status, result = await self.request(path='/health', method='GET')
        self.assertEqual(status, 200)
        self.assertEqual(result['revision'], server.QWEN_REVISION)
        status, result = await self.request({'texts': ['hello'], 'input_type': 'document'})
        self.assertEqual(status, 200)
        self.assertEqual(result['embeddings'], [[1.0, 0.0]])

    async def test_body_limits_and_invalid_json(self):
        self.assertEqual((await self.request(body=b'x' * 65537))[0], 413)
        self.assertEqual((await self.request(body=b'{bad'))[0], 422)
        self.assertEqual((await self.request(body=b'{}', headers=[(b'content-type', b'text/plain')]))[0], 415)
        self.assertEqual((await self.request(body=b'{}', headers=[(b'content-type', b'application/json'), (b'content-length', b'65537')]))[0], 413)


if __name__ == '__main__':
    unittest.main()
