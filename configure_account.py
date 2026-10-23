#!/usr/bin/env python3
"""Configure one explicitly selected, authorized local account."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from core import account_state, constants, db_decryptor, locator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--account')
    parser.add_argument('--prepared-copy', type=Path)
    parser.add_argument('--timeout', type=int, default=900,
                        help='seconds to allow for phone login and capture (30-900)')
    parser.add_argument('--yes', action='store_true', help='already confirmed normal WeChat exit')
    args = parser.parse_args()
    if not 30 <= args.timeout <= 900:
        parser.error('--timeout must be between 30 and 900 seconds')
    os.umask(0o077)
    accounts = locator.discover_accounts()
    if not accounts:
        raise RuntimeError('未找到账号。先在官方微信登录并同步聊天记录。')
    if args.account:
        matches = [a for a in accounts if a.account_id == args.account]
        if len(matches) != 1:
            raise RuntimeError('账号不存在或不唯一，请通过菜单选择。')
        layout = matches[0]
    else:
        print('请选择本次由账号本人授权导出的账号：')
        for index, account in enumerate(accounts, 1):
            print(f'  {index}. {account.account_id}  ({len(account.message_dbs)} 个消息库)')
        answer = input('输入编号（回车取消）：').strip()
        if not answer:
            return
        if not answer.isdigit() or not 1 <= int(answer) <= len(accounts):
            raise RuntimeError('编号无效，未作任何更改。')
        layout = accounts[int(answer) - 1]
    if layout.version != 'v4':
        raise RuntimeError('这条配置流程适配 Apple 芯片上的微信 4.1；当前账号是旧版数据库。')
    print('本次账号：' + layout.account_id)
    if args.prepared_copy:
        print('将使用已准备好的临时微信副本；原版程序和系统 SIP 保持原状。')
    else:
        print('将临时复制微信程序并给副本签名；原版程序和系统 SIP 保持原状。')
    print('请保存草稿，从微信菜单正常退出。稍后由账号本人在临时窗口扫码登录。')
    print(f'登录与配置最多等待 {args.timeout} 秒；超时会关闭临时副本并恢复原版。')
    if not args.yes and input('已获账号本人授权并已退出微信，输入 YES 继续：').strip() != 'YES':
        print('已取消。')
        return
    directory = account_state.state_dir(layout)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    attempt = Path(tempfile.mkdtemp(prefix='capture-', dir=str(directory)))
    backend = Path(__file__).parent / 'vendor' / 'wechat41' / 'bootstrap_keys.py'
    command = [sys.executable, str(backend), '--db-root',
               str(Path(layout.account_dir) / 'db_storage'),
               '--state-dir', str(attempt), '--timeout', str(args.timeout),
               '--acknowledge-debug-copy']
    if args.prepared_copy:
        command.extend(['--prepared-copy', str(args.prepared_copy)])
    result = subprocess.run(command)
    manifest = attempt / 'keys.json'
    if result.returncode or not manifest.exists():
        raise RuntimeError('本次配置未完成，之前该账号的配置已保留。请查看上方错误；没有覆盖旧密钥。')
    entries = json.loads(manifest.read_text())['keys']
    dbroot = (Path(layout.account_dir) / 'db_storage').resolve()
    keys = {}
    for relative, entry in entries.items():
        path = (dbroot / relative).resolve()
        if not path.is_relative_to(dbroot):
            raise RuntimeError('捕获文件路径异常。')
        key = entry['enc_key']
        # Validate against the current database before saving; never print keys.
        import sqlcipher3.dbapi2 as sqlcipher
        from urllib.parse import quote
        connection = sqlcipher.connect('file:' + quote(str(path)) + '?mode=ro&immutable=1', uri=True)
        try:
            literal = db_decryptor._key_literal(key, str(path))
            connection.execute('PRAGMA key = "' + literal + '"')
            db_decryptor._apply_pragmas(connection.cursor(), 'v4')
            connection.execute('SELECT count(*) FROM sqlite_master').fetchone()
        finally:
            connection.close()
        keys[db_decryptor.read_salt(str(path)).hex()] = key
    required = db_decryptor._collect_sources(layout)
    missing = [Path(p).name for p in required if db_decryptor.read_salt(p).hex() not in keys]
    # Merge only this account's previous verified keys, never another account's.
    try:
        previous = account_state.load_keys(layout)
    except Exception:
        previous = {}
    previous.update(keys)
    account_state.save_keys(layout, previous)
    print(f'已为本次账号保存 {len(keys)} 个经过校验的数据库密钥。')
    if missing:
        print('仍有数据库未捕获：' + '、'.join(missing))
        print('可再次配置，在临时微信中点开需要的旧聊天；导出界面会阻止漏库导出。')
    print('请双击「启动.command」，在界面里选择对应账号。')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('配置未完成：' + str(exc), file=sys.stderr)
        sys.exit(1)
