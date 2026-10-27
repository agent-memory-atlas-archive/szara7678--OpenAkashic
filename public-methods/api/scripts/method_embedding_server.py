"""Bounded local CPU embedding service for sanitized public method text.

Weights and service state belong outside Git. Never use this endpoint for private
vault content. No request bodies or text are logged. The model is fixed per process.
"""
from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import ipaddress
import json
import math
import resource
import socket
import threading
import time
from pathlib import Path

QWEN_MODEL = 'Qwen/Qwen3-Embedding-0.6B'
QWEN_REVISION = '97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3'
BGE_MODEL = 'BAAI/bge-m3'
BGE_REVISION = '5617a9f61b028005a4858fdac845db406aefb181'
QUERY_INSTRUCTION = 'Given a situation and goal, retrieve reusable methods that help achieve the goal.'
MAX_BODY_BYTES = 65536
MAX_TEXTS = 8
MAX_TEXT_CHARS = 6000
MAX_TOKENS = 512
REQUEST_TIMEOUT_SECONDS = 30


class InputError(ValueError):
    pass


def validate_request(payload, family='qwen3'):
    if not isinstance(payload, dict) or set(payload) - {'texts', 'input_type', 'instruction'}:
        raise InputError('Expected texts, input_type, and optional instruction only')
    texts = payload.get('texts')
    if not isinstance(texts, list) or not 1 <= len(texts) <= MAX_TEXTS:
        raise InputError(f'texts must contain 1..{MAX_TEXTS} strings')
    if any(not isinstance(t, str) or not t.strip() or len(t) > MAX_TEXT_CHARS for t in texts):
        raise InputError(f'Each text must be nonempty and at most {MAX_TEXT_CHARS} characters')
    kind = payload.get('input_type')
    if kind not in ('query', 'document'):
        raise InputError('input_type must be query or document')
    instruction = payload.get('instruction')
    if instruction is not None and (family != 'qwen3' or kind != 'query' or instruction != QUERY_INSTRUCTION):
        raise InputError('instruction must match the fixed query instruction; documents use no instruction')
    if family == 'qwen3' and kind == 'query':
        texts = [f'Instruct: {QUERY_INSTRUCTION}\nQuery:{text}' for text in texts]
    return texts, kind


class EmbeddingEngine:
    def __init__(self, model_path, family='qwen3', threads=2):
        import torch
        from transformers import AutoModel, AutoTokenizer
        self.torch = torch
        self.family = family
        torch.set_num_threads(threads)
        torch.set_num_interop_threads(1)
        self.model_id = QWEN_MODEL if family == 'qwen3' else BGE_MODEL
        self.revision = QWEN_REVISION if family == 'qwen3' else BGE_REVISION
        self.spec = f'openakashic-methods-{family}-v1-{"lasttoken" if family == "qwen3" else "cls"}-l2-f32-max512'
        source = json.loads((Path(model_path) / 'source.json').read_text())
        if source != {'model': self.model_id, 'revision': self.revision}:
            raise RuntimeError('Model source manifest does not match the fixed revision')
        self.tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=False,
                                                       local_files_only=True, padding_side='left' if family == 'qwen3' else 'right')
        self.model = AutoModel.from_pretrained(str(model_path), trust_remote_code=False,
                                               local_files_only=True, dtype=torch.float32,
                                               attn_implementation='sdpa').to('cpu').eval()
        self.dimensions = int(self.model.config.hidden_size)
        self.threads = threads
        self.started = time.time()
        self.calls = 0
        self.actual_tokens = 0
        self.last_encode_ms = None
        self.lock = threading.Lock()

    def metadata(self):
        return {
            'model': self.model_id, 'revision': self.revision, 'dimensions': self.dimensions,
            'normalized': True, 'embedding_spec': self.spec,
            'preprocessing': {
                'query_instruction': QUERY_INSTRUCTION if self.family == 'qwen3' else None,
                'query_template': 'Instruct: {instruction}\nQuery:{text}' if self.family == 'qwen3' else '{text}',
                'document_template': '{text}', 'pooling': 'last_nonpadding_token' if self.family == 'qwen3' else 'cls',
                'padding_side': self.tokenizer.padding_side, 'add_special_tokens': True,
                'max_tokens_including_prompt_and_special_tokens': MAX_TOKENS,
                'truncation': 'reject', 'dtype': 'float32', 'device': 'cpu',
                'trust_remote_code': False,
            },
            'limits': {'max_texts': MAX_TEXTS, 'max_text_chars': MAX_TEXT_CHARS,
                       'max_body_bytes': MAX_BODY_BYTES, 'request_timeout_seconds': REQUEST_TIMEOUT_SECONDS,
                       'max_concurrent_inferences': 1, 'torch_threads': self.threads},
        }

    def embed(self, payload):
        texts, kind = validate_request(payload, self.family)
        batch = self.tokenizer(texts, padding=True, truncation=False, add_special_tokens=True, return_tensors='pt')
        counts = batch['attention_mask'].sum(dim=1).tolist()
        if max(counts) > MAX_TOKENS:
            raise InputError(f'Encoded input exceeds {MAX_TOKENS} tokens including prompt/special tokens; truncation is disabled')
        start = time.perf_counter()
        with self.torch.inference_mode():
            states = self.model(**batch).last_hidden_state
            vectors = states[:, -1] if self.family == 'qwen3' else states[:, 0]
            vectors = self.torch.nn.functional.normalize(vectors, p=2, dim=1)
        if not self.torch.isfinite(vectors).all().item():
            raise RuntimeError('Model returned nonfinite embedding')
        elapsed = (time.perf_counter() - start) * 1000
        self.calls += 1
        self.actual_tokens += int(sum(counts))
        self.last_encode_ms = round(elapsed, 3)
        return {k: v for k, v in self.metadata().items() if k not in ('limits', 'preprocessing')} | {
            'embeddings': vectors.tolist(), 'input_type': kind,
            'usage': {'actual_encoded_tokens': int(sum(counts)), 'encoded_tokens_per_text': counts,
                      'padded_tokens': int(batch['input_ids'].numel()), 'texts': len(texts),
                      'truncated': False, 'encode_ms': round(elapsed, 3)},
        }


class EmbeddingApp:
    def __init__(self, engine):
        self.engine = engine
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='public-embed')
        self.busy = False

    async def reply(self, send, status, value):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        await send({'type': 'http.response.start', 'status': status, 'headers': [
            (b'content-type', b'application/json; charset=utf-8'),
            (b'content-length', str(len(body)).encode()), (b'cache-control', b'no-store')]})
        await send({'type': 'http.response.body', 'body': body})

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    self.executor.shutdown(wait=False, cancel_futures=True)
                    await send({'type': 'lifespan.shutdown.complete'})
                    return
        if scope['type'] != 'http':
            return
        path, method = scope['path'], scope['method']
        if path == '/health' and method == 'GET':
            await self.reply(send, 200, self.engine.metadata() | {'status': 'ok', 'busy': self.busy,
                'metrics': {'calls': self.engine.calls, 'actual_encoded_tokens': self.engine.actual_tokens,
                            'last_encode_ms': self.engine.last_encode_ms,
                            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}})
            return
        if path != '/embed' or method != 'POST':
            await self.reply(send, 404, {'error': 'not_found'})
            return
        headers = dict(scope.get('headers', []))
        if headers.get(b'content-type', b'').split(b';')[0] != b'application/json':
            await self.reply(send, 415, {'error': 'content_type_must_be_application_json'})
            return
        try:
            size = int(headers.get(b'content-length', b'0'))
            if size < 0 or size > MAX_BODY_BYTES:
                await self.reply(send, 413, {'error': 'request_too_large'})
                return
        except ValueError:
            await self.reply(send, 400, {'error': 'invalid_content_length'})
            return
        body = bytearray()
        try:
            async with asyncio.timeout(5):
                while True:
                    message = await receive()
                    if message['type'] == 'http.disconnect':
                        return
                    body.extend(message.get('body', b''))
                    if len(body) > MAX_BODY_BYTES:
                        await self.reply(send, 413, {'error': 'request_too_large'})
                        return
                    if not message.get('more_body'):
                        break
            payload = json.loads(body)
            validate_request(payload, self.engine.family)
        except TimeoutError:
            await self.reply(send, 408, {'error': 'body_timeout'})
            return
        except (ValueError, UnicodeDecodeError):
            await self.reply(send, 422, {'error': 'invalid_embedding_input'})
            return
        if self.busy:
            await self.reply(send, 429, {'error': 'embedding_busy'})
            return
        self.busy = True
        future = asyncio.get_running_loop().run_in_executor(self.executor, self.engine.embed, payload)
        future.add_done_callback(lambda f: setattr(self, 'busy', False))
        try:
            result = await asyncio.wait_for(asyncio.shield(future), timeout=REQUEST_TIMEOUT_SECONDS)
            await self.reply(send, 200, result)
        except TimeoutError:
            # Work remains single-flight until the worker finishes; no unbounded queue.
            await self.reply(send, 504, {'error': 'embedding_timeout'})
        except InputError as exc:
            await self.reply(send, 422, {'error': str(exc)})
        except Exception:
            await self.reply(send, 503, {'error': 'embedding_unavailable'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-path', required=True)
    parser.add_argument('--family', choices=['qwen3', 'bge-m3'], default='qwen3')
    parser.add_argument('--host', action='append', default=[])
    parser.add_argument('--port', type=int, default=18083)
    parser.add_argument('--threads', type=int, choices=[1, 2], default=2)
    args = parser.parse_args()
    import uvicorn
    hosts = args.host or ['127.0.0.1']
    # Only explicit local addresses; never listen on wildcard/public interfaces.
    for host in hosts:
        address = ipaddress.ip_address(host)
        if address.is_unspecified or not (address.is_loopback or address.is_private):
            parser.error('Only explicit loopback or private bridge listener addresses are allowed')
    engine = EmbeddingEngine(args.model_path, args.family, args.threads)
    sockets = []
    for host in hosts:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, args.port))
        sock.listen(8)
        sockets.append(sock)
    server = uvicorn.Server(uvicorn.Config(EmbeddingApp(engine), log_level='warning', access_log=False,
                                           limit_concurrency=4, backlog=8, timeout_keep_alive=5))
    server.run(sockets=sockets)


if __name__ == '__main__':
    main()
