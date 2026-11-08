---
description: "Opcional após o passo 1: faz até 5 perguntas sobre lacunas da spec e grava suas respostas nela, antes de você aprová-la."
argument-hint: "<número da feature, ex.: 004>"
allowed-tools: Read, Glob, Grep, Edit, AskUserQuestion
---

Esclareça a spec da feature indicada por: $ARGUMENTS

Se não localizar `specs/<NNN>-*-spec.md`, liste o que existe em `specs/` e pergunte.
Se a spec já estiver aprovada, avise que alterá-la reabre a revisão e confirme antes.

1. Leia a spec, a constituição e o steering.
2. Encontre as lacunas que mais mudam o plano: escopo, regras de negócio, dados, permissões,
   erros e limites, requisitos não funcionais sem número, termos ambíguos, questões em aberto.
3. Faça **no máximo 5 perguntas**, uma decisão por pergunta, com opções de resposta quando
   couber, usando `AskUserQuestion`. Ordene da que mais impacta para a que menos impacta.
4. Grave cada resposta no lugar certo da spec (RF, CA, fora de escopo) e registre em uma seção
   "Esclarecimentos" no fim: data, pergunta, resposta. Remova das questões em aberto o que foi
   resolvido.

Não toque em outros arquivos. Não mude o status. Termine lembrando que a spec segue em
rascunho e que, ao aprová-la, o commit sugerido é `spec <NNN>: <título>` (veja
`${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md`).
