---
feature: <NNN>-<slug>
fase: tasks
status: rascunho
---

# Tarefas — <Título da feature>

Da spec `specs/<NNN>-<slug>-spec.md` e do plano `specs/<NNN>-<slug>-plan.md`
(aprovados, commits `<hash>` e `<hash>`).

**Ordem.** Ordenadas por dependência. Contratos de fronteira vêm antes de quem os consome.

## Tarefas

- [ ] T-1 — <título> · módulo <x> · origem RF-1 / plano U-1 · pronto: <teste X passa; build sem avisos>
- [ ] T-2 — <título> · módulo <x> · depende de T-1 · origem CA-2 · pronto: <...>

Regras desta lista:

- Uma tarefa = um commit atômico, um módulo. Exceção só quando dividir quebraria a
  branch principal, declarada na própria linha com o motivo.
- Toda tarefa com lógica nova traz o próprio teste. Não existe "escrever os testes depois".
- Critério de pronto verificável por comando.
