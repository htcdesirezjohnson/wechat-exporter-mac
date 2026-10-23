#!/bin/bash
cd "$(dirname "$0")" || exit 1
bash ./run.sh app.py
result=$?
if [ "$result" -ne 0 ]; then
  echo '启动未完成，请保留上方错误信息。'
  read -r -p '按回车关闭…' answer
fi
exit "$result"
