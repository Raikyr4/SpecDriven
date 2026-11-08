"""Confere o que os testes precisam para rodar sem ignorar nenhum caso.

Uso:
    python tests/preparar_ambiente.py             só confere e mostra o que falta
    python tests/preparar_ambiente.py --instalar  instala os pacotes Python que faltam (pip)

Pacotes Python (requirements-dev.txt) o script instala. Programas do sistema, como o pdftotext,
ele só aponta, com o comando sugerido para o seu sistema: instalá-los muda a máquina toda.
"""
import importlib.util
import os
import platform
import shutil
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REQUISITOS = os.path.join(RAIZ, "requirements-dev.txt")

# módulo importado -> pacote pip
PACOTES = {"yaml": "pyyaml"}


def dica_pdftotext():
    sistema = platform.system()
    if sistema == "Windows":
        return "winget install oschwartz10612.Poppler  (ou: choco install poppler)"
    if sistema == "Darwin":
        return "brew install poppler"
    return "sudo apt install poppler-utils  (ou o equivalente da sua distribuição)"


def faltando():
    pacotes = [pip for modulo, pip in PACOTES.items() if importlib.util.find_spec(modulo) is None]
    programas = [] if shutil.which("pdftotext") else [("pdftotext", dica_pdftotext())]
    return pacotes, programas


def main(argv):
    instalar = "--instalar" in argv
    pacotes, programas = faltando()
    if pacotes and instalar:
        print("Instalando: " + ", ".join(pacotes))
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-r", REQUISITOS])
        if r.returncode != 0:
            print("Falha ao instalar com o pip.")
            return 1
        pacotes, programas = faltando()
    for pacote in pacotes:
        print("Falta o pacote Python {}. Rode: python tests/preparar_ambiente.py --instalar".format(pacote))
    for programa, dica in programas:
        print("Falta o programa {} (um teste de PDF fica ignorado). Instale com: {}".format(programa, dica))
    if not pacotes and not programas:
        print("Ambiente de testes completo: nenhum teste deve ser ignorado.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
