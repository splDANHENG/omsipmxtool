#!/bin/bash
cd "$(dirname "$0")" || exit 1
if [ -x .venv-gui/bin/python ]; then
  .venv-gui/bin/python -m omsimod.gui
  result=$?
elif [ -x .venv/bin/python ]; then
  .venv/bin/python -m omsimod.gui
  result=$?
else
  echo '请先按 README 安装 Python 3.10+ 并创建带 GUI 依赖的虚拟环境。'
  result=1
fi
if [ "$result" -ne 0 ]; then
  echo '启动失败。请检查上方错误，并按 README 安装 GUI 依赖。'
  read -r -p '按回车关闭…'
fi
exit "$result"
