# Branch e pasta da feature

Lido por `/especificar` (prefixo `feat`) e `/corrigir` (prefixo `fix`). Abaixo, `<prefixo>` e
`<comando>` são os do comando que mandou ler este arquivo.

Cada feature (ou bug) tem a sua branch `<prefixo>/<NNN>-<slug>`. Para trabalhar em várias ao
mesmo tempo, cada uma tem também a sua pasta (`git worktree`) e a sua sessão do Claude Code.

1. Rode `git fetch origin` e depois
   `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py sincronia`.
   A **base** é a ref impressa por `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py base`
   (`origin/<branch_principal>` do `.claude/sdd.json`, ou a branch local quando ela não está no
   remoto). Nos comandos abaixo, `<base>` é essa ref e "branch principal" é essa branch.
   Confira também se a constituição já está aprovada na principal:
   `git show <base>:specs/constitution.md` deve conter `status: aprovado`. Se não
   contiver, o PR de adoção do padrão (`sdd/adocao`) ainda não entrou: pare e diga ao humano
   para concluí-lo primeiro, porque a feature precisa nascer de uma principal com a
   constituição aprovada. Só se ele pedir para seguir mesmo assim, use `sdd/adocao` no lugar de
   `<base>` nos comandos abaixo e avise que o PR da feature só pode ser aberto
   depois do merge da adoção.
2. **Saída 0 numa branch `.../<NNN>-<slug>`:** se `<NNN>` é deste trabalho (ou ainda não há
   artefato com esse número), siga com esse número. Se a branch é de outra feature, pare: diga
   que este trabalho precisa de branch própria e ofereça o passo 3 a partir da branch principal.
   Numa branch sem número (ex.: `hotfix`), siga usando o próximo número livre do `status` e
   sugira ao humano renomear a branch para `.../<NNN>-<slug>`.
3. **Saída 1 por estar na branch principal** (início normal): rode
   `sh "${CLAUDE_PLUGIN_ROOT}/scripts/py.sh" hooks/sdd_gate.py status` para obter o próximo número livre
   (ele considera todas as branches, locais e remotas) e proponha um slug curto. Pergunte com
   `AskUserQuestion` como trabalhar:
   - **Pasta separada (recomendado para paralelo):** rode
     `git worktree add "../<pasta do projeto>-<NNN>" -b <prefixo>/<NNN>-<slug> <base>`.
     Depois **pare**: diga ao humano para abrir um terminal na pasta nova, rodar `claude` e repetir
     `<comando> <os mesmos argumentos>`. Não escreva nada na pasta nova a partir desta sessão (o gate
     desta sessão vigia a pasta atual).
   - **Branch nesta pasta:** só com `git status --porcelain` vazio; rode
     `git switch -c <prefixo>/<NNN>-<slug> <base>` e siga.
4. **Saída 1 por atraso:** pare e mostre a mensagem com o `git merge` sugerido. Merge e pull são
   do humano; espere ele dizer que fez e rode a checagem de novo.
5. **Saída 2:** a branch principal não está no clone; peça ao humano para conferir o remote.

Se o `status` mostrar **ATENCAO** de sobreposição com um módulo que este trabalho vai tocar,
avise o humano antes de seguir: duas features no mesmo módulo ao mesmo tempo geram conflito no merge.

Terminado este passo, volte ao comando e siga a partir de onde ele mandou ler este arquivo.
