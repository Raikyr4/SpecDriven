---
feature: 001-desconto-progressivo
fase: spec
status: aprovado
---

# Desconto progressivo

## 1. Contexto e problema

Clientes com compras grandes pedem desconto. **Módulos afetados:** app
**Classe:** media (confirmada por avaliação)

## 3. Requisitos funcionais

- **RF-1** — O sistema deve aplicar 10% de desconto ao total de compras acima de R$ 100,00.

## 5. Critérios de aceite (EARS)

- **CA-1** (RF-1) — Quando o total for maior que R$ 100,00, o sistema deve devolver o total com 10% de desconto.
- **CA-2** (RF-1) — Quando o total for R$ 100,00 ou menos, o sistema deve devolver o total sem desconto.
