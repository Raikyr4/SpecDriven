# Mensagens de commit e de PR sugeridas

Todo comando que termina numa etapa em que o humano precisa (ou deve) commitar sugere a
mensagem pronta. Quando chega a hora do PR, sugere o título e a descrição. Quem commita e
abre o PR continua sendo o humano.

## Regras

- Mensagem em português, no imperativo ou nominal, primeira linha com até 72 caracteres.
- Mostre o bloco pronto para copiar, com os caminhos exatos que entram no commit:
  ```
  git add <caminhos>
  git commit -m "<primeira linha>"
  ```
- **Nunca** inclua `Co-Authored-By`, `Claude-Session`, "Generated with Claude Code" ou
  qualquer outra menção a IA na mensagem de commit, no título ou na descrição do PR.
- Não invente número: use o `<NNN>` e o título da spec.

## Commits

| Momento | Primeira linha |
| --- | --- |
| Adoção do padrão (`/prepararsdd`) | `sdd: adota o padrão SDD no projeto` |
| Constituição aprovada | `constituicao: aprova a constituição do projeto` |
| Emenda da constituição | `constituicao: emenda <AAAA-MM-DD> - <resumo>` |
| Spec aprovada | `spec <NNN>: <título da feature>` |
| Plano aprovado (com ADRs) | `plan <NNN>: <título da feature>` |
| Tarefas aprovadas | `tasks <NNN>: <título da feature>` |
| Bug aprovado (`/corrigir`) | `bug <NNN>: <título do bug>` |
| Tarefa implementada | `task <NNN> T-<n>: <título da tarefa>` |
| Base trazida para a branch | `merge: atualiza <branch> com <base>` |
| Correção pedida pelo `/verificar` | `fix <NNN>: <o que foi corrigido>` |

## Pull request

- **Título:** `<NNN> <título da feature ou do bug>` (adoção: `Adoção do padrão SDD`).
- **Descrição:** siga o template de PR do projeto (`.azuredevops/` ou `.github/`
  `pull_request_template.md`), preenchido: caminho da spec e tarefas da PR, resumo em 2 ou 3
  linhas, ADRs aceitas, a saída decisiva do `/verificar` e o checklist do revisor.
- Comando sugerido (Azure Repos):
  ```
  git push -u origin <branch>
  az repos pr create --source-branch <branch> --target-branch <base> --title "<título>" --description "<descrição>"
  ```
  No GitHub: `gh pr create --base <base> --title "<título>" --body-file <arquivo>`.
