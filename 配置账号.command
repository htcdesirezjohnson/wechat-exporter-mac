#!/bin/bash
cd "$(dirname "$0")" || exit 1
bash ./run.sh configure_account.py
result=$?
read -r -p '按回车关闭…' answer
exit "$result"
