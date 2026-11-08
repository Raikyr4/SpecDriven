---
description: "Passo 4: com as tarefas aprovadas, implementa uma tarefa por vez com teste e para para você revisar e commitar."
argument-hint: "<número da feature, ex.: 004>"
---

Implemente as tarefas de `specs/<NNN>-<slug>-tasks.md` (ou `-bug.md`) da feature indicada por:

$ARGUMENTS

Se não localizar a feature, liste o que existe em `specs/` e pergunte. O gate bloqueia código
de módulo enquanto não houver tarefas commitadas, aprovadas e pendentes; se ele negar uma
escrita, relate ao humano em vez de contornar.

**Contexto mínimo, não arquivos inteiros.** Antes de cada tarefa, rode
`sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py contexto <NNN>`. Ele mostra a próxima
tarefa com dependências prontas, se a lista está liberada pelo gate, o módulo (com o
`instructions/` a ler e os comandos de verificação) e só os itens da spec e do plano que a linha
da tarefa cita. Leia então o `instructions/` indicado e o código que vai mudar. Abra a spec, o
plano ou a constituição inteiros apenas quando a saída não bastar (contrato entre módulos,
decisão D-n, ADR, princípio em dúvida) e diga ao humano por quê.

**Uma tarefa por vez:**

1. Trabalhe na tarefa que o `contexto` indicou (a próxima `- [ ]` com dependências prontas).
2. Escreva primeiro o teste que expressa o critério de aceite e veja-o falhar pelo motivo certo.
   O nome do teste contém `F<NNN>_CA_<n>` (ex.: `F004_CA_2_bloqueia_apos_5_falhas`): é assim que
   a cobertura CA → teste é calculada no `/verificar`.
3. Implemente o mínimo que o faz passar, seguindo plano, instructions e constituição. Não
   amplie o escopo: o que sobrar vira observação para o humano.
4. Rode a verificação do módulo (build sem avisos, testes). Só marque `- [x]` quando estiver
   verde, e cole a saída decisiva no relato.
5. Ao concluir uma fatia coesa, rode `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py revisao`. Ele grava o diff
   num arquivo temporário e diz se cada revisor é necessário (tamanho, arquivo novo, área ou termo
   sensível). Chame só os indicados, passando **o caminho do diff** e a tarefa (nunca o texto do
   diff); se nenhum for indicado, diga isso no relato. Corrija o que for CRÍTICO ou ALTO e **pare
   para revisão humana**.

Regras rígidas:

- Nunca desative teste, aviso, lint ou verificação de tipo para "passar". O gate bloqueia os
  padrões conhecidos; o princípio vale para todos.
- Não commite. Diga o que está pronto para commit, em qual módulo, com o bloco pronto
  (`git add <arquivos da tarefa e specs/<NNN>-<slug>-tasks.md>` e
  `git commit -m "task <NNN> T-<n>: <título>"`), conforme `${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md`.
- Ao parar, termine sempre com o próximo passo: "revise o diff, commite e rode
  `/implementar <NNN>` para a próxima tarefa (de preferência depois de `/clear`)". Se não
  restar `- [ ]`, o próximo passo é `/verificar <NNN>`.
- Se a spec ou o plano estiverem errados, pare e avise. Voltar uma fase é decisão humana.
- Nunca escreva credencial, connection string ou segredo no repositório.
