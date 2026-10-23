#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
umask 077
runtime=""
for candidate in python3.12 python3.11 python3.13 python3.14 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys;sys.exit(0 if sys.version_info >= (3,9) else 1)'; then
    runtime="$candidate"
    break
  fi
done
[ -n "$runtime" ] || { echo '请先安装 Python 3.11 或以上版本。'; exit 1; }
"$runtime" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-core.txt
echo '基础依赖安装完成，可双击「启动.command」。'
read -r -p '按回车关闭…' answer
