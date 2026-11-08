---
feature: 001-desconto-progressivo
fase: plan
status: aprovado
---

# Plano — Desconto progressivo

| Módulo | Arquivo | Mudança | Origem (RF/CA) |
| --- | --- | --- | --- |
| app | app/precos.py | criar `total_com_desconto(itens)` | RF-1, CA-1, CA-2 |

- **U-1** — Função e testes de CA-1 e CA-2 (módulo app)

## Tarefas

- [ ] T-1 — total_com_desconto com testes · módulo app · origem RF-1, CA-1, CA-2 / U-1 · pronto: `python -m unittest discover -s app -p test_*.py` verde
