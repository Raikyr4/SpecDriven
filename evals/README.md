# Evals dos comandos

Medem se uma mudança no plugin `sdd` mantém (ou melhora) **qualidade e custo** dos comandos.
Cada caso roda o comando de verdade com `claude -p` num projeto descartável (`fixture/`, Python +
unittest) e confere o resultado com verificações determinísticas (`validar`, `cobertura`,
testes, git).

| Caso | Comando | O que precisa acontecer |
| --- | --- | --- |
| `especificar` | `/sdd:especificar <necessidade>` | spec criada em rascunho, `validar` sem erro, branch `feat/NNN-...`, nenhum commit |
| `corrigir` | `/sdd:corrigir <bug>` | `-bug.md` com tarefas, `validar` sem erro, código intocado, nenhum commit |
| `implementar` | `/sdd:implementar 001` (plano compacto aprovado em `extras/001`) | T-1 marcada, testes `F001_CA_1`/`F001_CA_2`, suíte verde, cobertura ok, nenhum commit |

## Rodar

```bash
python evals/rodar_evals.py                       # todos os casos, 1 vez
python evals/rodar_evals.py --caso implementar --repeticoes 5
python evals/rodar_evals.py --simular             # sem Claude: testa só o runner
```

Requer o CLI `claude` no PATH, logado. Cada execução **gasta tokens de verdade**. O padrão é
`--permission-mode bypassPermissions` porque a pasta é temporária; o hook do gate continua
valendo. Troque com `--claude-args "..."`.

O resultado vai para `evals/resultados/<data>.json` (ignorado pelo git): tokens por tipo (entrada,
saída, gravação e leitura de cache), custo informado pelo CLI, tempo, turnos e cada verificação.

## Como usar numa mudança do plugin

1. Rode os casos afetados com `--repeticoes 5` **antes** da mudança e guarde o JSON.
2. Faça a mudança e rode de novo.
3. Compare a taxa de sucesso e a mediana de tokens. Uma mudança que reduz tokens e derruba a taxa
   de sucesso não entra. O protocolo completo de comparação está em
   `pesquisa-paperclip-bmad/benchmark-tokens.md`.

Para um caso novo: acrescente em `casos.json` (prompt, `extras` opcionais, `branch` opcional,
`limite_tokens` e verificações) e, se precisar de artefatos aprovados, uma pasta em `extras/`.
