# POP — Procedimento de uso do padrão SDD

Procedimento operacional do plugin `sdd` (v0.1.21) no Claude Code. Para a instalação e o
detalhe de cada regra, veja o [README](../README.md).

## Pré-requisitos

- Git, Python 3.8+ e, no Windows, Git Bash (vem com o Git for Windows).
- Claude Code (app desktop, aba Code, ou terminal) com o plugin `sdd` instalado. Para conferir,
  digite `/` numa sessão: `/especificar` e `/situacao` precisam aparecer.

### Quando o CLI `claude` (terminal) é necessário

O uso do dia a dia roda dentro do Claude Code, inclusive no app. O CLI só é necessário para:

| Para quê | Por quê |
| --- | --- |
| Instalar ou atualizar o plugin (`claude plugin marketplace add`, `claude plugin install`) | No app desktop, `/plugin` abre uma tela de gerenciamento e descarta os argumentos |
| `claude plugin validate` ao alterar o plugin | Só existe no CLI |
| Evals (`evals/rodar_evals.py`) | Rodam `claude -p` |
| Execução assíncrona com Paperclip | O agente do Paperclip chama o `claude` |

Sem o CLI: ao abrir um projeto que já passou pelo `/prepararsdd`, o Claude Code oferece instalar o
plugin (o projeto traz o marketplace em `.claude/settings.json`).

## 1. Preparar o projeto (uma vez)

1. Na branch base do projeto, rode `/prepararsdd <pasta>`.
2. Responda à entrevista e aprove a proposta (recomendado: branch de adoção `sdd/adocao`).
3. Revise `specs/constitution.md`, troque `status: rascunho` por `status: aprovado` e commite.
4. Abra o PR de adoção.
5. Crie o pipeline do check `sdd-gate` (Azure ou GitHub) e proteja a branch principal exigindo o
   check e um revisor.

## 2. Ideia ainda vaga (opcional)

`/descobrir <ideia>` → até 3 rodadas de perguntas → `docs/descoberta/<slug>/brief.md`.
Modos: `/descobrir brainstorm ...` (comparar caminhos), `/descobrir prfaq ...` (testar a ideia),
`/descobrir prd ...` (iniciativa grande, fatiada em features F-n). Depois:
`/especificar docs/descoberta/<slug>/brief.md` (ou `... F-<n>` para uma feature do PRD).

## 3. Cada feature

1. **Especificar** — `/especificar <necessidade>` (texto, arquivo `.md`/`.docx`/`.pdf` ou pasta).
   O agente cria a branch `feat/NNN-slug` e propõe a classe; você confirma:
   - **trivial** → use `/corrigir`;
   - **média** → as tarefas ficam dentro do plano;
   - **grande** → fluxo completo.

   Opcional: `/esclarecer NNN`. Revise a spec, troque para `aprovado` e commite.
2. **Planejar** — `/planejar NNN` (com `alternativas` para discutir opções antes). Revise; troque as ADRs de `proposta` para `aceita`; aprove o
   plano e commite plano e ADRs no mesmo commit.
3. **Tarefas** (só classe grande) — `/tarefas NNN`, aprove e commite. Opcional: `/analisar NNN`.
4. **Implementar** — `/implementar NNN`. O agente faz **uma** tarefa (teste primeiro) e para. Você
   revisa o diff e commita. Depois `/clear` e `/implementar NNN` de novo, até acabar.
5. **Verificar** — `/verificar NNN` → PASS ou FAIL. Com PASS, a spec viva é consolidada e o PR é
   sugerido. Abra o PR; o check `sdd-gate` e o revisor humano fecham.

**Bug pequeno:** `/corrigir <descrição>` → aprovar e commitar → `/implementar NNN` →
`/verificar NNN`.

**A qualquer momento:** `/situacao` (fase de cada feature, próximo número livre) e
`/medir NNN <fase>` (tokens gastos na fase).

## 4. Regras de ouro

- Só a pessoa aprova: trocar o status para `aprovado` **e** commitar. O agente nunca faz isso.
- Nunca desative teste, aviso ou lint para passar; o gate bloqueia.
- Features em paralelo: uma pasta (`git worktree`) e uma sessão por feature.
- Mantenha a branch em dia com a principal, senão o check do PR falha.

## 5. O que o padrão fornece

| Tipo | Itens |
| --- | --- |
| Comandos (13) | `/prepararsdd`, `/descobrir`, `/constituicao`, `/especificar`, `/esclarecer`, `/corrigir`, `/planejar`, `/tarefas`, `/analisar`, `/implementar`, `/verificar`, `/situacao`, `/medir` |
| Agentes revisores (5) | `revisor-de-spec`, `arquiteto`, `revisor-de-codigo` (focos: bordas, lacunas de teste, intenção), `revisor-de-seguranca`, `minerador-de-specs` |
| Gate local (hook) | Ordem das fases; código só com tarefa aprovada; agente não aprova nem commita; sem supressões nem `--no-verify`; confirmação em git destrutivo |
| Check de PR (CI) | Tarefa aprovada marcada; rascunho não entra com código; branch em dia; numeração única; spec viva consolidada |
| `sdd_gate.py` | `status`, `sincronia`, `base`, `ci`, `contexto`, `validar`, `consolidar`, `revisao`, `cobertura` |
| Scripts | `ler_fontes.py` (`.md`/`.docx`/`.pdf`/pastas), `medir_sessao.py` (tokens reais da sessão), `py.sh` |
| Templates de projeto | `CLAUDE.md`, constituição, steering, `instructions/`, `sdd.json`, `settings.json`, pipelines Azure/GitHub, template de PR, `.gitignore` |
| Templates de artefato | brief (descoberta), spec (EARS + mudanças no comportamento vigente), plano (com tarefas opcionais), tarefas, bug, checklist, ADR |
| Só no repositório do padrão | testes, `evals/` (exige o CLI), `integrations/paperclip/` (experimental) |
