---
description: "Atalho para bug ou ajuste pequeno: descreva o problema e receba análise e tarefas num só arquivo para aprovar; depois use /implementar."
argument-hint: "<descrição do bug>"
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion, Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/py.sh *), Bash(git fetch:*), Bash(git status:*), Bash(git switch -c:*), Bash(git worktree add:*), Bash(git show:*)
---

Analise o bug descrito a seguir e prepare a correção pelo caminho curto do padrão SDD:

$ARGUMENTS

## Branch e pasta da feature (antes de tudo)

Leia `${CLAUDE_PLUGIN_ROOT}/references/branch-da-feature.md` e siga-o com prefixo `fix` e
comando `/corrigir`. Ele define `<base>`, o número `<NNN>` e a branch. Só continue aqui quando
ele disser para seguir.

## Quando o caminho curto vale

Só quando a correção **não** muda contrato entre módulos, modelo de dados, comportamento
combinado em outra spec ou mais de um módulo. Se mudar, pare e recomende `/especificar`.

## Passos

1. Leia `specs/constitution.md`, o `instructions/` do módulo e as specs relacionadas ao
   comportamento afetado.
2. Reproduza ou localize a causa lendo o código e os testes. Não altere código nesta fase.
3. Use o número `<NNN>` da branch definido no passo "Branch e pasta da feature".
4. Crie `specs/<NNN>-<slug>-bug.md` a partir de `${CLAUDE_PLUGIN_ROOT}/templates/artefatos/bug.md`,
   com `status: rascunho`: comportamento atual, esperado, o que não pode mudar, causa provável
   (com evidência ou marcada como hipótese), critérios de aceite em EARS e as tarefas.
5. A primeira tarefa é sempre o teste que reproduz o bug e falha hoje.

Termine dizendo que o próximo passo é revisar, trocar o status para `aprovado` e commitar;
então `/implementar <NNN>` é liberado. Sugira o commit da aprovação
(`git add specs/<NNN>-<slug>-bug.md` e `git commit -m "bug <NNN>: <título>"`), conforme
`${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md`. Nunca escreva `status: aprovado`.
