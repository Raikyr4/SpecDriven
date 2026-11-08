---
description: "Passo 0,5 (opcional): transforma uma ideia vaga num brief — problema, quem tem, sucesso medido, escopo, riscos — e, em iniciativa grande, nas features que viram /especificar."
argument-hint: "[brainstorm|prfaq|prd] <ideia: texto, arquivo .md/.docx/.pdf ou pasta>"
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion, Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/py.sh *)
---

Conduza a descoberta da ideia a seguir:

$ARGUMENTS

## Quando usar

Use quando a necessidade ainda não está clara (veio como solução, sem métrica, sem saber para
quem) ou quando a iniciativa é grande demais para uma spec. Se a necessidade já está clara e cabe
numa feature, diga isso e recomende `/especificar` direto; não faça descoberta por ritual.

## Modo

A primeira palavra dos argumentos escolhe o modo; sem ela, é `brief`.

- `brief` — o documento básico.
- `brainstorm` — compara caminhos antes de fechar.
- `prfaq` — testa a ideia com comunicado de lançamento e perguntas difíceis.
- `prd` — iniciativa com várias features: requisitos de produto e fatias.

Para `brainstorm`, `prfaq` e `prd`, leia `${CLAUDE_PLUGIN_ROOT}/references/descoberta-modos.md`.

## Passos

1. **Entrada.** Texto: use como está. Arquivo ou pasta: extraia com
   `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" scripts/ler_fontes.py <caminho>` (o mesmo do
   `/especificar`). Leia `specs/steering/produto.md` se existir. Não leia código: a descoberta é
   sobre o problema.
2. **Rascunho primeiro.** Preencha o que der para inferir no template
   `${CLAUDE_PLUGIN_ROOT}/templates/artefatos/brief.md` e identifique as lacunas.
3. **No máximo 3 rodadas de perguntas**, em lote com `AskUserQuestion`. Escolha a técnica pela
   lacuna em `${CLAUDE_PLUGIN_ROOT}/references/descoberta-tecnicas.md` (uma ou duas, não todas).
   Depois da terceira rodada, o que faltar vira Pergunta aberta.
4. **Grave** `docs/descoberta/<slug>/brief.md` (slug em kebab-case, sem acento), com
   `status: rascunho` e o `modo` usado, mantendo só as seções do modo.
5. **Valide:** `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py validar docs/descoberta/<slug>/brief.md`
   e corrija todo ERRO.

## Regras

- Sem solução técnica: nada de tela, tabela, rota, biblioteca. Solução trazida pelo humano vira
  opção, com o porquê registrado.
- Sucesso sempre com número, unidade e prazo; sem número, vira pergunta aberta.
- Não invente dado de negócio. Não altere nenhum arquivo além do brief.
- Seja breve: o brief cabe em uma ou duas páginas. Descoberta longa custa tokens e atenção.

## Ao terminar

Mostre o caminho do brief, as perguntas abertas e o próximo passo:

- `brief`, `brainstorm` ou `prfaq` → `/especificar docs/descoberta/<slug>/brief.md`;
- `prd` → um `/especificar docs/descoberta/<slug>/brief.md F-<n>` por feature, na ordem sugerida.

O brief não passa pelo gate. Se o humano quiser registrá-lo, sugira o commit conforme
`${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md` (`git add docs/descoberta/<slug>/brief.md` e
`git commit -m "descoberta: <nome da ideia>"`). Para dar o brief por fechado, o humano troca o
status para `aprovado` antes do commit; você nunca escreve `aprovado`.
