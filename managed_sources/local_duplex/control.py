"""Only a fresh admin-written probe request, never arbitrary device commands."""
import json
import math
import re


def read_control(root,last_nonce,now):
    path=root/'control.json'
    try:
        if root.is_symlink() or path.is_symlink() or not path.is_file() or path.stat().st_size>4096:return None
        data=json.loads(path.read_text())
        if not isinstance(data,dict) or set(data)!={'action','nonce','expires_at'}:return None
        expiry=data['expires_at'];nonce=data['nonce']
        if data['action'] not in ('probe','output_test') or not isinstance(nonce,str) or not re.fullmatch(r'[a-f0-9]{32}',nonce) or nonce==last_nonce:return None
        if type(expiry) not in (int,float) or not math.isfinite(expiry) or not now<expiry<=now+600:return None
        return data
    except (OSError,ValueError,TypeError):return None
