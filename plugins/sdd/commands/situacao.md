---
description: Mostra em que passo está cada funcionalidade do projeto, o que espera sua aprovação e o próximo número livre.
allowed-tools: Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/py.sh *)
---

Rode `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py status` na raiz do projeto e mostre a tabela. Em seguida, diga em uma ou duas frases o
que está esperando revisão humana (artefatos em rascunho) e qual feature tem tarefas pendentes.
Se houver features em andamento em outras branches, liste-as com os módulos; se houver linha
**ATENCAO** de sobreposição, destaque-a e sugira combinar a ordem de merge.
