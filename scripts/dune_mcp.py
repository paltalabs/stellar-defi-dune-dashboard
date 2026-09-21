#!/usr/bin/env python3
"""Cliente MCP de Dune. Lee la credencial local sin imprimirla ni evaluarla como shell.

Uso: python3 scripts/dune_mcp.py tools/list
     python3 scripts/dune_mcp.py getUsage '{}'
     python3 scripts/dune_mcp.py createDuneQuery @/ruta/request.json
"""
import json
import http.client
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def credential():
    values = dict(os.environ)
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text().splitlines():
            match = re.match(r'^\s*(?:export\s+)?(DUNE_API_KEY|DUNE_APY_KEY|DUNE_APY)\s*=\s*(.*)$', line)
            if match:
                value = match[2].strip()
                if value[:1] in ('"', "'") and value[-1:] == value[:1]:
                    value = value[1:-1]
                else:
                    value = value.split(' #', 1)[0].strip()
                values.setdefault(match[1], value)
    key = values.get('DUNE_API_KEY') or values.get('DUNE_APY_KEY') or values.get('DUNE_APY')
    if not key:
        raise RuntimeError('Falta DUNE_API_KEY (o DUNE_APY) en el entorno o .env')
    return key


class DuneMCP:
    def __init__(self):
        self.headers = {'X-DUNE-API-KEY': credential(), 'Content-Type': 'application/json',
                        'Accept': 'application/json, text/event-stream'}
        self.counter = 0
        result = self.rpc('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                          'clientInfo': {'name': 'stellar-defi-pilot', 'version': '1.0'}})
        self.headers['MCP-Protocol-Version'] = result['protocolVersion']
        self.rpc('notifications/initialized', notification=True)

    def rpc(self, method, params=None, notification=False):
        self.counter += 1
        payload = {'jsonrpc': '2.0', 'method': method}
        if not notification:
            payload['id'] = self.counter
        if params is not None:
            payload['params'] = params
        request = urllib.request.Request('https://api.dune.com/mcp/v1',
                    data=json.dumps(payload).encode(), headers=self.headers)
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                session = response.headers.get('Mcp-Session-Id')
                if session:
                    self.headers['Mcp-Session-Id'] = session
                if 'text/event-stream' in response.headers.get('Content-Type', ''):
                    # Stop at the RPC response; the SSE connection may stay open afterwards.
                    body = ''
                    for line in response:
                        text = line.decode()
                        if text.startswith('data:'):
                            candidate = json.loads(text[5:].strip())
                            if candidate.get('id') == payload.get('id'):
                                body = json.dumps(candidate)
                                break
                else:
                    body = response.read().decode()
        except urllib.error.HTTPError as error:
            raise RuntimeError(f'Dune HTTP {error.code}') from None
        if not body:
            return {}
        if body.lstrip().startswith('{'):
            message = json.loads(body)
        else:
            messages = [json.loads(line[5:].strip()) for line in body.splitlines()
                        if line.startswith('data:')]
            message = next(m for m in messages if m.get('id') == payload.get('id'))
        if 'error' in message:
            raise RuntimeError(json.dumps(message['error']))
        return message.get('result', {})

    def call(self, name, arguments):
        if name == 'getDuneQuery':
            # Read-only. The MCP answered getDuneQuery with empty bodies or hung on 2026-09-21;
            # the REST endpoint works with the same key, so it goes first.
            try:
                return self._rest_query(arguments['query_id'])
            except urllib.error.URLError:
                result = self._call(name, arguments)
                if not result.get('query'):
                    raise RuntimeError('getDuneQuery sin SQL')
                return result
        return self._call(name, arguments)

    def _rest_query(self, query_id):
        request = urllib.request.Request(f'https://api.dune.com/api/v1/query/{query_id}',
                                         headers={'X-DUNE-API-KEY': self.headers['X-DUNE-API-KEY']})
        with urllib.request.urlopen(request, timeout=60) as response:
            remote = json.load(response)
        remote['query'] = remote['query_sql']
        return remote

    def _call(self, name, arguments):
        try:
            result = self.rpc('tools/call', {'name': name, 'arguments': arguments})
        except http.client.IncompleteRead:
            # Never retry a mutation after an ambiguous transport failure.
            raise
        if result.get('isError'):
            raise RuntimeError(json.dumps(result.get('content')))
        if 'structuredContent' in result:
            return result['structuredContent']
        text = '\n'.join(c.get('text', '') for c in result.get('content', []) if c.get('type') == 'text')
        try:
            return json.loads(text)
        except ValueError:
            return {'text': text}


def main():
    client = DuneMCP()
    name = sys.argv[1]
    raw = sys.argv[2] if len(sys.argv) > 2 else '{}'
    arguments = json.loads(Path(raw[1:]).read_text() if raw.startswith('@') else raw)
    result = client.rpc(name) if name == 'tools/list' else client.call(name, arguments)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
