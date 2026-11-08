---
description: "Passo 1: comece uma funcionalidade nova. Descreva a necessidade (texto, arquivo ou pasta) e aprove a spec."
argument-hint: "<necessidade: texto, arquivo .md/.docx/.pdf, pasta ou brief da descoberta> [F-n]"
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion, Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/py.sh *), Bash(git fetch:*), Bash(git status:*), Bash(git switch -c:*), Bash(git worktree add:*), Bash(git show:*)
---

Escreva a ESPECIFICAÇÃO da feature que atende à necessidade a seguir:

$ARGUMENTS

## Branch e pasta da feature (antes de tudo)

Leia `${CLAUDE_PLUGIN_ROOT}/references/branch-da-feature.md` e siga-o com prefixo `feat` e
comando `/especificar`. Ele define `<base>`, o número `<NNN>` e a branch. Só continue aqui quando
ele disser para seguir.

## A necessidade

A entrada é a **necessidade**: o problema, quem tem e por que importa (o QUE e o porquê), não a
solução. Ela pode chegar de quatro formas, combinadas ou não:

- **Texto no prompt:** use como está.
- **Arquivo anexado ao prompt** (PDF ou imagem que já veio no contexto): use o conteúdo anexado.
- **Caminho de arquivo** `.md`, `.markdown`, `.txt`, `.docx` ou `.pdf`, ou **caminho de pasta**
  (lida inteira, com subpastas): extraia o texto de todos de uma vez com
  `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" scripts/ler_fontes.py <caminho> [<caminho> ...]`
  (caminhos com espaço entre aspas). O
  resumo no fim da saída lista o que precisa ser lido com a ferramenta Read (PDF quando não há
  `pdftotext` na máquina), o que foi ignorado por formato e o que não foi encontrado. Leia os
  pendentes com Read e avise o humano sobre os ignorados (ex.: `.doc` antigo, planilha), sem
  converter nada.
- **Nenhuma entrada:** pergunte qual é a necessidade com `AskUserQuestion`.

Com várias fontes, trate todas como uma necessidade só. Se elas se contradisserem, a
contradição vira pergunta ou questão em aberto, nunca escolha sua. Se as fontes trouxerem
solução pronta (tela, tabela, tecnologia), guarde o porquê dela na spec e deixe o como para o
plano. Na seção de contexto da spec, liste as fontes usadas (caminho ou "texto do prompt").
Se a necessidade cobrir mais de uma feature independente, proponha a divisão ao humano antes de
escrever. Se ela for vaga (veio como solução, sem para quem, sem métrica), sugira `/descobrir`
antes.

**Brief da descoberta** (`docs/descoberta/<slug>/brief.md`): use problema, quem tem, sucesso,
escopo e perguntas abertas como necessidade; as métricas M-n viram RNF ou contexto. Com
`F-<n>` nos argumentos (brief em modo `prd`), especifique **só** essa feature, com os RP que ela
cobre; sem `F-<n>` num PRD, pergunte qual. Cite nas fontes o brief e a F-n.

## Antes de escrever

1. Leia `specs/constitution.md` e `specs/steering/`, e respeite todos os princípios.
2. Leia `.claude/sdd.json` para conhecer os módulos, e o arquivo de `instructions/` de cada
   módulo que a feature tocar.
3. Use o número `<NNN>` da branch definido no passo "Branch e pasta da feature".
4. Procure specs existentes que a feature altere ou contradiga e cite-as. Para saber como o
   sistema se comporta hoje, leia em `specs/vivas/` (e nas pastas de `specs_vivas_externas` do
   `sdd.json`, que são de outros repositórios e só de leitura) só as capacidades que a feature toca.
5. **Classifique a cerimônia** (o humano confirma com `AskUserQuestion`, sugestão primeiro):
   - **trivial** — 1 módulo, sem contrato, sem dados, poucas linhas: pare e recomende `/corrigir` (serve para bug e para ajuste pequeno);
   - **media** — 1 a 2 módulos, sem migração nem contrato entre sistemas: spec curta, e o
     `/planejar` coloca as tarefas dentro do plano (uma aprovação a menos);
   - **grande** — contrato entre módulos ou sistemas, migração de dados, segurança, muitos
     arquivos: fluxo completo (`/planejar` e depois `/tarefas`).
   Registre na seção de contexto da spec: `**Classe:** <classe> (confirmada por <quem>)`.

## O arquivo

Crie `specs/<NNN>-<slug>-spec.md` (NNN em três dígitos, slug em kebab-case, sem acento) a partir
de `${CLAUDE_PLUGIN_ROOT}/templates/artefatos/spec.md`, mantendo `status: rascunho`.

Regras:

- **Sem solução técnica.** Nada de nomes de classe, tabela, rota, biblioteca ou arquivo. Isso é
  do plano.
- Declare os módulos afetados e as fronteiras cruzadas.
- Critérios de aceite em EARS ("Quando <evento>, o sistema deve <resposta>"), verificáveis,
  cada um citando ao menos um RF.
- Requisito não funcional sempre com número e unidade.
- **Ambiguidade vira pergunta.** Se algo essencial estiver ambíguo, pergunte com
  `AskUserQuestion` (no máximo 5 perguntas). O que continuar dependendo de decisão humana vai
  para "Questões em aberto"; nunca preencha lacuna com suposição.
- **Mudanças no comportamento vigente** (seção 8 do template): para cada capacidade de
  `specs/vivas/` que a feature cria ou muda, liste os requisitos `ADICIONADO`, `ALTERADO` (com o
  título exato do vivo) ou `REMOVIDO`. Ela alimenta a spec viva no fim da feature.
- Não altere nenhum arquivo além da spec criada.

## Depois de escrever

Rode `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py validar <NNN>` e corrija todo ERRO (ids, CA sem RF, formato das
mudanças). Só então chame o agente `revisor-de-spec` sobre o arquivo e aplique as correções que forem só de
escrita. O que for decisão vira questão em aberto.

Termine dizendo ao humano: o caminho da spec, as questões em aberto, e que o próximo passo é
revisar, trocar o status para `aprovado` e commitar; só então `/planejar <NNN>` é liberado.
Sugira o commit da aprovação (`git add specs/<NNN>-<slug>-spec.md` e
`git commit -m "spec <NNN>: <título>"`), conforme `${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md`.
Nunca escreva `status: aprovado`.
