#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
umask 077
mode="${1:-app.py}"
shift || true
runtime=""
for candidate in "$PWD/.venv/bin/python" "$HOME/.wechat_exporter/venv/bin/python"; do
  if [ -x "$candidate" ] && "$candidate" -c 'import flask,sqlcipher3,zstandard,rich,jinja2,click,pandas,PIL,Crypto' >/dev/null 2>&1; then
    runtime="$candidate"
    break
  fi
done
if [ -z "$runtime" ]; then
  echo '没有完整的 Python 环境，请先运行「安装依赖.command」。'
  exit 1
fi
export WECHAT_EXPORTER_DATA_DIR="$HOME/Library/Application Support/WeChatExporterLocal"
exec "$runtime" "$mode" "$@"
