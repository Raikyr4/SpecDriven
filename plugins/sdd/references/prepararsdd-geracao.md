# /prepararsdd — geração e relatório final

Lido pelo `/prepararsdd` só depois que o humano confirmou a proposta (passo 3). Os passos 1 a 3
(diagnóstico, entrevista, proposta, base e onde gerar) estão no comando.

## 4. Geração

**Primeiro passo, antes de criar ou alterar qualquer arquivo: a branch de adoção**, se o humano
escolheu criá-la no passo 7. Se escolheu manter na branch atual, faça só o item 1 e siga.

1. `git status --porcelain`. Se houver alterações locais, pare e peça ao humano para
   guardá-las ou commitá-las antes; não gere nada.
2. Se a base existe no remoto, `git fetch origin <base>` e confira com `git status -sb` que a
   base local não está atrás de `origin/<base>`; se estiver, peça ao humano `git pull` e pare.
3. `git switch -c sdd/adocao` (a partir da base, que é a branch atual).
4. Confirme com `git rev-parse --abbrev-ref HEAD` que está em `sdd/adocao`. Se o comando foi
   negado ou falhou, **pare** e dê ao humano o comando exato para ele rodar; não gere os
   arquivos na base.

Com a confirmação, crie a partir dos templates, preenchendo com o que você descobriu e o que
o humano respondeu. Nada de placeholder `<...>` onde você já tem a informação; onde não tem,
deixe o placeholder e liste-o no relatório final.

**Contexto enxuto.** `CLAUDE.md`, `specs/steering/` e `instructions/` são lidos em toda sessão ou
em todo comando, então cada linha custa tokens sempre:

- Escreva só o que o agente **não** descobre barato lendo o código: intenção, regras, fronteiras,
  armadilhas já vistas, comandos de build e teste. Não copie árvore de pastas, lista de arquivos,
  versões de pacote ou resumos que o código já mostra; aponte o caminho.
- Nada que mude a cada feature (datas, contagens, status, listas de features): isso desatualiza
  e quebra o cache do prompt. O que muda fica em `specs/`.
- Uma regra mora em um lugar só. Se já está na constituição, `CLAUDE.md` e `instructions/` não a
  repetem.
- Meta: `CLAUDE.md` até ~60 linhas; cada `instructions/<módulo>.md` até ~40.

1. `CLAUDE.md` (template `CLAUDE.md`), com stack, comandos e estrutura reais.
2. `specs/constitution.md` (template `constitution.md`). Em projeto existente, derive a stack,
   as fronteiras e os invariantes do que o código já impõe, e registre como "Questões em
   aberto" ao fim do arquivo o que não deu para inferir. A constituição nasce em rascunho:
   ela é aprovada pelo humano com um commit.
3. `specs/steering/produto.md`, `tecnologia.md`, `estrutura.md`.
4. `instructions/<módulo>.md` para cada módulo (template `instructions/modulo.md`).
5. `.sdd/sdd_gate.py`: cópia exata de `${CLAUDE_PLUGIN_ROOT}/hooks/sdd_gate.py`
   (`mkdir -p .sdd && cp "${CLAUDE_PLUGIN_ROOT}/hooks/sdd_gate.py" .sdd/`).
   Não redigite o arquivo. Se a cópia for negada, dê ao humano esse comando exato para ele rodar.
6. O check de pull request, conforme onde o projeto está hospedado (veja `git remote -v`):
   - **GitHub:** `.github/workflows/sdd-gate.yml` (template `github/workflows/sdd-gate.yml`) e
     `.github/pull_request_template.md` se não existir.
   - **Azure DevOps** (remote com `dev.azure.com` ou `visualstudio.com`):
     `azure-pipelines.sdd.yml` na raiz (template `azure/azure-pipelines.sdd.yml`) e
     `.azuredevops/pull_request_template.md` (mesmo conteúdo de
     `github/pull_request_template.md`) se não existir. Explique ao humano que, no Azure Repos,
     o pipeline precisa ser criado a partir desse arquivo e adicionado como **Build validation**
     obrigatório na política da branch principal (o passo a passo está no comentário do arquivo).
   - Outro host ou sem remote: pergunte ao humano qual CI usar e mostre o comando
     `python .sdd/sdd_gate.py ci --base origin/<base>` com checkout completo.
7. `.claude/settings.json` a partir do template `settings.json`, trocando `__MARKETPLACE__`
   e `__URL_DO_REPOSITORIO__` pelos valores de `padrao.json` (`marketplace` e
   `url_do_repositorio`). Se já existir, proponha só a fusão das
   chaves `extraKnownMarketplaces` e `enabledPlugins`. Isso faz o Claude Code de quem clonar
   o projeto oferecer a instalação do plugin.
8. **Por último**, `.claude/sdd.json` com os módulos, extensões, comandos de verificação, o
   modo escolhido e `"branch_principal": "<base>"` (a branch base do passo 6 do diagnóstico).
   Preencha `areas_sensiveis` com as pastas ou globs de autenticação, pagamentos, dados pessoais e
   segredos que o diagnóstico encontrou (vazio se não houver); elas fazem o `revisao` pedir o
   revisor de segurança. A partir deste arquivo o gate passa a valer neste projeto.

Em projeto existente, ofereça como passo seguinte (depois que a constituição for aprovada,
porque o gate só libera specs a partir daí): reconstruir a spec do estado atual de um módulo
com o agente `minerador-de-specs`, gravando `specs/000-estado-atual-<módulo>-spec.md` em
rascunho.

## 5. Relatório final

Responda com:

- o que foi criado e o que foi alterado;
- os placeholders que ficaram para o humano preencher;
- os avisos do diagnóstico: `CLAUDE.md` de pasta acima que conflita, módulos sem testes;
- os próximos passos, nesta ordem:
  1. revisar e preencher `specs/constitution.md`, trocar o status dela para `aprovado` e
     commitar tudo na branch `sdd/adocao` (ou na própria base, se a adoção ficou nela);
  2. com branch de adoção: `git push -u origin sdd/adocao` e abrir o PR de adoção para a base
     (`<base>`); sem branch de adoção: `git push` da base;
  3. criar o pipeline do check (Azure: a partir de `azure-pipelines.sdd.yml`, que já está na
     branch) e ativar a proteção da base exigindo esse check (GitHub: status check
     `sdd-gate`; Azure: Build validation) e um revisor;
  4. com branch de adoção, depois do merge do PR voltar para a base atualizada
     (`git switch <base> && git pull`); então começar a primeira feature com `/especificar`.
- o commit e o PR de adoção prontos para copiar, conforme `${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md`: `git add` dos
  arquivos gerados, `git commit -m "sdd: adota o padrão SDD no projeto"` e, com branch de
  adoção, o título `Adoção do padrão SDD` e a descrição (o que foi gerado, avisos do
  diagnóstico, questões em aberto da constituição e os passos de configuração do pipeline).

Não commite. Não marque nada como `aprovado`.
