---
fase: constituicao
status: rascunho
---

# Constituição — <Nome do projeto>

Princípios não negociáveis que toda spec, plano, tarefa e código seguem. Alterações só por
emenda datada, na seção "Emendas", aprovadas pelo dev responsável.

## Princípios

1. **Spec antes de código.** Mudança relevante passa por spec → plano → tarefas →
   implementação, com revisão humana entre as fases. Bug pequeno usa o caminho curto
   (`/corrigir`), também com revisão humana.
2. **Teste faz parte da tarefa.** Nenhuma lógica nova entra sem teste. Nunca se desativa
   teste, aviso, lint ou verificação de tipo para "passar". Em código legado sem testes, a
   regra vale para o que a tarefa cria ou altera: o código tocado ganha teste de
   caracterização antes da mudança. Não se exige cobrir o legado inteiro.
3. **Pequeno e reversível.** Cada tarefa cabe em um commit atômico, em um módulo por padrão.
4. **Validação na fronteira.** Toda entrada externa é validada na borda do sistema antes de
   ser persistida ou processada.
5. **Erros de domínio explícitos.** Falhas previsíveis viram erros tratados e traduzidos em
   respostas claras; nada de exceção não tratada chegando ao usuário.
6. **Segurança por padrão.** Sem credenciais, segredos ou dados pessoais reais no repositório.
   Ações destrutivas passam por confirmação humana.
7. **Ambiguidade vira pergunta.** O que depende de decisão humana fica em "Questões em aberto",
   nunca em suposição.
<Acrescente princípios específicos do projeto.>

## Stack obrigatória

| Camada | Tecnologia e versão |
| --- | --- |
| <camada> | <tecnologia> |

## Fronteiras e responsabilidades

<Quem faz o quê. Ex.: "Só a API escreve no banco"; "o front-end não chama serviços externos".>

## Invariantes técnicos

<Regras que, se quebradas, causam erro silencioso. Registradas para não serem redescobertas.>

## Definição de pronto

- Build sem avisos e testes verdes nos módulos tocados (comandos em `.claude/sdd.json`).
- Critérios de aceite da spec cobertos por teste que os cita.
- Revisão humana do pull request e check `sdd-gate` verde.

## Emendas

<AAAA-MM-DD — O que mudou, por quê, quem decidiu, o que não mudou.>
