# Modos do /descobrir

Lido pelo `/descobrir` quando o modo não é o `brief` simples. Mantenha no arquivo só as seções do
modo usado.

## brainstorm — quando há mais de um caminho

1. Com o problema já escrito, gere de 3 a 5 opções realmente diferentes: construir, comprar ou
   integrar, mudar processo, fazer o mínimo, não fazer.
2. Compare todas pelos mesmos critérios: quanto resolve do problema, custo relativo, risco,
   tempo até o primeiro valor.
3. Mostre a tabela ao humano e pergunte qual seguir (ou se combina opções). Registre em
   `## Opções` com a recomendação e a decisão.

## prfaq — quando é preciso testar se a ideia se sustenta

1. Escreva o `## Comunicado` como se a solução já existisse, em linguagem de cliente, em até 250
   palavras: título, quem ganha, o problema que some, uma citação de cliente, como começar.
2. Escreva o `## FAQ` com 5 a 8 perguntas difíceis, de cliente e de quem financia, incluindo
   "por que alguém não usaria isto?" e "o que acontece se não fizermos?".
3. Se o comunicado soar fraco ou o FAQ revelar um furo grave, diga isso ao humano: a descoberta
   também serve para desistir cedo e barato.

## prd — quando a iniciativa tem várias features

1. Escreva `## Requisitos de produto` (RP-n): capacidades, sem solução técnica.
2. Fatie em `## Features candidatas` (F-n): cada uma entregável sozinha, com valor próprio, no
   tamanho de um `/especificar`. Indique quais RP cobre, a classe sugerida e a dependência.
3. Ordene pela entrega que primeiro prova o valor, não pela ordem técnica.
4. O PRD não substitui as specs: cada F-n vira um `/especificar` que cita o brief e a F-n.
