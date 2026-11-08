---
description: Cria ou altera as regras fixas do seu projeto (stack, fronteiras, definição de pronto). Para mudar uma regra, descreva o que muda.
argument-hint: "[o que mudar na constituição]"
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion
---

Trabalhe na constituição do projeto, `specs/constitution.md`.

Pedido do humano: $ARGUMENTS

- **Se não existe:** crie a partir de `${CLAUDE_PLUGIN_ROOT}/templates/projeto/constitution.md`,
  preenchendo stack, fronteiras e invariantes com o que o código, o `CLAUDE.md` e
  `specs/steering/` mostram. O que não der para inferir vai para "Questões em aberto" no fim.
  Frontmatter com `status: rascunho`.
- **Se existe e está em rascunho:** ajuste conforme o pedido.
- **Se já foi aprovada:** não reescreva princípios. Proponha uma **emenda** na seção
  "Emendas": data de hoje, o que muda, por quê, quem decidiu e o que deliberadamente não muda.
  Liste também os trechos de `CLAUDE.md`, `instructions/` e specs que ficarão desatualizados.
  O gate vai pedir confirmação humana para editar o arquivo aprovado.

Nunca escreva `status: aprovado`. A aprovação é do dev responsável, com um commit.
Termine sugerindo esse commit conforme `${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md`:
`constituicao: aprova a constituição do projeto` ou, para emenda,
`constituicao: emenda <AAAA-MM-DD> - <resumo>`, com os arquivos que entram no `git add`.
Se algo estiver ambíguo, pergunte com `AskUserQuestion` antes de escrever.
