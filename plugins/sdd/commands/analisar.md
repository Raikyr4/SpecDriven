---
description: "Opcional após o passo 3: confere se spec, plano e tarefas estão coerentes antes de implementar. Não altera nada."
argument-hint: "<número da feature, ex.: 004>"
allowed-tools: Read, Glob, Grep, Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/py.sh *)
---

Analise a feature indicada por: $ARGUMENTS

Comece por `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py validar <NNN>`: os problemas de forma que ele acha (ids, CA sem RF,
RF/CA fora do plano, tarefas sem módulo/pronto, deltas inválidos) entram no relatório sem você
precisar procurá-los. Depois leia a constituição, a spec, o plano e as tarefas que existirem
para o que exige julgamento. **Não altere nenhum arquivo.**

Produza um relatório com uma tabela `Severidade | Onde | Problema | Sugestão`, severidade
CRÍTICA, ALTA, MÉDIA ou BAIXA, cobrindo:

1. **Cobertura:** RF ou CA sem item no plano; CA sem teste na estratégia; RF/CA sem tarefa.
2. **Órfãos:** item de plano ou tarefa sem origem na spec (escopo inventado).
3. **Constituição:** qualquer violação de princípio, stack ou fronteira (sempre CRÍTICA).
4. **Contradições:** termos, números ou comportamentos diferentes entre os artefatos.
5. **Ambiguidades:** requisito vago, sem número, ou questão em aberto que bloqueia o plano.
6. **Tarefas:** sem critério de pronto, mais de um módulo sem justificativa, dependência fora
   de ordem, lógica sem teste.
7. **ADRs:** plano aprovado que cita ADR de `docs/adr/` ainda com Situação `proposta` (ALTA:
   a ADR deveria ter sido aceita no commit que aprovou o plano).

Feche com uma tabela de cobertura `RF/CA → plano → tarefa → teste` e o veredito: pronto para
aprovação, ou o que precisa mudar antes.
