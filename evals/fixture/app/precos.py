from decimal import Decimal


def total(itens):
    """Soma dos preços (Decimal)."""
    return sum((Decimal(str(p)) for p in itens), Decimal("0"))


def desconto(preco, percentual):
    return Decimal(str(preco)) - Decimal(str(preco)) * Decimal(str(percentual)) / 100 - Decimal("1")
