---
description: "Passo 2: com a spec aprovada e commitada, gera o plano técnico (como fazer) para você aprovar."
argument-hint: "<número da feature, ex.: 004>"
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion, Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/py.sh *)
---

Gere o PLANO TÉCNICO da feature indicada por: $ARGUMENTS

Se não localizar a spec, liste o que existe em `specs/` e pergunte, sem inventar.
O gate só libera este arquivo com a spec commitada e aprovada; se ele negar, diga ao humano
que a spec precisa de revisão e não tente contornar.

## Antes de escrever

- Leia a spec, `specs/constitution.md`, `specs/steering/` e o `instructions/` de cada módulo
  que a spec atinge.
- Leia o código dos pontos que vão mudar: o plano descreve o código real, não um imaginado.
- Consulte as decisões anteriores em `docs/adr/` e os planos de features vizinhas.

## O arquivo

Crie `specs/<NNN>-<slug>-plan.md` com o **mesmo NNN e slug da spec**, a partir de
`${CLAUDE_PLUGIN_ROOT}/templates/artefatos/plan.md`, com `status: rascunho`. Se já existir,
pergunte antes de sobrescrever.

Regras:

- Todo RF e todo CA da spec aparecem no plano (arquitetura ou estratégia de testes).
- Toda fronteira cruzada tem contrato explícito: entrada, saída, erros e versão.
- Estratégia de testes com a ferramenta de cada módulo e cada CA mapeado para um teste.
- Unidades de entrega que caibam em um commit atômico por módulo.
- Decisão com impacto duradouro vira ADR em `docs/adr/` (template
  `${CLAUDE_PLUGIN_ROOT}/templates/artefatos/adr.md`), com `**Situação:** proposta`, citada no
  plano. Nunca escreva `aceita`: quem aceita a ADR é o humano, ao aprovar o plano.
- Riscos e pontos que precisam de decisão humana listados; se algo estiver ambíguo, pergunte.
- **Tamanho:** mire 900 a 1600 tokens (cerca de 3,5 a 6,5 KB). Corte o que não muda a
  implementação; detalhe que só um arquivo precisa fica no código ou no `instructions/`.
- **Spec de classe `media`** (veja `**Classe:**` na spec): acrescente ao plano a seção
  `## Tarefas` com as regras de `/tarefas` (`- [ ] T-<n> — <título> · módulo · origem · pronto:`).
  Aprovado, o plano libera o `/implementar` sem `-tasks.md`.
- Não implemente nada e não altere outros arquivos além do plano e das ADRs propostas.

## Depois de escrever

Rode `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py validar specs/<NNN>-<slug>-plan.md` e corrija todo ERRO (RF/CA da spec
ausente, tarefas sem módulo ou pronto). Depois chame o agente `arquiteto` para revisar o plano contra a constituição e a spec, e aplique as
correções. Termine dizendo que o próximo passo é revisar, aprovar e commitar o plano; só então
`/tarefas <NNN>` é liberado (ou, com `## Tarefas` no plano, direto o `/implementar <NNN>`). Se houver ADRs propostas, liste os caminhos e diga que, na mesma
aprovação, o humano troca a **Situação** de cada uma de `proposta` para `aceita` (ou apaga a
ADR rejeitada e ajusta o plano) e commita as ADRs junto com o plano, no mesmo commit.
Sugira esse commit (`git add specs/<NNN>-<slug>-plan.md docs/adr/<arquivos>` e
`git commit -m "plan <NNN>: <título>"`), conforme `${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md`.
Nunca escreva `status: aprovado`.
