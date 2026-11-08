# Execução assíncrona do `/implementar` com Paperclip (opcional)

> **Experimental. Não foi exercitada com agentes reais.** O servidor Paperclip 2026.1106.0 foi
> instalado e rodou nesta máquina, mas nenhum agente foi contratado nem executado. Use só depois da
> Fase 4 da pesquisa mostrar que o gargalo é "babá" de sessões, não qualidade.

## O que isto resolve

Hoje cada tarefa aprovada espera alguém abrir o Claude Code e rodar `/implementar <NNN>`. Com o
Paperclip, uma tarefa do Paperclip por feature acorda um agente Claude Code (adaptador
`claude_local`) que implementa **uma** tarefa SDD por heartbeat e para para revisão humana. O que
não muda:

- o gate continua valendo no agente: código só com tarefa aprovada, sem `status: aprovado`, sem
  commit (`agente_pode_commitar: false`), sem supressões;
- aprovação e commit continuam humanos; o check de PR continua sendo a barreira final.

```text
Humano aprova tarefas (commit) ──► cria/atribui tarefa no Paperclip "SDD 004"
Paperclip (wake por atribuição) ──► Claude Code no worktree da feature
   contexto 004 → implementa 1 tarefa → testes → revisao → marca [x] → medir
   ──► comentário + work product (arquivos) + status in_review
Humano revisa o diff, commita, e devolve a tarefa (in_progress) para a próxima ──► repete
Sem tarefas pendentes ──► agente marca done e sugere /verificar
```

## Configuração

1. Servidor: `npx paperclipai@latest onboard --yes --no-install-service` (no Windows não há
   serviço; suba com `npx paperclipai run`). UI em `http://127.0.0.1:3100`.
2. Projeto no Paperclip ligado ao repositório. Prefira **workspaces isolados** (git worktree por
   tarefa) para não misturar o trabalho do agente com a sua pasta.
3. Contrate um agente com adaptador `claude_local`:
   - `cwd`: a raiz do projeto (ou o worktree da feature);
   - política de heartbeat: `wakeOnAssignment` ligado, `timer` **desligado** (sem polling);
   - `maxTurns` ~60 e `timeoutSec` ~1800;
   - orçamento mensal por agente (ex.: US$ 50) com aviso em 80%;
   - instruções: o conteúdo de [`instrucoes-agente.md`](instrucoes-agente.md);
   - plugin `sdd` instalado para o usuário que roda o Paperclip (o hook precisa estar ativo).
4. No Claude Code do host, o plugin precisa estar habilitado: `claude plugin list` mostra
   `sdd@specdriven` como `enabled`.

## Riscos e cuidados

| Risco | Mitigação |
| --- | --- |
| O adaptador usa `dangerouslySkipPermissions: true` por padrão | Rode em worktree isolado; o hook do gate continua negando o que importa; considere sandbox |
| `--setting-sources user` em conexões gerenciadas pode não carregar configurações do projeto | Verifique na primeira run que o hook bloqueia código sem tarefa (faça o teste negativo) |
| Dois estados (caixa `[x]` no SDD e status no Paperclip) | O SDD é a fonte de verdade; o Paperclip só reflete |
| Custo de protocolo por heartbeat (Skill `paperclip` grande, chamadas de controle) | Uma tarefa SDD por heartbeat, wake só por atribuição; compare com `/medir` e com o benchmark |

## Verificação mínima antes de usar de verdade

1. Tarefa do Paperclip para uma feature **sem** tarefas aprovadas: o agente precisa terminar
   `blocked` dizendo que o gate negou, sem escrever código.
2. Feature com plano compacto aprovado (use `evals/extras/001`): o agente implementa T-1, deixa a
   caixa marcada, não commita e passa a tarefa para `in_review`.
3. Compare tokens e tempo com o mesmo caso rodado por `evals/rodar_evals.py --caso implementar`.
