#!/bin/sh
# Executa um script Python do plugin com o primeiro interpretador 3.8+ disponível
# (python3, python ou py). Os atalhos da Microsoft Store no Windows são ignorados porque
# não passam no teste de versão.
# Uso: py.sh <script relativo à raiz do plugin> [argumentos...]
# Sai com 127 se nenhum interpretador servir.
raiz=$(cd "$(dirname "$0")/.." && pwd) || exit 127
script=$1
shift
for py in python3 python py; do
  if command -v "$py" >/dev/null 2>&1 &&
    "$py" -c 'import sys; sys.exit(sys.version_info < (3, 8))' </dev/null >/dev/null 2>&1; then
    exec "$py" "$raiz/$script" "$@"
  fi
done
echo "SDD: Python 3.8+ nao encontrado (tentei python3, python e py)." >&2
exit 127
