---
feature: <NNN>-<slug>
fase: spec
status: rascunho
---

# <Título da feature>

## 1. Contexto e problema

<Qual problema existe hoje, para quem, e por que resolver agora. Sem solução técnica.>

**Fontes da necessidade:** <arquivos, pastas ou "texto do prompt" usados no `/especificar`>
**Módulos afetados:** <lista dos módulos de `.claude/sdd.json` que a feature toca>
**Fronteiras cruzadas:** <integrações entre módulos ou sistemas externos; "nenhuma" se for o caso>
**Classe:** <trivial | media | grande> (confirmada por <quem>)

## 2. User stories

- **US-1** — Como <papel>, quero <objetivo> para <benefício>.

## 3. Requisitos funcionais

- **RF-1** — <O sistema deve ...>

## 4. Requisitos não funcionais

- **RNF-1** — <desempenho, segurança, disponibilidade, privacidade, com número e unidade>

## 5. Critérios de aceite (EARS)

Cada critério é verificável e cita pelo menos um RF.

- **CA-1** (RF-1) — Quando <evento>, o sistema deve <resposta>.
- **CA-2** (RF-1) — Se <condição indesejada>, então o sistema deve <resposta>.
- **CA-3** (RF-1) — Enquanto <estado>, o sistema deve <comportamento>.

## 6. Fora de escopo

- <O que esta feature deliberadamente não faz.>

## 7. Questões em aberto

- **QA-1** — <Dúvida que depende de decisão humana. Não preencha com suposição.>

## 8. Mudanças no comportamento vigente

O que esta feature cria, muda ou remove nas specs vivas (`specs/vivas/<capacidade>.md`). No fim
da feature, `sdd_gate.py consolidar <NNN>` aplica esta seção. `ALTERADO` e `REMOVIDO` usam o
título exato do requisito vivo; o texto é o comportamento observável, sem solução técnica.

### Capacidade: <capacidade-em-kebab-case>
#### ADICIONADO
##### Requisito: <título curto e estável>
<Quando <evento>, o sistema deve <resposta>.>
#### ALTERADO
##### Requisito: <título exato do requisito vivo>
<Texto novo, completo.>
#### REMOVIDO
##### Requisito: <título exato do requisito vivo>
