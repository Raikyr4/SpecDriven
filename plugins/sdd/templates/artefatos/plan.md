---
feature: <NNN>-<slug>
fase: plan
status: rascunho
---

# Plano — <Título da feature>

Da spec `specs/<NNN>-<slug>-spec.md` (aprovada, commit `<hash>`).

Alvo: 900 a 1600 tokens. Pronto para implementar quando cada unidade tem arquivo e ação, a ordem
respeita as dependências, todo CA tem teste, não há TBD nem contradição.

## 1. Arquitetura

Por módulo: camadas e arquivos criados ou alterados, e por quê.

| Módulo | Arquivo | Mudança | Origem (RF/CA) |
| --- | --- | --- | --- |
| <módulo> | <caminho> | <criar/alterar: o quê> | RF-1 |

## 2. Modelo de dados

<Entidades, campos, tipos, índices, migrations. "Sem mudança" quando for o caso.>

## 3. Contratos

Toda fronteira cruzada tem contrato explícito: rota HTTP, evento, comando, assinatura
pública. Entrada, saída, erros e versão.

## 4. Decisões e trade-offs

- **D-1** — <Decisão>. Alternativas consideradas: <...>. Por que esta: <...>.

## 5. Estratégia de testes

| Critério | Tipo de teste | Ferramenta | Onde |
| --- | --- | --- | --- |
| CA-1 | <unitário/integração/E2E> | <ferramenta> | <caminho> |

Todo módulo tocado tem cobertura. Todo CA da spec aparece nesta tabela.

## 6. Unidades de entrega

Quebra em unidades que cabem em um commit atômico por módulo (base para `/tarefas`).

- **U-1** — <descrição> (módulo <x>)

## 7. Riscos e pontos de decisão humana

- **R-1** — <Risco>. Mitigação: <...>.

## Tarefas

<Só na classe `media`; na `grande`, apague esta seção e use `/tarefas`. Mesmas regras de
`tasks.md`: uma tarefa = um commit, um módulo, com teste.>

- [ ] T-1 — <título> · módulo <x> · origem RF-1 / U-1 · pronto: <teste X passa; build sem avisos>
