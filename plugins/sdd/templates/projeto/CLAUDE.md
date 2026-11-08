# <Nome do projeto>

<Uma frase: o que o sistema faz e para quem. Estado atual em uma linha.>

## Stack
- <Linguagem/framework e versão> — <papel no sistema>

## Comandos
| Módulo | Build | Teste | Diretório |
| --- | --- | --- | --- |
| <módulo> | `<comando>` | `<comando>` | `/<caminho>` |

## Estrutura
- `/<caminho>` — <responsabilidade do módulo>

## Convenções
- <Regra que o código já segue e o agente precisa respeitar.>
- Nunca commitar credenciais, `.env`, connection strings ou binários pesados.
- **Contexto dinâmico:** ao atuar em um módulo, é OBRIGATÓRIO ler o arquivo dele em
  `/instructions` antes de planejar ou alterar código.

## Fluxo de trabalho (padrão SDD)
Toda mudança relevante segue `/especificar` → `/planejar` → `/tarefas` → `/implementar` →
`/verificar`, com revisão humana entre as fases. Bug pequeno usa `/corrigir`. Artefatos em
`specs/`; princípios em `specs/constitution.md`; contexto de produto, tecnologia e estrutura
em `specs/steering/`.

O gate do plugin `sdd` bloqueia cada fase até o artefato anterior estar commitado e com
`status: aprovado`, e bloqueia código de módulo sem tarefa aprovada e pendente. Configuração
em `.claude/sdd.json`. **Nunca marque `aprovado` por conta própria e nunca commite sem pedido
explícito do humano.** Ao terminar algo que deva ser commitado, sugira a mensagem de commit
(e, na hora do PR, título e descrição), sem `Co-Authored-By`, `Claude-Session` nem menção a IA.
