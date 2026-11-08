"""Testes de plugins/sdd/scripts/medir_sessao.py (soma de tokens do log da sessao)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(AQUI, "..", "plugins", "sdd", "scripts", "medir_sessao.py")


def evento(msg_id, entrada, saida, cw=0, cr=0, ferramentas=()):
    conteudo = [{"type": "tool_use", "id": "t-" + n, "name": n} for n in ferramentas]
    return {"type": "assistant", "sessionId": "s1", "message": {
        "id": msg_id, "content": conteudo,
        "usage": {"input_tokens": entrada, "output_tokens": saida,
                  "cache_creation_input_tokens": cw, "cache_read_input_tokens": cr}}}


class MedirSessao(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="sdd-medir-")
        self.log = os.path.join(self.dir, "s1.jsonl")
        linhas = [
            {"type": "user", "sessionId": "s1", "message": {"content": "oi"}},
            evento("m1", 10, 1),                          # streaming: mesmo id, uso parcial
            evento("m1", 10, 5, cw=100, ferramentas=("Read",)),
            evento("m2", 3, 7, cr=100, ferramentas=("Bash", "Edit")),
        ]
        with open(self.log, "w", encoding="utf-8") as f:
            f.write("\n".join(json.dumps(l) for l in linhas) + "\nlinha quebrada\n")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def rodar(self, *args, env=None):
        p = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True,
                           encoding="utf-8", env=env)
        return p

    def test_soma_cada_mensagem_uma_vez(self):
        dados = json.loads(self.rodar(self.log, "--json").stdout)
        self.assertEqual(dados["chamadas"], 2)
        self.assertEqual(dados["input_tokens"], 13)
        self.assertEqual(dados["output_tokens"], 12)
        self.assertEqual(dados["cache_creation_input_tokens"], 100)
        self.assertEqual(dados["cache_read_input_tokens"], 100)
        self.assertEqual(dados["ferramentas"], {"Read": 1, "Bash": 1, "Edit": 1})

    def test_registrar_calcula_o_consumo_da_fase(self):
        reg = os.path.join(self.dir, "specs", ".metricas", "004.jsonl")
        self.rodar(self.log, "--registrar", reg, "--feature", "004", "--fase", "spec")
        with open(self.log, "a", encoding="utf-8") as f:
            f.write(json.dumps(evento("m3", 50, 20)) + "\n")
        self.rodar(self.log, "--registrar", reg, "--feature", "004", "--fase", "plano")
        with open(reg, encoding="utf-8") as f:
            linhas = [json.loads(l) for l in f]
        self.assertEqual(len(linhas), 2)
        self.assertEqual(linhas[1]["fase"], "plano")
        self.assertEqual(linhas[1]["desde_o_anterior"]["input_tokens"], 50)
        self.assertEqual(linhas[1]["desde_o_anterior"]["chamadas"], 1)

    def test_encontra_a_sessao_mais_recente_do_projeto(self):
        config = os.path.join(self.dir, "config")
        projeto = os.path.join(self.dir, "meu projeto")
        os.makedirs(projeto)
        import re
        pasta = os.path.join(config, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(projeto)))
        os.makedirs(pasta)
        shutil.copy(self.log, os.path.join(pasta, "s1.jsonl"))
        env = dict(os.environ, CLAUDE_CONFIG_DIR=config)
        p = self.rodar("--projeto", projeto, "--json", env=env)
        self.assertEqual(json.loads(p.stdout)["chamadas"], 2)

    def test_sem_log(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=os.path.join(self.dir, "vazio"))
        self.assertEqual(self.rodar("--projeto", self.dir, env=env).returncode, 2)


if __name__ == "__main__":
    unittest.main()
