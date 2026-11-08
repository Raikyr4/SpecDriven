# SpecDriven

Padrão de **Spec-Driven Development (SDD)** da empresa para o Claude Code. Os agentes de IA
escrevem a especificação, o plano, as tarefas e o código; uma pessoa aprova cada fase antes da
seguinte começar, e o gate de fases impõe essa ordem na máquina do dev e no pull request.

```text
/prepararsdd → constituição ─(aprovação)→ /especificar ─(aprovação)→ /planejar ─(aprovação)→
/tarefas ─(aprovação)→ /implementar → /verificar ─(revisão do PR + check sdd-gate)→ merge
```

## Instalação

Pré-requisitos: Claude Code 2.1 ou mais novo, Git, Python 3.8+ no `PATH` e, no Windows, Git Bash
(que já vem com o Git for Windows).

> **O Claude Code do terminal é um requisito à parte.** O app Claude Desktop não instala o
> comando `claude`; são produtos independentes. A instalação e a verificação do plugin usam o
> CLI (`claude plugin ...`), então instale o Claude Code no terminal antes (veja
> [a documentação oficial](https://code.claude.com/docs/en/setup)) e confirme com
> `claude --version`, que deve mostrar 2.1 ou mais novo.
>
> Para a instalação automática pelo [AGENTS.md](AGENTS.md), a versão mínima é a **2.1.277**
> (18/09/2026), que passou a ler o `AGENTS.md` quando o projeto não tem `CLAUDE.md`. Em Amazon
> Bedrock, Google Vertex AI, Microsoft Foundry, gateway de LLM ou sessão com telemetria
> desligada, use a **2.1.281** (23/09/2026) ou mais nova. Em versão mais antiga o arquivo é
> ignorado e o plugin precisa ser instalado pela "Instalação manual" abaixo. Fonte: o
> [changelog oficial](https://code.claude.com/docs/en/changelog).

Basta **clonar este repositório e abrir o Claude Code nele**. O agente lê o
[AGENTS.md](AGENTS.md) e faz a instalação por você:

```bash
git clone https://github.com/Raikyr4/SpecDriven.git
cd SpecDriven
claude
```

Na primeira resposta da sessão, o agente confere o ambiente e avisa o resultado em uma ou duas
linhas. Se o plugin `sdd` não estiver instalado, ele pergunta e **só instala depois da sua
confirmação**, pelo CLI (`claude plugin marketplace add` e `claude plugin install`). Em seguida
valida Git, Python 3.8+, Claude Code 2.1+ e os testes do gate
(`python -m unittest discover -s tests`), parando e mostrando o erro se algo falhar.

Depois da instalação, a sessão em andamento só vê os comandos após `/reload-plugins` ou numa
sessão nova. Confira que `/especificar` e `/situacao` aparecem ao digitar `/`. O plugin fica
instalado para o usuário, então vale para todos os projetos da máquina.

- **Repositório público** ([github.com/Raikyr4/SpecDriven](https://github.com/Raikyr4/SpecDriven)):
  clonar e instalar o plugin não pedem login.
- **Se a sessão não leu o `AGENTS.md`:** peça "leia o AGENTS.md". O `/memory` não está
  disponível no app desktop do Claude, na aba Code; no terminal ele lista os arquivos
  carregados.
- **Atualizar:** `claude plugin marketplace update sdd-padrao`.

### Instalação manual (alternativa)

Só se não quiser usar o `AGENTS.md`. Instale **pelo CLI**, não pelo comando `/plugin`: no app
desktop do Claude, `/plugin` abre uma tela de gerenciamento e descarta os argumentos.

```bash
claude plugin marketplace add https://github.com/Raikyr4/SpecDriven.git
claude plugin install sdd@sdd-padrao
claude plugin list
```

`sdd@sdd-padrao` deve aparecer com `Status: enabled`.

Projetos que já passaram pelo `/prepararsdd` trazem em `.claude/settings.json` a referência a
este marketplace, então quem clonar o projeto recebe a oferta de instalar o plugin ao abrir o
Claude Code.

## Uso

| Comando | Fase | O que faz |
| --- | --- | --- |
| `/prepararsdd <dir>` | Preparação | Cria ou melhora a estrutura SDD no diretório (projeto novo ou existente) |
| `/descobrir [modo] <ideia>` | Descoberta (opcional) | Ideia vaga → brief em `docs/descoberta/`; modos `brainstorm`, `prfaq` e `prd` (fatia a iniciativa em features) |
| `/constituicao` | Preparação | Cria a constituição ou propõe emenda datada |
| `/especificar <necessidade>` | Spec | Escreve a spec (o QUE e por quê) com critérios EARS; a necessidade vem em texto, anexo, arquivo `.md`/`.docx`/`.pdf` ou pasta |
| `/esclarecer <NNN>` | Spec | Até 5 perguntas sobre lacunas, gravadas na spec |
| `/corrigir <descrição>` | Bug | Caminho curto: análise do bug e tarefas em um arquivo |
| `/planejar <NNN>` | Plano | Plano técnico: arquitetura, contratos, testes, riscos |
| `/tarefas <NNN>` | Tarefas | Tarefas T-n, um commit e um módulo cada |
| `/analisar <NNN>` | Tarefas | Consistência entre spec, plano e tarefas, sem alterar nada |
| `/implementar <NNN>` | Implementação | Uma tarefa por vez, teste primeiro, para revisão humana |
| `/verificar <NNN>` | Verificação | Build, testes, segurança e critérios de aceite: PASS/FAIL |
| `/situacao` | — | Situação das features e próximo número livre |
| `/medir [<NNN> <fase>]` | — | Tokens da sessão lidos do log; com a feature, registra o custo da fase em `specs/.metricas/` |

Os comandos também respondem com o prefixo do plugin, por exemplo `/sdd:prepararsdd`.

### De onde vem a necessidade do `/especificar`

A `<necessidade>` é o problema a resolver, quem tem e por que importa, não a solução. Ela pode
vir de qualquer combinação destas formas:

```text
/especificar O gestor precisa exportar o espelho de ponto do mês em PDF para assinatura
/especificar docs/necessidades/exportacao-espelho.docx
/especificar docs/necessidades/exportacao/            (lê todos os arquivos da pasta)
/especificar ata-reuniao.pdf e considere também que o prazo é de 30 dias
```

Arquivos `.md`, `.txt`, `.docx` e `.pdf` e pastas inteiras são lidos pelo script
`plugins/sdd/scripts/ler_fontes.py` (Python, só biblioteca padrão). PDF usa o `pdftotext`
quando ele existe na máquina; sem ele, o agente lê o PDF com a ferramenta Read do Claude Code.
Um PDF ou imagem anexado direto no prompt também vale. Formatos fora dessa lista (`.doc`
antigo, planilhas) são listados como ignorados e o agente avisa.

### Adotar o padrão num projeto existente

A branch em que o projeto está quando você roda o `/prepararsdd` vira a **base** do projeto
(`branch_principal` no `.claude/sdd.json`): dela saem as branches de adoção e de feature, para ela
vão os PRs, e contra ela o gate confere sincronia e numeração. Não precisa ser a `main`; para um
piloto, rode o `/prepararsdd` com o projeto na branch do piloto. O `/prepararsdd` pergunta onde gerar a
estrutura: numa branch de adoção (`sdd/adocao`, recomendado, que entra na base por PR) ou na
própria branch atual. Você revisa e aprova a constituição e commita. Com branch de adoção, abre o
PR e, depois do merge, começa as features a partir da base atualizada; sem ela, dá push na base e
já pode começar.

```text
main ─┬─ sdd/adocao: /prepararsdd → aprova constituição → commit → PR ─┐
      │                                                                ▼
      └──────────────────────────────── main com SDD ── /especificar → feat/001-...
```

### Features em paralelo

Cada feature tem a sua branch (`feat/NNN-slug`, ou `fix/NNN-slug` para bug) e, para trabalhar em
várias ao mesmo tempo, a sua pasta (`git worktree`) com a sua sessão do Claude Code. O
`/especificar` e o `/corrigir` criam isso para você a partir da branch principal atualizada.

- **Numeração:** o próximo número livre considera todas as branches, locais e remotas (nome da
  branch e arquivos em `specs/`). O check do PR falha se o número já pertence a outra feature
  na branch de destino.
- **Escopo do código:** numa branch `.../NNN-slug`, só as tarefas da feature NNN liberam código.
- **Mesmo módulo:** o `/situacao` lista as features em andamento em outras branches, com os
  módulos que cada uma toca, e avisa quando duas mexem no mesmo módulo.
- **Main em dia:** veja "O que o gate faz".

```text
D:\Projetos\MeuApp          main
D:\Projetos\MeuApp-004      feat/004-exportar-espelho   (sessão 1: /especificar)
D:\Projetos\MeuApp-005      feat/005-alerta-hora-extra  (sessão 2: /planejar 005)
D:\Projetos\MeuApp-006      fix/006-importacao          (sessão 3: /implementar 006)
```

Depois do merge de cada uma: `git worktree remove ..\MeuApp-NNN`.

### Projeto legado sem testes

O padrão vale do mesmo jeito. O `/prepararsdd` registra a falta de testes como questão em
aberto da constituição, e o primeiro `/tarefas` de cada módulo começa criando o projeto de
testes. Daí em diante, o código que uma tarefa altera ganha antes um teste de caracterização do
comportamento atual; não é preciso cobrir o legado inteiro.

O `/prepararsdd` também avisa quando um `CLAUDE.md` de pasta acima do projeto descreve outra
stack, porque o Claude Code carrega esses arquivos junto com o do projeto.

### Como a aprovação funciona

Cada artefato tem `status: rascunho` no frontmatter. Quem aprova troca para `status: aprovado`
e **commita**. O agente nunca escreve `aprovado` e nunca commita, então um artefato aprovado em
`HEAD` só pode ter sido promovido por uma pessoa.

Ao aprovar um plano que propõe ADRs em `docs/adr/`, troque também a **Situação** de cada ADR
de `proposta` para `aceita` (ou apague a ADR rejeitada e ajuste o plano) e commite as ADRs no
mesmo commit do plano. `/analisar` e `/verificar` apontam ADR que ficou `proposta`.

Todo comando que termina num ponto de commit sugere a mensagem pronta (`spec 004: …`,
`plan 004: …`, `task 004 T-2: …`), e o `/verificar` com PASS sugere título e descrição do PR.
A convenção está em `plugins/sdd/templates/mensagens.md`. As mensagens sugeridas nunca levam
`Co-Authored-By`, `Claude-Session` nem menção a IA.

| Artefato | Quem aprova |
| --- | --- |
| `specs/constitution.md` | Dev responsável |
| `specs/NNN-slug-spec.md` | Dono do produto ou dev responsável |
| `specs/NNN-slug-bug.md` | Dev responsável |
| `specs/NNN-slug-plan.md` | Dev responsável |
| `specs/NNN-slug-tasks.md` | Dev responsável |

### O que o gate faz

Na máquina do dev (hook `PreToolUse` do plugin, só em projetos com `.claude/sdd.json`):

- spec ou bug só depois da constituição aprovada; plano só com spec aprovada; tarefas só com
  plano aprovado; código de módulo só com tarefas (ou bug, ou plano com `## Tarefas`) aprovadas e
  com tarefa pendente;
- o agente não escreve `status: aprovado`, não commita, não usa `--no-verify`;
- escrever código que desativa aviso ou teste (`#pragma warning disable`, `skip`, `@ts-ignore`…)
  é bloqueado;
- editar artefato aprovado, a configuração do gate ou rodar git destrutivo pede confirmação.

No pull request (`.sdd/sdd_gate.py ci`, rodando em `azure-pipelines.sdd.yml` no Azure DevOps ou
em `.github/workflows/sdd-gate.yml` no GitHub):

- PR que altera código precisa marcar ao menos uma tarefa de um `-tasks.md`, `-bug.md` ou plano
  com `## Tarefas` aprovado, sem mudar o texto das tarefas depois de aprovadas;
- com todas as tarefas da feature marcadas, se a spec tem a seção "Mudanças no comportamento
  vigente", `specs/vivas/` precisa refletir essa seção (`sdd_gate.py consolidar <NNN>`);
- artefato em rascunho não entra no mesmo PR que código;
- linhas adicionadas não podem desativar verificação.
- a branch do PR precisa conter o último commit da branch de destino. Se outra feature entrou
  na `main` depois, o check falha e manda trazer a `main` antes (`git fetch origin` e
  `git merge origin/main`, depois build, testes, commit e push). Desligue com
  `"exigir_base_atualizada": false` em `.claude/sdd.json`.

A mesma regra aparece antes, na máquina do dev: `/especificar` e `/corrigir` começam com
`git fetch origin` e `sdd_gate.py sincronia` e param se você estiver na branch principal ou
numa branch atrasada; `/verificar` dá FAIL com a branch atrasada; e o hook nega `gh pr create` ou
`az repos pr create` nessa situação. Para checar à mão: `python .sdd/sdd_gate.py sincronia`
(0 em dia, 1 na principal ou atrasada, 2 sem `git fetch`). A branch principal vem de
`"branch_principal"` em `.claude/sdd.json` (padrão `main`).

### Descoberta (antes da spec)

Quando a ideia ainda é vaga (veio como solução, sem para quem, sem métrica) ou é grande demais
para uma spec, `/descobrir` conduz até 3 rodadas de perguntas e grava
`docs/descoberta/<slug>/brief.md`: problema, quem tem, por que agora, sucesso com número, escopo,
fora de escopo, riscos e perguntas abertas. Modos: `brainstorm` compara caminhos, `prfaq` testa
a ideia com um comunicado de lançamento e perguntas difíceis, e `prd` lista requisitos de
produto e features candidatas (F-n). O brief vira a entrada do `/especificar` (`/especificar
docs/descoberta/<slug>/brief.md F-2` especifica só a F-2). O brief não passa pelo gate, mas
o agente não pode marcá-lo como `aprovado`, e o `validar` confere a estrutura. Na classe grande,
o `/planejar` mostra 2 ou 3 alternativas para cada decisão estrutural antes de escrever
(`/planejar <NNN> alternativas` força isso em qualquer classe).

### Cerimônia proporcional

O `/especificar` classifica a mudança e você confirma: **trivial** vai para `/corrigir`;
**media** (1 a 2 módulos, sem migração nem contrato entre sistemas) tem as tarefas dentro do
plano, na seção `## Tarefas`, e o plano aprovado já libera o `/implementar` (uma aprovação a
menos); **grande** segue spec → plano → `/tarefas`. A classe fica registrada na spec.

### Specs vivas

`specs/vivas/<capacidade>.md` descreve como o sistema se comporta **hoje**, requisito por
requisito (`### Requisito: <título>`). Cada spec diz, na seção 8 "Mudanças no comportamento
vigente", o que adiciona, altera ou remove nessas capacidades. No `/verificar`,
`sdd_gate.py consolidar <NNN>` aplica a seção às specs vivas (é idempotente; `--verificar` só
confere) e o resultado vai no PR, revisado como qualquer arquivo. Assim, para saber o
comportamento atual de um módulo, lê-se uma spec viva em vez de várias specs antigas. Em projeto
existente, o agente `minerador-de-specs` escreve a spec viva inicial a partir do código.

### Validação de forma

`sdd_gate.py validar <NNN>` (ou o caminho de um artefato) checa sem LLM o que não precisa de
julgamento: ids repetidos, CA sem RF ou citando RF inexistente, CA fora de EARS (aviso), RNF sem
número (aviso), RF/CA da spec ausente no plano, tarefas sem módulo, origem ou `pronto:`,
dependências inexistentes, CA sem tarefa (aviso), plano acima de ~2.000 tokens (aviso) e seção de
mudanças malformada ou citando requisito vivo inexistente. Os comandos rodam a validação antes de
chamar os agentes revisores, que ficam com o que exige julgamento. Sai com 1 quando há ERRO.

Projetos já preparados recebem tudo isso pelo plugin; só o check de PR (spec viva consolidada e
plano com tarefas) depende de atualizar a cópia `.sdd/sdd_gate.py` a partir de
`plugins/sdd/hooks/`.

### Revisão proporcional e cobertura

`sdd_gate.py revisao` (no `/implementar`) e `revisao --base principal` (no `/verificar`) gravam o
diff num arquivo temporário e dizem se o `revisor-de-codigo` (diff acima de `limite_revisao`
linhas ou arquivo de código novo) e o `revisor-de-seguranca` (caminho em `areas_sensiveis` do
`sdd.json` ou termo sensível nas linhas adicionadas) são necessários. Os revisores recebem o
caminho do diff, não o texto. No `/verificar`, a revisão completa opcional roda três revisores
em paralelo, cada um com um foco: bordas, lacunas de teste e intenção.

`sdd_gate.py cobertura <NNN> --resultados <TRX ou JUnit XML>` monta a tabela CA → teste →
resultado. A convenção é o nome do teste conter `F<NNN>_CA_<n>` (ex.: `F004_CA_2_bloqueia`). CA sem
teste, com teste falhando ou ignorado faz o `/verificar` dar FAIL. O relatório do `/verificar` é
organizado em correção, completude e coerência.

### Medição e evals

`/medir` soma os tokens da sessão a partir do log do Claude Code (entrada nova, saída, gravação e
leitura de cache, chamadas e ferramentas), sem estimativa. `evals/` traz casos que rodam
`/especificar`, `/corrigir` e `/implementar` num projeto descartável e conferem o resultado com
`validar`, `cobertura`, testes e git, registrando tokens e custo (veja `evals/README.md`). Use os
dois para provar que uma mudança no plugin economiza sem piorar o resultado.

### Specs de outros repositórios

Quando outro time é dono de uma capacidade, aponte a pasta de specs vivas dele (checkout ao lado
ou submódulo) em `"specs_vivas_externas": ["../plataforma/specs/vivas"]`. O `/especificar` as lê
como referência e o `validar`/`consolidar` recusam mudanças nelas: a mudança vai por PR no
repositório dono.

### Execução assíncrona (experimental)

`integrations/paperclip/` descreve como um agente do Paperclip pode rodar o `/implementar` uma
tarefa por vez, acordado por atribuição, com o gate valendo e o commit continuando humano. Não foi
exercitado com agentes reais.

### Contexto mínimo por tarefa

O `/implementar` não relê spec, plano e constituição inteiros a cada tarefa. Ele roda
`sdd_gate.py contexto <NNN>` (versão do plugin, nada a atualizar nos projetos), que imprime a
próxima tarefa com dependências prontas, se a lista está liberada pelo gate, o módulo com o
`instructions/` e os comandos de verificação, e só os itens da spec (`RF`, `CA` que citam esses
`RF`…) e do plano (`U-n`, linhas de tabela) que a linha da tarefa cita. Os arquivos completos são
abertos só quando isso não basta. O comando usa a cópia do plugin; a cópia `.sdd/sdd_gate.py`
dos projetos só ganha o subcomando quando for atualizada a partir de `plugins/sdd/hooks/`. Para
ver à mão (com a cópia atualizada): `python .sdd/sdd_gate.py contexto 004` (`--json` para a forma
estruturada). Por isso vale escrever na linha da tarefa a `origem` e o
`módulo`, como o template já pede.

Projetos preparados antes da v0.1.4 precisam atualizar `.sdd/sdd_gate.py` e acrescentar
`--head` ao pipeline (veja os templates em `plugins/sdd/templates/projeto/`). Sem o `--head`, o
check de branch atualizada não funciona no Azure nem no GitHub, porque os dois fazem checkout
do commit de merge.

Ative a proteção da branch principal exigindo esse check e um revisor: é a camada que não pode
ser burlada. No Azure DevOps: crie um pipeline a partir de `azure-pipelines.sdd.yml` e adicione-o
como **Build validation** obrigatório na política da branch. No GitHub: exija o status check
`sdd-gate` na regra de proteção. Para adoção gradual, `"modo": "aviso"` em `.claude/sdd.json` transforma os
bloqueios de fase em avisos (a aprovação continua exclusiva do humano).

## Estrutura do repositório

```text
.claude-plugin/marketplace.json   catálogo do marketplace
plugins/sdd/
  .claude-plugin/plugin.json      manifesto do plugin
  commands/                       os comandos acima
  agents/                         revisor-de-spec, arquiteto, revisor-de-codigo,
                                  revisor-de-seguranca, minerador-de-specs
  hooks/                          hooks.json, sdd_gate.py (hook, ci, status, contexto)
  scripts/                        ler_fontes.py (texto de .md, .docx, .pdf e pastas)
  references/                     trechos lidos sob demanda pelos comandos (branch da feature,
                                  geração do /prepararsdd)
  templates/projeto/              CLAUDE.md, constituição, steering, instructions,
                                  sdd.json, settings.json, pipelines (Azure e GitHub),
                                  template de PR
  templates/artefatos/            spec, bug, plano, tarefas, checklist, ADR
  templates/mensagens.md          convenção das mensagens de commit e de PR sugeridas
  padrao.json                     URL do repositório e versão do padrão
tests/                            testes do gate, das referências, do tamanho dos comandos, do
                                  medidor e do runner de evals
evals/                            casos e runner dos evals dos comandos (gasta tokens)
integrations/paperclip/           execução assíncrona do /implementar (experimental)
docs/POP.md                       procedimento de uso (passo a passo)
```

## Desenvolvimento do padrão

```bash
python3 -m unittest discover -s tests -v   # testes do gate
claude plugin validate .                   # marketplace
claude plugin validate ./plugins/sdd       # plugin
python evals/rodar_evals.py --simular      # runner dos evals, sem Claude
python evals/rodar_evals.py                # evals de verdade (gasta tokens)
```

Mudanças no padrão seguem o próprio padrão: abra um PR, descreva o impacto nos projetos que já
usam e suba a `version` em `plugins/sdd/.claude-plugin/plugin.json`.
