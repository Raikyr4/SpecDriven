---
description: "Passo 5: antes de abrir o PR, roda build, testes, segurança e critérios de aceite e diz se está pronto (PASS/FAIL)."
argument-hint: "<número da feature, ex.: 004>"
---

Verifique a feature indicada por: $ARGUMENTS

Use os comandos de `.claude/sdd.json` de cada módulo tocado. Pare no primeiro vermelho que impeça
os seguintes. O relatório tem três dimensões:

**Correção — o código funciona e é seguro**

1. **Build** sem erros e sem avisos; **lint / tipos** quando o módulo tiver.
2. **Testes** do módulo, gerando resultado em arquivo: TRX no .NET
   (`dotnet test --logger trx --results-directory TestResults`), JUnit XML no JS/Python
   (Vitest `--reporter=junit --outputFile=...`, pytest `--junitxml=...`).
3. **Revisão:** `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py revisao --base principal` grava o diff da branch e
   indica os revisores. Rode o `revisor-de-seguranca` se indicado, com o caminho do diff. Se o
   humano pedir revisão completa, rode em paralelo três `revisor-de-codigo`, cada um com um foco:
   `bordas`, `lacunas de teste` e `intenção` (a spec), todos com o caminho do diff.
4. **Verificações desligadas:** o gate já barra os padrões conhecidos; confira o diff mesmo assim.

**Completude — tudo o que foi pedido está feito**

5. **Critérios de aceite:** `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py cobertura <NNN> --resultados <arquivos do passo 2>`.
   A tabela CA → teste → resultado vem do script; CA sem teste, com teste falhando ou ignorado é
   **FAIL**. Não reconstrua a tabela lendo arquivos.
6. **Tarefas:** todas `[x]` têm código e teste; nenhuma `[ ]` esquecida no escopo do PR.
7. **Spec viva:** `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py consolidar <NNN> --verificar`. Se acusar pendência, rode
   `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py consolidar <NNN>` (só grava em `specs/vivas/`), mostre o diff e inclua esses
   arquivos no commit sugerido. O check do PR falha com a feature concluída e a spec viva desatualizada.

**Coerência — bate com o que foi decidido**

8. **Plano e ADRs:** os arquivos alterados correspondem às unidades do plano; as ADRs citadas no
   plano estão `aceita` (ADR ainda `proposta` é **FAIL**: o humano troca e commita).
9. **Gate do PR:** `git fetch origin` e `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py ci` (sem `--base`, usa `branch_principal`). Branch
   atrás da base é **FAIL**: o humano traz a base (`git merge <base>`, ref de `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py base`), resolve
   conflitos e commita, e a verificação roda de novo.

Relatório: uma tabela `Dimensão | Verificação | Resultado | Evidência` com a saída decisiva de cada
comando, a tabela de cobertura do passo 5 e o veredito **PASS** ou **FAIL** com o que falta.
Não corrija nada nesta fase sem pedido do humano.

Com **PASS**, sugira o PR conforme `${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md`: o comando de push, o título
`<NNN> <título>` e a descrição pronta, preenchendo o template de PR do projeto com a spec,
as tarefas, as ADRs aceitas e a saída decisiva desta verificação. Com **FAIL** por branch
atrasada, sugira o commit do merge (`merge: atualiza <branch> com <base>`).
