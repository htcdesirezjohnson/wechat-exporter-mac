"""Private per-account keys; no automatic process scanning from the web UI."""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from . import constants
from .key_extractor import KeyExtractionError


def state_dir(layout):
    identity = str(Path(layout.account_dir).resolve())
    token = hashlib.sha256(identity.encode()).hexdigest()[:24]
    return Path(constants.APP_DIR) / 'accounts' / token


def load_keys(layout):
    path = state_dir(layout) / 'keys.json'
    try:
        data = json.loads(path.read_text())
        if data.get('account_dir') != str(Path(layout.account_dir).resolve()):
            raise ValueError('account mismatch')
        keys = data['keys']
        if not isinstance(keys, dict):
            raise ValueError('invalid key map')
        keys = {s.lower(): k.lower() for s, k in keys.items()
                if re.fullmatch('[0-9a-fA-F]{32}', s)
                and isinstance(k, str) and re.fullmatch('[0-9a-fA-F]{64}', k)}
        if not keys:
            raise ValueError('empty key map')
        return keys
    except (OSError, ValueError, KeyError, TypeError):
        raise KeyExtractionError('这个账号尚未配置。请双击「配置账号.command」，选择当前由本人登录并授权的账号；完成后重新启动导出工具。') from None


def save_keys(layout, keys):
    directory = state_dir(layout)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    fd, tmp = tempfile.mkstemp(prefix='.keys-', dir=str(directory))
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump({'account_dir': str(Path(layout.account_dir).resolve()), 'keys': keys}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, directory / 'keys.json')
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def ready(layout):
    try:
        load_keys(layout)
        return True
    except KeyExtractionError:
        return False
