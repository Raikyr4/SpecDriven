# Instruções do agente implementador SDD (Paperclip)

Você implementa features de um projeto que segue o padrão SDD (plugin `sdd`). Siga o procedimento
de heartbeat da Skill `paperclip` (checkout, contexto, status com `X-Paperclip-Run-Id`) e, no
passo "fazer o trabalho", siga **apenas** o roteiro abaixo. Uma tarefa SDD por heartbeat.

## 1. Qual feature

A tarefa do Paperclip tem no título ou na descrição `SDD <NNN>` (ex.: `SDD 004`). Sem isso, deixe
um comentário pedindo o número e passe a tarefa para `in_review` com uma interação de pergunta.

## 2. Contexto mínimo

Rode `python .sdd/sdd_gate.py contexto <NNN>` na raiz do projeto. (A variável
`${CLAUDE_PLUGIN_ROOT}` só existe dentro dos comandos do plugin; aqui use a cópia do projeto,
que precisa ser da versão 0.1.22 ou mais nova: `python .sdd/sdd_gate.py status` avisa se não for.)

- `Lista liberada pelo gate: NAO` → marque a tarefa `blocked` com um `unblockDescriptor` para você
  mesmo e a ação "humano aprovar e commitar as tarefas da feature <NNN>". Não escreva código.
- Sem tarefas pendentes → comente "todas as tarefas da feature <NNN> estão feitas; próximo passo:
  `/verificar <NNN>`" e marque `done`.

## 3. Implementar uma tarefa

Siga as regras do comando `/implementar` do plugin (`commands/implementar.md`): teste primeiro com
`F<NNN>_CA_<n>` no nome, mínimo para passar, verificação do módulo verde, `revisao` para decidir
os revisores, marcar `- [x]` só com tudo verde. Se o gate negar uma escrita, **não contorne**:
relate no comentário e marque `blocked`.

## 4. Fechar o heartbeat

1. Se o script do plugin estiver acessível (procure `plugins/sdd/scripts/medir_sessao.py` ou
   `**/sdd/scripts/medir_sessao.py` em `~/.claude/plugins/`), registre o consumo:
   `python <caminho>/medir_sessao.py --registrar specs/.metricas/<NNN>.jsonl --feature <NNN> --fase implementar`.
   O Paperclip também registra tokens por run; não deixe de fechar o heartbeat por causa disso.
2. Comentário na tarefa do Paperclip com: a tarefa SDD feita, arquivos alterados, a saída decisiva
   dos testes, os achados dos revisores, o consumo (se registrado) e o bloco de commit sugerido
   (`git add ...` e `git commit -m "task <NNN> T-<n>: <título>"`). **Você não commita.**
3. Work product `workspace_file` apontando para os arquivos alterados, para o humano abrir o diff.
4. Status `in_review` (o revisor é o humano dono da feature). Não escolha a próxima tarefa: o
   humano commita e devolve a tarefa para `in_progress`, o que gera o próximo heartbeat.

## Nunca

Escrever `status: aprovado`, commitar, usar `--no-verify`, desativar teste ou aviso, editar
`.claude/sdd.json` ou `.sdd/`, nem trabalhar em outra feature que não a da tarefa.
