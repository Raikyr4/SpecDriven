---
description: "Passo 0: prepara seu projeto (novo ou existente) para SDD. Rode na branch base, uma vez por projeto."
argument-hint: "<pasta do projeto>"
allowed-tools: Read, Glob, Grep, Write, Edit, AskUserQuestion, Bash(git status:*), Bash(git fetch:*), Bash(git switch -c:*), Bash(git rev-parse:*), Bash(git branch:*), Bash(git remote:*), Bash(git ls-remote:*), Bash(mkdir:*), Bash(cp:*), Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/py.sh *)
---

Prepare o diretório abaixo para o padrão SDD da empresa:

$ARGUMENTS

Se nenhum diretório foi informado, use o diretório atual e diga que fez isso.

Materiais do padrão (somente leitura, nunca altere):

- Templates do projeto: `${CLAUDE_PLUGIN_ROOT}/templates/projeto/`
- Templates de artefatos: `${CLAUDE_PLUGIN_ROOT}/templates/artefatos/`
- Gate: `${CLAUDE_PLUGIN_ROOT}/hooks/sdd_gate.py`
- Identificação do padrão: `${CLAUDE_PLUGIN_ROOT}/padrao.json` (repositório e nome do marketplace)

## 1. Diagnóstico (não escreva nada ainda)

1. Se o diretório não existir ou estiver vazio, é **projeto novo**. Caso contrário, é
   **projeto existente**.
2. Em projeto existente, mapeie sem ler arquivo por arquivo:
   - manifestos e stack (`*.csproj`, `*.sln*`, `package.json`, `pyproject.toml`, `pom.xml`,
     `build.gradle*`, `go.mod`, `Cargo.toml`, `pubspec.yaml`, `CMakeLists.txt`...);
   - módulos (pastas de primeiro e segundo nível com manifesto ou código próprio);
   - comandos de build e teste de cada módulo (README, scripts, pipelines de CI);
   - testes existentes, CI (`.github/workflows`, `azure-pipelines.yml`), `.gitignore`;
   - o que já existe do padrão ou parecido: `CLAUDE.md`, `.claude/`, `specs/`, `docs/adr/`,
     `instructions/`, `constitution.md`.
3. Procure `CLAUDE.md` nas pastas acima do diretório, até a raiz do disco ou do repositório
   pai. O Claude Code carrega esses arquivos junto com o do projeto. Se algum descrever outra
   stack, outro produto ou regras que conflitem com este projeto, avise o humano no relatório
   e sugira mover o conteúdo para o projeto a que ele pertence, ou declarar no `CLAUDE.md` do
   projeto que ele prevalece sobre os das pastas acima. Não altere arquivos fora do diretório.
4. Anote se o projeto tem testes automatizados por módulo. Projeto sem testes é **legado sem
   testes**: o padrão vale do mesmo jeito, mas a constituição registra isso como questão em
   aberto (qual framework adotar) e o primeiro `/tarefas` de cada módulo começa criando o
   projeto de testes. Não crie o projeto de testes agora.
5. Verifique se é um repositório git. Se não for, diga ao humano que o gate depende de
   commits e pergunte se ele quer rodar `git init` (você não roda).
6. **Branch base.** A branch em que o diretório está agora (`git rev-parse --abbrev-ref HEAD`)
   é a **base** do projeto: é dela que saem as branches de adoção e de feature, é para ela que
   vão os PRs, e é contra ela que o gate confere sincronia e numeração. Ela vai para
   `branch_principal` no `.claude/sdd.json`. Não troque pela `main` nem pelo HEAD do remoto.
   Exceções: se o diretório estiver numa branch `sdd/...`, `feat/...` ou `fix/...`, ou em HEAD
   destacado, pergunte qual é a base. Anote também se a base existe no remoto
   (`git ls-remote --heads origin <base>`).
7. **Onde gerar.** Pergunte com `AskUserQuestion` (junto com a entrevista do passo 2):
   - **Criar a branch de adoção (recomendado):** os arquivos vão para a branch nova
     `sdd/adocao` (ou `sdd/adocao-<base>` se esse nome já existir), criada a partir da base, e
     entram na base por pull request;
   - **Manter na branch atual:** os arquivos são gerados na própria base, sem branch nova; o
     humano revisa e commita ali mesmo.

## 2. Entrevista curta

Use `AskUserQuestion` para confirmar, de uma vez, o que não deu para inferir. No máximo
cinco perguntas. Para projeto novo, pergunte no mínimo:

- propósito do sistema e usuários;
- stack e módulos (nome, caminho, linguagem);
- comandos de build e teste de cada módulo;
- modo do gate: `bloqueio` (padrão) ou `aviso` (adoção gradual em projeto existente).

Para projeto existente, mostre o que inferiu (módulos, comandos, stack) e peça só correções.

## 3. Proposta

Antes de escrever, apresente a lista de arquivos que serão **criados** e os que serão
**alterados**, com uma linha sobre cada. Regras:

- **Nunca sobrescreva** `CLAUDE.md`, `specs/constitution.md`, specs, `instructions/`,
  `.claude/settings.json` ou workflows existentes. Para esses, proponha o acréscimo exato
  (a seção que falta) e aplique só o que o humano aceitar.
- Se já há instruções para agentes com conteúdo (`CLAUDE.md`, `AGENTS.md`, `instructions/`,
  regras de outra ferramenta), leia `${CLAUDE_PLUGIN_ROOT}/references/ledger-de-instrucoes.md` e
  inclua na proposta o ledger: cada instrução com destino (manter, reescrever, mover, automatizar,
  remover) e motivo.
- `.gitignore`: acrescente apenas as linhas de `gitignore-sdd` que ainda não existem, e
  pergunte antes de incluir padrões que possam pegar arquivos legítimos do projeto (ex.: `*.bin`).

Inclua no topo da proposta a base e onde os arquivos serão gerados, conforme a resposta do
passo 7, por exemplo: "Base: `release/2026` (branch atual). Os arquivos serão gerados na branch
nova `sdd/adocao`, criada a partir dela, e o PR de adoção vai para `release/2026`." ou "Base:
`release/2026` (branch atual). Os arquivos serão gerados nela mesma, sem branch de adoção."

Espere a confirmação do humano.

## 4. Geração e 5. Relatório final

Só depois da confirmação do humano, leia `${CLAUDE_PLUGIN_ROOT}/references/prepararsdd-geracao.md`
e siga-o: ele cria a branch de adoção (se escolhida), gera os arquivos na ordem certa
(`.claude/sdd.json` por último) e monta o relatório final com o commit e o PR sugeridos conforme
`${CLAUDE_PLUGIN_ROOT}/templates/mensagens.md`.

Não commite. Não marque nada como `aprovado`.
