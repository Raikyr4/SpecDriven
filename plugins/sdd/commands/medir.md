---
description: Mostra quantos tokens a sessão atual gastou (lido do log, sem estimativa) e, com a feature, registra o custo da fase.
argument-hint: "[<NNN> <fase>]"
allowed-tools: Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/py.sh *)
---

Meça o consumo da sessão atual. Argumentos: $ARGUMENTS

- **Sem argumentos:** rode `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" scripts/medir_sessao.py` na raiz
  do projeto e mostre a tabela.
- **Com `<NNN> <fase>`** (ex.: `004 implementar`): rode
  `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" scripts/medir_sessao.py --registrar specs/.metricas/<NNN>.jsonl --feature <NNN> --fase <fase>`.
  A linha registrada traz o total da sessão e o consumo desde o registro anterior da mesma
  sessão, que é o custo da fase.

Depois da tabela, diga em uma frase onde o gasto se concentrou (entrada nova, cache ou saída) e,
se a leitura de cache for baixa em relação à entrada, lembre que `CLAUDE.md` e arquivos lidos em
toda sessão precisam ser estáveis para o cache funcionar. Não altere outros arquivos.
