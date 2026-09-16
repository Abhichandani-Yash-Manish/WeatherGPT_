"""Serve the built probe page under either policy, for the R0 CSP measurement. Development only."""
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import REACT_CSP, STRICT_CSP

DIST = ROOT / 'web' / 'dist'
TYPES = {'.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html', '.json': 'application/json'}


REPORTS = Path(__file__).resolve().parent


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass

    def do_POST(self):
        if self.path.split('?')[0] != '/__probe/report':
            self.send_response(404); self.end_headers(); return
        length = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(length)
        policy = 'strict' if 'strict' in (self.headers.get('Referer') or '') else 'react'
        (REPORTS / ('csp-report-' + policy + '.json')).write_bytes(body)
        print('report: ' + policy + ' ' + str(len(body)) + ' bytes', flush=True)
        self.send_response(204); self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]
        policy = 'strict' if 'csp=strict' in self.path else 'react'
        if path in ('/', '/probe.html'):
            body = (DIST / 'probe.html').read_text().encode(); kind = 'text/html'
        else:
            target = (DIST / path.lstrip('/')).resolve()
            if DIST.resolve() not in target.parents or not target.exists():
                self.send_response(404); self.end_headers(); return
            body = target.read_bytes(); kind = TYPES.get(target.suffix, 'application/octet-stream')
        self.send_response(200)
        self.send_header('Content-Type', kind + '; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Security-Policy', STRICT_CSP if policy == 'strict' else REACT_CSP)
        self.end_headers(); self.wfile.write(body)


server = ThreadingHTTPServer(('127.0.0.1', 8798), Handler)
print('probe server on http://127.0.0.1:8798', flush=True)
server.serve_forever()
