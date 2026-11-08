---
feature: <NNN>-<slug>
fase: bug
status: rascunho
---

# Bug — <título curto>

Caminho curto do padrão SDD: análise do bug e tarefas no mesmo arquivo, com uma
aprovação humana antes da correção. Use só quando a correção não muda contrato,
modelo de dados nem comportamento combinado em outra spec. Caso contrário, use
`/especificar`.

## 1. Comportamento atual

<O que acontece hoje. Passos para reproduzir, entrada, saída observada, logs.>

## 2. Comportamento esperado

<O que deveria acontecer, citando a spec de origem quando existir (ex.: `specs/012-...-spec.md` CA-3).>

## 3. Comportamento que não pode mudar

<O que a correção não pode alterar. Vira teste de regressão junto com o do bug.>

## 4. Causa provável

<Hipótese com evidência (arquivo:linha, commit, log). Marque como hipótese se não confirmada.>

## 5. Critérios de aceite (EARS)

- **CA-1** — Quando <condição do bug>, o sistema deve <comportamento esperado>.
- **CA-2** — Quando <caso vizinho>, o sistema deve continuar <comportamento atual correto>.

## 6. Tarefas

- [ ] T-1 — Teste que reproduz o bug e falha hoje (CA-1). Pronto: teste vermelho pelo motivo certo.
- [ ] T-2 — Correção (CA-1, CA-2). Pronto: <comando de verificação do módulo> verde.

## 7. Questões em aberto

- <Se houver.>
