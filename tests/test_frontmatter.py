"""Os cabeçalhos YAML dos comandos e agentes precisam ser YAML válido."""
import glob
import os
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.join(AQUI, "..", "plugins", "sdd")

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


@unittest.skipIf(yaml is None, "PyYAML não instalado (rode: python tests/preparar_ambiente.py --instalar)")
class Frontmatter(unittest.TestCase):
    def test_cabecalhos_validos(self):
        arquivos = glob.glob(os.path.join(PLUGIN, "commands", "*.md")) + glob.glob(os.path.join(PLUGIN, "agents", "*.md"))
        self.assertTrue(arquivos)
        for caminho in arquivos:
            with open(caminho, encoding="utf-8") as f:
                texto = f.read()
            self.assertTrue(texto.startswith("---\n"), caminho)
            cabecalho = texto.split("---\n", 2)[1]
            dados = yaml.safe_load(cabecalho)
            self.assertIsInstance(dados, dict, caminho)
            self.assertTrue(dados.get("description"), caminho)


if __name__ == "__main__":
    unittest.main()


class MensagensSugeridas(unittest.TestCase):
    def test_comandos_que_terminam_em_commit_citam_a_convencao(self):
        raiz = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins", "sdd")
        self.assertTrue(os.path.isfile(os.path.join(raiz, "templates", "mensagens.md")))
        for nome in ("prepararsdd", "descobrir", "constituicao", "especificar", "esclarecer", "corrigir",
                     "planejar", "tarefas", "implementar", "verificar"):
            with open(os.path.join(raiz, "commands", nome + ".md"), encoding="utf-8") as f:
                self.assertIn("templates/mensagens.md", f.read(), nome)
