---
description: "Passo 3: com o plano aprovado e commitado, quebra o trabalho em tarefas pequenas e testáveis para você aprovar."
argument-hint: "<número da feature, ex.: 004>"
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion, Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/py.sh *)
---

Gere a lista de tarefas da feature indicada por: $ARGUMENTS

Se não localizar a spec e o plano, liste o que existe em `specs/` e pergunte. Se o plano não
existir, diga que `/planejar` precisa rodar antes. O gate só libera este arquivo com o plano
commitado e aprovado.

Se o plano aprovado já tem a seção `## Tarefas` (caminho `media`), não crie `-tasks.md`: diga
que o próximo passo é `/implementar <NNN>`.

Leia a spec, o plano, a constituição e o `instructions/` dos módulos envolvidos.

Crie `specs/<NNN>-<slug>-tasks.md` com o mesmo NNN e slug, a partir de
`${CLAUDE_PLUGIN_ROOT}/templates/artefatos/tasks.md`, com `status: rascunho`.

Cada tarefa é uma linha `- [ ] T-<n> — <título> · módulo · origem · pronto: <critério>` e deve:

- caber em um commit atômico e tocar **um módulo** por padrão;
- ter critério de pronto verificável por comando (teste X passa, build sem avisos);
- declarar dependências pelo identificador (`depende de T-2`);
- citar o RF/CA da spec ou a unidade do plano que a origina;
- incluir o próprio teste quando introduz lógica. Não crie tarefa de "testes depois".

Se um módulo envolvido não tiver projeto de testes (ou o comando de teste em
`.claude/sdd.json` estiver vazio), a primeira tarefa da lista é criar esse projeto com o
framework previsto em `specs/steering/tecnologia.md`, registrá-lo no build e preencher o
comando `verificacao` do módulo em `.claude/sdd.json` (arquivo protegido: o humano confirma).
As tarefas seguintes que alteram código existente começam por um teste de caracterização do
comportamento atual e só depois mudam o código.

Uma tarefa só toca mais de um módulo quando dividi-la deixaria a branch principal quebrada
(tipicamente mudança de contrato), declarando o motivo na própria linha. Conveniência não é
motivo.

Ordene por dependência; tarefas de fronteira vêm depois do contrato fixado no plano. Agrupe
em ondas quando houver tarefas independentes que possam ir em paralelo.

Depois de gravar, rode `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py validar specs/<NNN>-<slug>-tasks.md`, corrija
todo ERRO e confira os AVISOs: todo CA tem tarefa, nenhuma tarefa sem origem. Termine dizendo que o próximo passo é revisar, aprovar e commitar a lista; só então
`/implementar <NNN>` é liberado. Sugira o commit da aprovação
(`git add specs/<NNN>-<slug>-tasks.md` e `git commit -m "tasks <NNN>: <título>"`), conforme
`${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md`. Nunca escreva `status: aprovado`.
