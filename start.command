#!/bin/zsh
set -e
cd "${0:A:h}"
if command -v node >/dev/null 2>&1; then
  NODE_BIN="$(command -v node)"
else
  NODE_BIN="/Users/admin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
fi
if [[ ! -x "$NODE_BIN" ]]; then
  echo "需要 Node.js 22 或更新版本。请安装后重新双击此文件。"
  read -r
  exit 1
fi
if [[ ! -d node_modules ]]; then
  echo "首次使用：请在本文件夹运行 npm install，再重新启动。"
  read -r
  exit 1
fi
"$NODE_BIN" server.mjs
