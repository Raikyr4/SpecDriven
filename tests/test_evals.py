"""Testes do runner de evals (evals/rodar_evals.py), sem chamar o Claude."""
import json
import os
import shutil
import sys
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "evals"))
import rodar_evals as ev  # noqa: E402  (o caminho e montado acima)

IMPLEMENTACAO = '''

def total_com_desconto(itens):
    t = total(itens)
    return t * Decimal("0.9") if t > 100 else t
'''

TESTES = '''
import unittest
from decimal import Decimal
from precos import total_com_desconto


class Desconto(unittest.TestCase):
    def test_F001_CA_1_acima_de_100(self):
        self.assertEqual(total_com_desconto([200]), Decimal("180.0"))

    def test_F001_CA_2_ate_100(self):
        self.assertEqual(total_com_desconto([100]), Decimal("100"))
'''


def caso(id_):
    with open(os.path.join(AQUI, "..", "evals", "casos.json"), encoding="utf-8") as f:
        return next(c for c in json.load(f)["casos"] if c["id"] == id_)


class Evals(unittest.TestCase):
    def test_casos_tem_verificacoes_conhecidas(self):
        with open(os.path.join(AQUI, "..", "evals", "casos.json"), encoding="utf-8") as f:
            dados = json.load(f)
        self.assertGreaterEqual(len(dados["casos"]), 3)
        for c in dados["casos"]:
            for v in c["verificacoes"]:
                self.assertIn(v["tipo"], ("arquivo_existe", "contem", "nao_contem", "validar_ok", "cobertura_ok",
                                          "comando_ok", "branch_casa", "sem_commits_novos", "sem_codigo_alterado"))

    def test_implementacao_correta_passa_em_todas_as_verificacoes(self):
        c = caso("implementar")
        base, projeto = ev.preparar(c)
        try:
            commit = ev.git(projeto, "rev-parse", "HEAD").stdout.strip()
            self.assertEqual(ev.git(projeto, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), c["branch"])
            with open(os.path.join(projeto, "app", "precos.py"), "a", encoding="utf-8") as f:
                f.write(IMPLEMENTACAO)
            with open(os.path.join(projeto, "app", "test_desconto.py"), "w", encoding="utf-8") as f:
                f.write(TESTES)
            plano = os.path.join(projeto, "specs", "001-desconto-progressivo-plan.md")
            texto = ev.ler(plano).replace("- [ ] T-1", "- [x] T-1")
            with open(plano, "w", encoding="utf-8") as f:
                f.write(texto)
            falhas = [(v["tipo"], d) for v in c["verificacoes"] for ok, d in [ev.checar(projeto, v, commit)] if not ok]
            self.assertEqual(falhas, [])
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_projeto_sem_mudanca_falha(self):
        c = caso("implementar")
        base, projeto = ev.preparar(c)
        try:
            commit = ev.git(projeto, "rev-parse", "HEAD").stdout.strip()
            resultados = [ev.checar(projeto, v, commit)[0] for v in c["verificacoes"]]
            self.assertFalse(all(resultados))
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_fixture_valida_no_gate(self):
        c = caso("implementar")
        base, projeto = ev.preparar(c)
        try:
            ok, detalhe = ev.checar(projeto, {"tipo": "validar_ok", "alvo": "specs/001-*.md"}, "")
            self.assertTrue(ok, detalhe)
        finally:
            shutil.rmtree(base, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
