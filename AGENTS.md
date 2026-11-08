# AGENTS.md

Instruções para agentes de IA que trabalham neste repositório (`sdd-padrao`), que é o
marketplace e o plugin `sdd` do Claude Code. Antes de qualquer tarefa, faça a validação inicial
abaixo. Detalhes do padrão estão no [README.md](README.md).

## Ao iniciar a sessão: avise o usuário

Na primeira resposta da sessão, antes de qualquer outra tarefa, faça a checagem rápida abaixo e
**avise o usuário** do resultado em uma ou duas linhas:

1. Rode `claude plugin list`. Se `sdd@sdd-padrao` não aparecer como `enabled`, diga:
   "O plugin `sdd` não está instalado. Ele é necessário para usar este projeto (comandos
   `/especificar`, `/planejar` e os demais). Posso instalar pelo CLI?" Só instale depois do
   usuário confirmar, seguindo "Instalar o plugin `sdd`".
2. Se o plugin está instalado mas `/especificar` não aparece nesta sessão, diga que é preciso
   `/reload-plugins` ou uma sessão nova.
3. Se estiver tudo certo, basta dizer que o ambiente SDD foi verificado.

Se o usuário suspeitar que esta sessão não leu o `AGENTS.md`, ele pode pedir "leia o AGENTS.md"
(o `/memory` não está disponível no app desktop do Claude, na aba Code; no terminal ele lista
os arquivos carregados).

## Validação inicial do ambiente

Rode os passos na ordem. Se um falhar, **pare e informe o usuário** com a saída do erro; não
tente contornar.

1. **Git:** `git --version` deve responder.
2. **Python 3.8+ no PATH:** `python --version` deve mostrar 3.8 ou mais novo.
   - No Windows, se aparecer "Python não foi encontrado", o atalho da Microsoft Store está na
     frente do Python real. Peça ao usuário para desligar `python.exe` e `python3.exe` em
     Configurações > Aplicativos > Configurações avançadas do aplicativo > Aliases de execução do
     aplicativo e reabrir o Claude Code. Não instale Python sem pedir.
3. **Claude Code 2.1+:** `claude --version`.
4. **Testes do gate:** rode `python tests/preparar_ambiente.py` (com `--instalar` para instalar o
   PyYAML pelo pip; o `pdftotext` ele só aponta). Depois `python -m unittest discover -s tests` deve
   terminar em `OK`, sem testes ignorados.
5. **Plugin instalado:** `claude plugin list` deve mostrar `sdd@sdd-padrao` com `Status: enabled`.

## Instalar o plugin `sdd`

Se o passo 5 não mostrar o plugin, instale **pelo CLI**, não pelo comando `/plugin`. No app
desktop do Claude, `/plugin` abre uma tela de gerenciamento e descarta os argumentos.

```bash
claude plugin marketplace add https://github.com/Raikyr4/SpecDriven.git
claude plugin install sdd@sdd-padrao
claude plugin list
```

- O repositório é público (`https://github.com/Raikyr4/SpecDriven.git`): não precisa de login.
- Para testar o plugin a partir desta pasta local, sem baixar do GitHub, use
  `claude plugin marketplace add <caminho-desta-pasta>`.
- Para atualizar: `claude plugin marketplace update sdd-padrao`.
- Depois de instalar, a sessão em andamento só vê os comandos após `/reload-plugins` ou uma nova
  sessão. Confirme que `/especificar` e `/situacao` aparecem ao digitar `/`.

## Convenções deste repositório

- **Idioma:** português do Brasil em comandos, templates, documentação e mensagens de commit.
- **Mudanças no padrão seguem o próprio padrão:** PR, descrição do impacto nos projetos que já
  usam, e `version` nova em `plugins/sdd/.claude-plugin/plugin.json` (e `plugins/sdd/padrao.json`
  se a versão do padrão mudar).
- **Commits:** mensagem no formato `vX.Y.Z: resumo`, como no histórico. Não commite sem o usuário
  pedir.
- **Validação do plugin e do marketplace:**

  ```bash
  claude plugin validate .
  claude plugin validate ./plugins/sdd
  ```

- **Gate de fases:** `plugins/sdd/hooks/sdd_gate.py` é código crítico. Toda alteração nele exige
  teste novo ou ajustado em `tests/`, com `python -m unittest discover -s tests -v` passando.
- **Aprovação é humana:** nunca escreva `status: aprovado` em artefatos de projeto e nunca use
  `--no-verify`.
- **Abrir o PR (GitHub, `Raikyr4/SpecDriven`):** só quando o usuário pedir, depois do commit e do
  push da branch `feat/vX.Y.Z-...`, para a `main`. Com o `gh` logado, use `gh pr create`; sem ele,
  entregue ao usuário o link `https://github.com/Raikyr4/SpecDriven/compare/main...<branch>` com o
  título e a descrição prontos. Nunca peça, imprima nem grave token.

  Título no formato `vX.Y.Z: resumo`. A descrição traz o impacto nos projetos que já usam.

## Estrutura

```text
.claude-plugin/marketplace.json   catálogo do marketplace
plugins/sdd/                      plugin: commands/, agents/, hooks/, scripts/, templates/
tests/                            testes do gate
```
