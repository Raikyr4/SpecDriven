---
feature: <NNN>-<slug>
fase: checklist
status: rascunho
---

# Checklist de qualidade da spec — <Título>

Testa a escrita dos requisitos, não a implementação. Cada item falho vira ajuste na spec
ou uma questão em aberto.

## Clareza
- [ ] Todo termo vago ("rápido", "seguro", "amigável") tem número e unidade.
- [ ] Cada RF descreve um comportamento observável, sem solução técnica.

## Completude
- [ ] Todo RF tem ao menos um critério de aceite.
- [ ] Erros, entradas inválidas e limites estão especificados.
- [ ] Permissões e papéis estão definidos para cada ação.

## Consistência
- [ ] Nenhum RF contradiz a constituição ou outra spec aprovada.
- [ ] Os mesmos termos são usados para as mesmas coisas em todo o documento.

## Cobertura de borda
- [ ] Concorrência, volume máximo e dados ausentes têm comportamento definido.
- [ ] O que acontece quando uma dependência externa falha está definido.

## Rastreabilidade
- [ ] Cada CA cita o RF que verifica.
- [ ] Fora de escopo e questões em aberto estão preenchidos (ou "nenhum").
