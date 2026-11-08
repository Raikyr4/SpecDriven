# Ledger das instruções existentes

Lido pelo `/prepararsdd` quando o projeto já tem `CLAUDE.md`, `AGENTS.md`, `.cursorrules`,
`.github/copilot-instructions.md`, `instructions/` ou documento parecido com conteúdo. O objetivo é
adotar o que existe sem perder nada e sem inchar o contexto lido em toda sessão.

As instruções existentes são o ponto de partida, nunca rascunho descartável. Para cada seção e
para cada regra independente, abra uma linha:

| # | Onde está | Instrução (resumo) | Destino | Motivo | Risco se sair |
| --- | --- | --- | --- | --- | --- |

**Destinos possíveis**

- **manter** — o agente erraria sem ela e ela não é derivável do código.
- **reescrever** — vale, mas está vaga, longa ou desatualizada; mostre o texto novo.
- **mover** — vale, mas só para um módulo ou uma fase: vai para `instructions/<módulo>.md`, a
  constituição ou o steering. O destino precisa ser lido por algum comando; mover para um arquivo
  que ninguém lê é apagar.
- **automatizar** — é uma checagem que um teste, lint, o gate ou o CI faz melhor (ex.: "não use
  `@ts-ignore`"). Indique onde; enquanto a automação não existir, mantenha.
- **remover** — só com um destes motivos: (1) o código mostra isso barato e de forma confiável
  (árvore de pastas, versões, lista de arquivos); (2) está errada ou desatualizada, com a evidência;
  (3) repete outra regra que fica; (4) o humano decidiu tirar.

Regras:

- Não leia documentos externos nem invente regras. O ledger cobre o que existe.
- Instruções de segurança, conformidade e governança nunca saem sem decisão explícita do humano.
- Em caso de dúvida entre manter e remover, mantenha.
- Mostre o ledger completo na proposta (passo 3 do `/prepararsdd`) e aplique só o que o humano
  aprovar, linha a linha se ele quiser. Nunca sobrescreva o arquivo original: proponha o texto
  final e as linhas movidas.
- No relatório final, diga quantas linhas cada destino recebeu e o tamanho do `CLAUDE.md` antes e
  depois (em linhas).
