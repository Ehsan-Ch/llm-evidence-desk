"""Small local demo server; no uploads, document editing, or remote exposure."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from pathlib import Path
import threading
from .core import answer


def make_handler(index, client, report, port):
    lock = threading.Lock()
    hosts = {f'127.0.0.1:{port}',f'localhost:{port}'}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not persist questions in request logs.

        def send(self, status, payload, content_type='application/json; charset=utf-8'):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(body)

        def valid_host(self):
            return self.headers.get('Host') in hosts

        def do_GET(self):
            if not self.valid_host():
                return self.send(403, {'error':'Unsupported host.'})
            if self.path in ('/','/report.html'):
                payload = {**report, 'mode':'live', 'live_model':client.model,
                           'live_corpus_count':len(index.chunks), 'live_k':1}
                template = files('evidence_desk').joinpath('template.html').read_text(encoding='utf-8')
                html = template.replace('__PAYLOAD__',json.dumps(payload, ensure_ascii=False).replace('<','\\u003c'))
                return self.send(200, html.encode(), 'text/html; charset=utf-8')
            if self.path == '/api/status':
                try:
                    healthy = client.health()
                except (OSError,ValueError):
                    healthy = False
                return self.send(200, {'ready':healthy,'model':client.model,'passages':len(index.chunks)})
            return self.send(404, {'error':'Not found.'})

        def do_POST(self):
            if not self.valid_host() or self.headers.get('Origin') not in (None, 'http://'+self.headers.get('Host','')):
                return self.send(403, {'error':'Only same-origin local requests are allowed.'})
            if self.path != '/api/ask':
                return self.send(404, {'error':'Not found.'})
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                return self.send(415, {'error':'Use application/json.'})
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 8192:
                    return self.send(413, {'error':'Request body must be 1 to 8192 bytes.'})
                self.connection.settimeout(10)
                data = json.loads(self.rfile.read(length))
                if not isinstance(data,dict) or set(data) != {'question'}:
                    raise ValueError('Send a single question field.')
                index.retrieve(data['question'],1)  # Validate before acquiring model slot.
            except (ValueError,OSError):
                return self.send(400, {'error':'Provide a question containing 1 to 600 characters.'})
            if not lock.acquire(blocking=False):
                return self.send(429, {'error':'The local model is busy. Try again shortly.'})
            try:
                result = answer(index,data['question'],client,1)
                self.send(200,result)
            except (OSError,ValueError,KeyError,IndexError,TypeError):
                self.send(503, {'error':'The local model is unavailable or returned an invalid response. Check its server and try again.'})
            finally:
                lock.release()
    return Handler


def serve(index, client, report_path, port=8774):
    report = json.loads(Path(report_path).read_text(encoding='utf-8'))
    server = ThreadingHTTPServer(('127.0.0.1',port),make_handler(index,client,report,port))
    print(f'Evidence Desk: http://127.0.0.1:{port}/report.html',flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
