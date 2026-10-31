"""Bounded local sources, media and shared files. Never follows links or executes code."""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import uuid
from .config_files import ConfigFiles, EXTENSIONS
from .policy import APIError

MAX_FILE = 8 * 1024 * 1024
TEXT = EXTENSIONS | {'.sh', '.toml', '.ini', '.cfg', '.conf', '.svg', '.csv', '.xml'}
ASSETS = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.pdf', '.mp3', '.wav', '.ogg', '.mp4', '.zip'}


class WorkspaceFiles(ConfigFiles):
    def __init__(self, root, workspace):
        super().__init__(root)
        self.workspace = workspace

    def parts(self, name):
        if not isinstance(name, str) or not 1 <= len(name) <= 400 or '\\' in name:
            raise APIError(400, 'invalid_workspace_path')
        parts = name.split('/')
        if any(not p or p.startswith('.') or '\x00' in p for p in parts) or str(PurePosixPath(name)) != name:
            raise APIError(400, 'invalid_workspace_path')
        if any(re.search(r'(^|[_-])(secrets?|credentials?|tokens?|private[_-]?key)([._-]|$)', p, re.I) or p in ('options.json', 'id_rsa', 'id_ed25519') for p in parts):
            raise APIError(403, 'workspace_sensitive_path')
        suffix = PurePosixPath(name).suffix.lower()
        allowed = suffix in TEXT or parts[-1] in ('Dockerfile', 'Containerfile', 'Makefile', 'run', 'finish', 'requirements.txt')
        if self.workspace != 'addons':
            allowed = allowed or suffix in ASSETS
        if not allowed or self.workspace == 'addons' and len(parts) < 2:
            raise APIError(400, 'workspace_file_type_not_allowed')
        return parts

    def raw(self, name):
        with self.parent(name) as (parent, leaf):
            if parent is None:
                return None, 0o644
            try:
                fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            except FileNotFoundError:
                return None, 0o644
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise APIError(400, 'unsafe_workspace_file')
                data = stream.read(MAX_FILE+1)
            if len(data) > MAX_FILE:
                raise APIError(400, 'workspace_file_too_large')
            return data, stat.S_IMODE(info.st_mode) & 0o777

    def read(self, name):
        data, mode = self.raw(name)
        result = {'path': name, 'revision': 'missing' if data is None else hashlib.sha256(data).hexdigest(), 'bytes': len(data or b''), 'mode': mode}
        if data is None:
            result['content'] = None
        elif PurePosixPath(name).suffix.lower() in ASSETS:
            result['binary'] = True
        else:
            if len(data) > 256*1024:
                raise APIError(400, 'workspace_text_too_large')
            try:
                result['content'] = data.decode('utf-8')
            except UnicodeError:
                raise APIError(400, 'workspace_text_not_utf8') from None
        return result

    def write_raw(self, name, data, expected_revision, restore_mode=None):
        self.parts(name)
        if data is not None and len(data) > MAX_FILE:
            raise APIError(400, 'workspace_file_too_large')
        before, mode = self.raw(name)
        current = 'missing' if before is None else hashlib.sha256(before).hexdigest()
        if current != expected_revision:
            raise APIError(409, 'workspace_revision_conflict')
        with self.parent(name, create=data is not None) as (parent, leaf):
            if parent is not None:
                if data is None:
                    if before is not None:
                        os.unlink(leaf, dir_fd=parent)
                else:
                    temporary = '.jarvis-' + uuid.uuid4().hex
                    try:
                        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
                        with os.fdopen(fd, 'wb') as stream:
                            stream.write(data)
                            os.fchmod(stream.fileno(), mode if restore_mode is None else restore_mode & 0o777)
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temporary, leaf, src_dir_fd=parent, dst_dir_fd=parent)
                    finally:
                        try:
                            os.unlink(temporary, dir_fd=parent)
                        except FileNotFoundError:
                            pass
                os.fsync(parent)
        after, _ = self.raw(name)
        return {'path': name, 'revision': 'missing' if after is None else hashlib.sha256(after).hexdigest(), 'verified': after == data}

    def write(self, name, content, expected_revision):
        if content is not None:
            if PurePosixPath(name).suffix.lower() in ASSETS:
                raise APIError(400, 'use_binary_upload')
            self.validate(name, content)
        return self.write_raw(name, None if content is None else content.encode(), expected_revision)

    def inventory(self):
        if not self.root.is_dir() or self.root.is_symlink():
            raise APIError(503, 'workspace_mount_unavailable')
        items = []
        for parent, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = [d for d in dirs if not d.startswith('.') and not (Path(parent)/d).is_symlink()]
            for leaf in files:
                name = (Path(parent)/leaf).relative_to(self.root).as_posix()
                try:
                    self.parts(name)
                    info = (Path(parent)/leaf).lstat()
                    if stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                        items.append({'path': name, 'bytes': info.st_size})
                except (APIError, OSError):
                    continue
                if len(items) >= 1000:
                    return {'items': items, 'truncated': True}
        return {'items': items, 'truncated': False}


class Uploads:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def paths(self, key):
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', key):
            raise APIError(400, 'invalid_upload_id')
        return self.root/(key+'.json'), self.root/(key+'.part')

    def begin(self, args):
        meta, part = self.paths(args['upload_id'])
        if type(args['size']) is not int or not 0 <= args['size'] <= MAX_FILE or not re.fullmatch(r'[a-f0-9]{64}', args['sha256']):
            raise APIError(400, 'invalid_upload_size_or_digest')
        if meta.exists() or part.exists():
            raise APIError(409, 'upload_already_exists')
        if len(list(self.root.glob('*.json'))) >= 50:
            raise APIError(503, 'upload_staging_full')
        with part.open('xb') as stream:
            os.chmod(part, 0o600)
        with meta.open('x') as stream:
            os.chmod(meta, 0o600)
            json.dump(args, stream)
        return {'upload_id': args['upload_id'], 'offset': 0, 'verified': True}

    def info(self, key):
        meta, part = self.paths(key)
        if not meta.is_file() or not part.is_file():
            raise APIError(404, 'upload_not_found')
        return json.loads(meta.read_text()), part

    def chunk(self, key, offset, encoded):
        args, part = self.info(key)
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError):
            raise APIError(400, 'invalid_base64') from None
        if type(offset) is not int or offset != part.stat().st_size or not 0 < len(data) <= 128*1024 or offset+len(data) > args['size']:
            raise APIError(409, 'upload_offset_or_size_mismatch')
        with part.open('ab') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        return {'verified': True, 'upload_id': key, 'offset': offset+len(data)}

    def finish(self, key, files):
        args, part = self.info(key)
        data = part.read_bytes()
        if len(data) != args['size'] or hashlib.sha256(data).hexdigest() != args['sha256']:
            raise APIError(409, 'upload_digest_or_size_mismatch')
        if files.workspace != args['workspace'] or PurePosixPath(args['path']).suffix.lower() not in ASSETS:
            raise APIError(403, 'upload_target_not_allowed')
        result = files.write_raw(args['path'], data, args['expected_revision'])
        if result['verified']:
            self.paths(key)[0].unlink()
            part.unlink()
        return result
