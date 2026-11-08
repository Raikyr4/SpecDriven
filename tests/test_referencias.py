"""Caminhos citados pelos comandos existem, referências não ficam órfãs e o texto carregado
por comando não cresce sem perceber (cada byte de um comando é pago a cada invocação)."""
import glob
import os
import re
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.normpath(os.path.join(AQUI, "..", "plugins", "sdd"))
RE_CAMINHO = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^`\s\"']+)")

# Limite por arquivo, em bytes UTF-8. Subir exige justificativa no PR.
LIMITE_COMANDO = 6500
LIMITE_REFERENCIA = 7000


def textos(*padroes):
    for padrao in padroes:
        for caminho in sorted(glob.glob(os.path.join(PLUGIN, padrao))):
            with open(caminho, encoding="utf-8") as f:
                yield caminho, f.read()


class Referencias(unittest.TestCase):
    def test_caminhos_do_plugin_existem(self):
        for caminho, texto in textos("commands/*.md", "agents/*.md", "references/*.md"):
            for rel in RE_CAMINHO.findall(texto):
                rel = rel.rstrip(".,;:)")
                if "<" in rel or "*" in rel:
                    continue
                self.assertTrue(os.path.exists(os.path.join(PLUGIN, rel)),
                                "{} cita {} que não existe".format(os.path.basename(caminho), rel))

    def test_toda_referencia_e_usada(self):
        citados = set()
        for _, texto in textos("commands/*.md", "agents/*.md", "references/*.md"):
            citados.update(r.rstrip(".,;:)") for r in RE_CAMINHO.findall(texto))
        for caminho, _ in textos("references/*.md"):
            rel = "references/" + os.path.basename(caminho)
            self.assertIn(rel, citados, "{} não é lida por nenhum comando".format(rel))

    def test_tamanho_dos_comandos(self):
        for caminho, texto in textos("commands/*.md"):
            self.assertLessEqual(len(texto.encode("utf-8")), LIMITE_COMANDO, caminho)
        for caminho, texto in textos("references/*.md"):
            self.assertLessEqual(len(texto.encode("utf-8")), LIMITE_REFERENCIA, caminho)

    def test_bloco_de_branch_nao_e_duplicado(self):
        for caminho, texto in textos("commands/*.md"):
            self.assertNotIn("git worktree add \"../<pasta do projeto>", texto,
                             "{}: use references/branch-da-feature.md".format(caminho))


if __name__ == "__main__":
    unittest.main()
