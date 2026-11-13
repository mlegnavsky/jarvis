"""Build-time downloads of pinned model and upstream public test fixtures."""
import hashlib
from pathlib import Path
import urllib.request
BASE='https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/'
ASSETS={
 '3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx':'aa3cfc16963a10586a9393f5035d6d6b57e98d358b347f80c2a30bf4f00ceba2',
 'fangjun-sr-1.wav':'33c24061180224d2350143ee19e3af031446995c676bd25996325d34bb20a4d5',
 'fangjun-test-sr-1.wav':'9175e523081bf6a630ce72a55b05f92148eaafaf58cbbbe743686cd81c50848e',
 'leijun-sr-1.wav':'160a3d9bf5dd5038da8191b4430e1f3f751461613ae9489401b6b35a61b488ad',
 'leijun-test-sr-1.wav':'36cda04ee4d10e38095de73b77c99e8e7c54347232967a9cde4cf54f7d496bab'}
def main():
 root=Path('/models');root.mkdir(exist_ok=True)
 for name,digest in ASSETS.items():
  path=root/name
  urllib.request.urlretrieve(BASE+name,path)
  if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('asset_checksum_'+name)
if __name__=='__main__':main()
