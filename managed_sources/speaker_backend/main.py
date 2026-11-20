"""Existing status UI plus stateless, container-network-only embedding service."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import threading
from pathlib import Path
from engine import Extractor,MODEL_ID

class Handler(BaseHTTPRequestHandler):
 engine=None;probe=None;gate=threading.BoundedSemaphore(1)
 def log_message(self,*args):pass
 def send(self,code,data):
  body=json.dumps(data,ensure_ascii=False,allow_nan=False).encode()
  self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers()
  try:self.wfile.write(body)
  except (BrokenPipeError,ConnectionResetError):pass
 def do_GET(self):
  if self.server.server_port==8766:
   if self.path=='/health':self.send(200,{'ok':True,'model':MODEL_ID,'reference_probe':self.probe,'service_version':'1.0.0'})
   else:self.send(404,{'error':'not_found'})
   return
  if self.path=='/health':self.send(200,{'ok':True,'speaker_backend':True});return
  try:cfg=json.loads(Path('/data/options.json').read_text())
  except (OSError,ValueError):cfg={}
  if self.path=='/':self.send(200,{'status':'Jarvis Core běží','jarvis':cfg.get('jarvis_name','Jarvis'),'user':cfg.get('user_name','Martin')})
  else:self.send(404,{'error':'not_found'})
 def do_POST(self):
  if self.server.server_port!=8766 or self.path!='/embedding':self.send(404,{'error':'not_found'});return
  try:size=int(self.headers.get('Content-Length','0'))
  except ValueError:self.send(400,{'error':'length'});return
  if not 1<=size<=384000 or size%2 or self.headers.get('Transfer-Encoding'):
   self.send(400,{'error':'size'});return
  if not self.gate.acquire(blocking=False):self.send(429,{'error':'busy'});return
  try:
   self.connection.settimeout(3);pcm=self.rfile.read(size)
   if len(pcm)!=size:self.send(400,{'error':'incomplete'});return
   self.send(200,self.engine.process(pcm))
  except (ValueError,TimeoutError,OSError):self.send(400,{'error':'audio'})
  finally:self.gate.release()

def main():
 Handler.engine=Extractor('/models/3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx')
 Handler.probe=Handler.engine.probe('/models')
 if not Handler.probe['passed']:raise RuntimeError('speaker_reference_probe_failed')
 # Port 8766 is deliberately absent from addon host port mappings.
 internal=ThreadingHTTPServer(('0.0.0.0',8766),Handler)
 threading.Thread(target=internal.serve_forever,daemon=True).start()
 print(json.dumps({'speaker_backend':'ready','model':MODEL_ID,'reference_probe':Handler.probe}),flush=True)
 ThreadingHTTPServer(('0.0.0.0',8765),Handler).serve_forever()
if __name__=='__main__':main()
