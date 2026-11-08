#!/usr/bin/env python3
"""Extrai o texto das fontes de uma necessidade para o /especificar.

Uso: ler_fontes.py <arquivo ou pasta> [<arquivo ou pasta> ...]

Aceita .md, .markdown, .txt, .docx e .pdf. Uma pasta é lida inteira (subpastas
incluídas, em ordem alfabética), ignorando arquivos e pastas ocultos. O texto de
cada arquivo sai no stdout, precedido de um cabeçalho com o caminho. PDF usa o
`pdftotext` se estiver instalado; sem ele, o arquivo é listado para ser lido com a
ferramenta Read do Claude Code. Só biblioteca padrão, Python 3.8+.
"""
import os
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

TEXTO = (".md", ".markdown", ".txt")
SUPORTADOS = TEXTO + (".docx", ".pdf")
LIMITE = 200000  # caracteres por arquivo

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def ler_texto(caminho):
    with open(caminho, "rb") as f:
        dados = f.read()
    for cod in ("utf-8-sig", "cp1252"):
        try:
            return dados.decode(cod).replace("\r\n", "\n")
        except UnicodeDecodeError:
            pass
    return dados.decode("utf-8", errors="replace")


def _paragrafo(p):
    partes = []
    for el in p.iter():
        if el.tag == W + "t" and el.text:
            partes.append(el.text)
        elif el.tag == W + "tab":
            partes.append("\t")
        elif el.tag in (W + "br", W + "cr"):
            partes.append("\n")
    texto = "".join(partes)
    estilo = p.find(W + "pPr/" + W + "pStyle")
    nome = estilo.get(W + "val", "") if estilo is not None else ""
    if texto and nome.lower().startswith(("heading", "titulo", "título", "ttulo")):
        nivel = "".join(c for c in nome if c.isdigit()) or "1"
        texto = "#" * min(int(nivel), 6) + " " + texto
    elif texto and p.find(W + "pPr/" + W + "numPr") is not None:
        texto = "- " + texto
    return texto


def _bloco(el, linhas):
    if el.tag == W + "p":
        linhas.append(_paragrafo(el))
    elif el.tag == W + "tbl":
        for tr in el.findall(W + "tr"):
            celulas = []
            for tc in tr.findall(W + "tc"):
                celulas.append(" ".join(_paragrafo(p) for p in tc.iter(W + "p")).strip())
            linhas.append("| " + " | ".join(celulas) + " |")
        linhas.append("")
    elif el.tag == W + "sdt":
        conteudo = el.find(W + "sdtContent")
        if conteudo is not None:
            for filho in conteudo:
                _bloco(filho, linhas)


def ler_docx(caminho):
    with zipfile.ZipFile(caminho) as z:
        raiz = ET.fromstring(z.read("word/document.xml"))
    corpo = raiz.find(W + "body")
    linhas = []
    for el in corpo if corpo is not None else []:
        _bloco(el, linhas)
    texto = "\n".join(linhas)
    while "\n\n\n" in texto:
        texto = texto.replace("\n\n\n", "\n\n")
    return texto.strip() + "\n"


def ler_pdf(caminho):
    if not shutil.which("pdftotext"):
        return None
    r = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", caminho, "-"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        return None
    texto = r.stdout.decode("utf-8", errors="replace")
    return texto if texto.strip() else None


def coletar(alvos):
    """Devolve (arquivos suportados, ignorados, inexistentes), na ordem de leitura."""
    arquivos, ignorados, faltando = [], [], []
    for alvo in alvos:
        if os.path.isfile(alvo):
            (arquivos if alvo.lower().endswith(SUPORTADOS) else ignorados).append(alvo)
        elif os.path.isdir(alvo):
            for raiz, pastas, nomes in os.walk(alvo):
                pastas[:] = sorted(p for p in pastas if not p.startswith("."))
                for nome in sorted(nomes):
                    if nome.startswith((".", "~$")):
                        continue
                    cam = os.path.join(raiz, nome)
                    (arquivos if nome.lower().endswith(SUPORTADOS) else ignorados).append(cam)
        else:
            faltando.append(alvo)
    return arquivos, ignorados, faltando


def extrair(caminho):
    """Devolve o texto do arquivo, ou None quando ele precisa ser lido com Read."""
    ext = os.path.splitext(caminho)[1].lower()
    if ext in TEXTO:
        return ler_texto(caminho)
    if ext == ".docx":
        return ler_docx(caminho)
    if ext == ".pdf":
        return ler_pdf(caminho)
    return None


def main(argv):
    if not argv:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    arquivos, ignorados, faltando = coletar(argv)
    para_read, falhas = [], 0
    for cam in arquivos:
        try:
            texto = extrair(cam)
        except (zipfile.BadZipFile, KeyError, ET.ParseError, OSError) as e:
            print("===== {} =====\n[não foi possível ler: {}]\n".format(cam, e))
            falhas += 1
            continue
        if texto is None:
            para_read.append(cam)
            continue
        if len(texto) > LIMITE:
            texto = texto[:LIMITE] + "\n[... cortado em {} caracteres]\n".format(LIMITE)
        print("===== {} =====\n{}".format(cam, texto.rstrip() + "\n"))
    print("===== resumo =====")
    print("lidos: {}".format(len(arquivos) - len(para_read) - falhas))
    for cam in para_read:
        print("ler com a ferramenta Read: {}".format(cam))
    for cam in ignorados[:20]:
        print("ignorado (formato não suportado): {}".format(cam))
    if len(ignorados) > 20:
        print("ignorados ainda: {} arquivos".format(len(ignorados) - 20))
    for cam in faltando:
        print("não encontrado: {}".format(cam))
    return 1 if faltando and not arquivos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
