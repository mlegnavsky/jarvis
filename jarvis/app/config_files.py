"""Bounded text editing under the HA mount, with no-follow directory handles."""
import ast
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import uuid
import yaml
from .policy import APIError

MAX_BYTES = 256 * 1024
ROOT_FILES = {'configuration.yaml', 'automations.yaml', 'scripts.yaml', 'scenes.yaml', 'groups.yaml', 'customize.yaml'}
ROOT_DIRS = {'packages', 'custom_components', 'blueprints', 'themes', 'www', 'python_scripts', 'jarvis_workspace'}
EXTENSIONS = {'.yaml', '.yml', '.py', '.json', '.js', '.css', '.html', '.md', '.txt', '.jinja', '.jinja2'}


def content_revision(content):
    return 'missing' if content is None else hashlib.sha256(content.encode()).hexdigest()


class ConfigFiles:
    def __init__(self, root=Path('/homeassistant')):
        self.root = Path(root)

    def parts(self, name):
        if not isinstance(name, str) or not 1 <= len(name) <= 400 or '\\' in name:
            raise APIError(400, 'invalid_config_path')
        parts = name.split('/')
        if (any(not p or p.startswith('.') or '\x00' in p for p in parts)
                or str(PurePosixPath(name)) != name
                or not (name in ROOT_FILES or len(parts) > 1 and parts[0] in ROOT_DIRS)
                or PurePosixPath(name).suffix not in EXTENSIONS):
            raise APIError(400, 'config_path_not_allowed')
        return parts

    @contextmanager
    def parent(self, name, create=False):
        parts = self.parts(name)
        try:
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        except OSError:
            raise APIError(503, 'ha_config_mount_unavailable') from None
        try:
            for part in parts[:-1]:
                if create:
                    try:
                        os.mkdir(part, mode=0o755, dir_fd=fd)
                    except FileExistsError:
                        pass
                try:
                    child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                except FileNotFoundError:
                    yield None, parts[-1]
                    return
                os.close(fd)
                fd = child
            yield fd, parts[-1]
        except OSError:
            raise APIError(400, 'unsafe_config_path') from None
        finally:
            os.close(fd)

    def read(self, name):
        content = None
        with self.parent(name) as (parent, leaf):
            if parent is not None:
                try:
                    fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                except FileNotFoundError:
                    fd = None
                if fd is not None:
                    with os.fdopen(fd, 'rb') as stream:
                        info = os.fstat(stream.fileno())
                        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                            raise APIError(400, 'unsafe_config_file')
                        data = stream.read(MAX_BYTES+1)
                    if len(data) > MAX_BYTES:
                        raise APIError(400, 'config_file_too_large')
                    try:
                        content = data.decode('utf-8')
                    except UnicodeError:
                        raise APIError(400, 'config_file_not_utf8') from None
        return {'path': name, 'content': content, 'revision': content_revision(content)}

    def validate(self, name, content):
        self.parts(name)
        if not isinstance(content, str) or len(content.encode()) > MAX_BYTES:
            raise APIError(400, 'config_file_too_large')
        try:
            suffix = PurePosixPath(name).suffix
            if suffix in {'.yaml', '.yml'}:
                # Compose checks syntax but never expands HA !secret/!include tags.
                list(yaml.compose_all(content, Loader=yaml.BaseLoader))
            elif suffix == '.json':
                def invalid_constant(value):
                    raise ValueError(value)
                json.loads(content, parse_constant=invalid_constant)
            elif suffix == '.py':
                ast.parse(content, filename=name)
        except (ValueError, SyntaxError, yaml.YAMLError, RecursionError):
            raise APIError(400, 'config_syntax_invalid') from None

    def write(self, name, content, expected_revision):
        if content is not None:
            self.validate(name, content)
        before = self.read(name)
        if before['revision'] != expected_revision:
            raise APIError(409, 'config_revision_conflict')
        with self.parent(name, create=content is not None) as (parent, leaf):
            if parent is not None:
                if content is None:
                    if before['content'] is not None:
                        os.unlink(leaf, dir_fd=parent)
                else:
                    temporary = '.jarvis-' + uuid.uuid4().hex
                    try:
                        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                     mode=0o600, dir_fd=parent)
                        with os.fdopen(fd, 'wb') as stream:
                            stream.write(content.encode())
                            stream.flush()
                            os.fsync(stream.fileno())
                        os.replace(temporary, leaf, src_dir_fd=parent, dst_dir_fd=parent)
                    finally:
                        try:
                            os.unlink(temporary, dir_fd=parent)
                        except FileNotFoundError:
                            pass
                os.fsync(parent)
        after = self.read(name)
        return {'path': name, 'revision': after['revision'], 'verified': after['content'] == content}

    def inventory(self):
        if not self.root.is_dir() or self.root.is_symlink():
            raise APIError(503, 'ha_config_mount_unavailable')
        items = []
        for parent, directories, files in os.walk(self.root, followlinks=False):
            relative = Path(parent).relative_to(self.root)
            directories[:] = [d for d in directories if not d.startswith('.')
                              and (relative.parts or d in ROOT_DIRS)
                              and not (Path(parent)/d).is_symlink()]
            for leaf in files:
                name = (relative / leaf).as_posix()
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
