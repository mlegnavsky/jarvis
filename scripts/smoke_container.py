"""CI-only container startup/authentication smoke check with a fake Supervisor."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

app = sys.argv[1]
assert app in ('jarvis', 'jarvis_updater')
network = 'jarvis-smoke'
image = 'jarvis-smoke:local'

def docker(*args, check=True):
    return subprocess.run(['docker', *args], check=check, capture_output=True, text=True)

fake = '''from http.server import BaseHTTPRequestHandler, HTTPServer
import json
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'result':'ok','data':{'slug':'smoketest_jarvis_updater'}}).encode())
    def log_message(self, *args): pass
HTTPServer(('0.0.0.0',80), Handler).serve_forever()
'''
port = 8099 if app == 'jarvis' else 8100
probe = '''import json, urllib.request, urllib.error
base = 'http://127.0.0.1:PORT'
path = '/v1/health' if PORT == 8099 else '/v1/jobs/missing'
try:
    urllib.request.urlopen(base + path)
    raise AssertionError('unauthenticated request accepted')
except urllib.error.HTTPError as error:
    assert error.code == 401, error.code
request = urllib.request.Request(base + path, headers={'Authorization': 'Bearer ' + 'x'*32})
try:
    response = urllib.request.urlopen(request)
    assert PORT == 8099
    assert json.load(response)['version'] == '0.1.0'
except urllib.error.HTTPError as error:
    assert PORT == 8100 and error.code == 404
    assert json.load(error)['error'] == 'job_not_found'
'''.replace('PORT', str(port))
with tempfile.TemporaryDirectory() as temporary:
    options = Path(temporary) / 'options.json'
    options.write_text(json.dumps({'api_token': 'x'*32}))
    try:
        docker('network', 'create', network)
        docker('run', '-d', '--name', 'fake-supervisor', '--network', network,
               '--network-alias', 'supervisor', image, 'python', '-c', fake)
        docker('run', '-d', '--name', 'jarvis-app', '--network', network,
               '-e', 'SUPERVISOR_TOKEN=fake-smoke-token',
               '-v', str(options) + ':/data/options.json:ro', image)
        for attempt in range(30):
            result = docker('exec', 'jarvis-app', 'python', '-c', probe, check=False)
            if result.returncode == 0:
                print(app + ': container startup and authentication OK')
                break
            time.sleep(1)
        else:
            raise RuntimeError(result.stderr + docker('logs', 'jarvis-app', check=False).stderr)
    finally:
        docker('rm', '-f', 'jarvis-app', 'fake-supervisor', check=False)
        docker('network', 'rm', network, check=False)
