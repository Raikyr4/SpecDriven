"""Testes do leitor de fontes do /especificar (plugins/sdd/scripts/ler_fontes.py)."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(AQUI, "..", "plugins", "sdd", "scripts", "ler_fontes.py")

DOCUMENTO = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Necessidade</w:t></w:r></w:p>
<w:p><w:r><w:t xml:space="preserve">O gestor precisa </w:t></w:r><w:r><w:t>exportar o ponto.</w:t></w:r></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/></w:numPr></w:pPr><w:r><w:t>Em PDF</w:t></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Campo</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Regra</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
</w:body>
</w:document>
"""


def criar_docx(caminho, xml=DOCUMENTO):
    with zipfile.ZipFile(caminho, "w") as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        z.writestr("word/document.xml", xml)


def criar_pdf(caminho, texto):
    """PDF de uma página só com o texto, sem depender de pandoc ou LaTeX."""
    conteudo = "BT /F1 12 Tf 20 50 Td ({}) Tj ET".format(texto).encode("latin-1")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 100] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(conteudo) + conteudo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    saida = b"%PDF-1.4\n"
    posicoes = []
    for n, obj in enumerate(objetos, 1):
        posicoes.append(len(saida))
        saida += b"%d 0 obj\n" % n + obj + b"\nendobj\n"
    xref = len(saida)
    saida += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    for pos in posicoes:
        saida += b"%010d 00000 n \n" % pos
    saida += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, xref)
    with open(caminho, "wb") as f:
        f.write(saida)


class LerFontes(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir)

    def rodar(self, *alvos, env=None):
        r = subprocess.run([sys.executable, SCRIPT] + list(alvos), stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, env=env)
        return r.returncode, r.stdout.decode("utf-8")

    def escrever(self, rel, texto, encoding="utf-8"):
        cam = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(cam), exist_ok=True)
        with open(cam, "w", encoding=encoding, newline="") as f:
            f.write(texto)
        return cam

    def test_docx_vira_texto_com_titulos_listas_e_tabelas(self):
        cam = os.path.join(self.dir, "necessidade.docx")
        criar_docx(cam)
        codigo, saida = self.rodar(cam)
        self.assertEqual(codigo, 0)
        self.assertIn("# Necessidade", saida)
        self.assertIn("O gestor precisa exportar o ponto.", saida)
        self.assertIn("- Em PDF", saida)
        self.assertIn("| Campo | Regra |", saida)
        self.assertIn("lidos: 1", saida)

    def test_pasta_le_todos_em_ordem_e_ignora_ocultos_e_nao_suportados(self):
        self.escrever("b.md", "segundo\r\n")
        self.escrever("a.txt", "primeiro")
        self.escrever("sub/c.markdown", "terceiro")
        self.escrever(".oculto/d.md", "nao")
        self.escrever("~$rascunho.docx", "nao")
        self.escrever("planilha.xlsx", "x")
        criar_docx(os.path.join(self.dir, "sub", "e.docx"))
        codigo, saida = self.rodar(self.dir)
        self.assertEqual(codigo, 0)
        self.assertLess(saida.index("primeiro"), saida.index("segundo"))
        self.assertLess(saida.index("segundo"), saida.index("terceiro"))
        self.assertIn("exportar o ponto", saida)
        self.assertNotIn("nao", saida.replace("não", ""))
        self.assertIn("ignorado (formato não suportado): " + os.path.join(self.dir, "planilha.xlsx"), saida)
        self.assertIn("lidos: 4", saida)
        self.assertNotIn("\r", saida)

    def test_texto_em_cp1252(self):
        cam = self.escrever("legado.txt", "Relatório de exceção", encoding="cp1252")
        _, saida = self.rodar(cam)
        self.assertIn("Relatório de exceção", saida)

    def test_pdf_sem_pdftotext_pede_leitura_com_read(self):
        cam = os.path.join(self.dir, "termo.pdf")
        with open(cam, "wb") as f:
            f.write(b"%PDF-1.4\n")
        env = dict(os.environ, PATH=os.path.dirname(sys.executable))
        codigo, saida = self.rodar(cam, env=env)
        self.assertEqual(codigo, 0)
        self.assertIn("ler com a ferramenta Read: " + cam, saida)
        self.assertIn("lidos: 0", saida)

    @unittest.skipUnless(shutil.which("pdftotext"),
                         "pdftotext não instalado (rode: python tests/preparar_ambiente.py)")
    def test_pdf_com_pdftotext(self):
        cam = os.path.join(self.dir, "x.pdf")
        criar_pdf(cam, "Prazo de 30 dias")
        _, saida = self.rodar(cam)
        self.assertIn("Prazo de 30 dias", saida)

    def test_docx_corrompido_nao_derruba_a_leitura(self):
        ruim = self.escrever("ruim.docx", "não é zip")
        bom = self.escrever("bom.md", "conteudo bom")
        codigo, saida = self.rodar(ruim, bom)
        self.assertEqual(codigo, 0)
        self.assertIn("não foi possível ler", saida)
        self.assertIn("conteudo bom", saida)

    def test_caminho_inexistente(self):
        codigo, saida = self.rodar(os.path.join(self.dir, "nada.md"))
        self.assertEqual(codigo, 1)
        self.assertIn("não encontrado", saida)


if __name__ == "__main__":
    unittest.main()
