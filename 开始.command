#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")" || exit 1
umask 077
state_dir="$HOME/Library/Application Support/WeChatExporterLocal"
mkdir -p "$state_dir"
chmod 700 "$state_dir"
echo '首先配置一个账号；已配置账号可直接双击「启动.command」。'
setup_args=(configure_account.py)
if [ -f "$state_dir/prepared-copy-path.txt" ]; then
  IFS= read -r prepared_copy < "$state_dir/prepared-copy-path.txt"
  if [ -d "$prepared_copy" ]; then
    setup_args+=(--prepared-copy "$prepared_copy")
  fi
fi
export PYTHONUNBUFFERED=1
bash ./run.sh "${setup_args[@]}" 2>&1 | tee "$state_dir/setup-status.log"
result=${PIPESTATUS[0]}
if [ "$result" -eq 0 ]; then
  bash ./run.sh app.py 2>&1 | tee "$state_dir/app-status.log"
  result=${PIPESTATUS[0]}
fi
if [ "$result" -ne 0 ]; then
  echo '本次未完成。错误已保存在本机应用数据文件夹中，旧配置未覆盖。'
fi
read -r -p '按回车关闭…' answer
exit "$result"
