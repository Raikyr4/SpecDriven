"""O lançador scripts/py.sh escolhe o Python 3.8+ e repassa os argumentos.

Cobre também os usos reais do lançador: o comando do hook em hooks.json e as chamadas
dos comandos /situacao, /especificar e /corrigir (status, sincronia, base e ler_fontes).
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from test_sdd_gate import Repo

AQUI = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.abspath(os.path.join(AQUI, "..", "plugins", "sdd"))
SH = shutil.which("sh")


def posix(caminho):
    return caminho.replace("\\", "/")


def lancador(raiz=PLUGIN):
    return posix(os.path.join(raiz, "scripts", "py.sh"))


def rodar(raiz, *args, cwd=None, env=None, entrada=None):
    return subprocess.run([SH, lancador(raiz)] + list(args), capture_output=True, text=True,
                          cwd=cwd, env=env, input=entrada)


def comando_do_hook():
    with open(os.path.join(PLUGIN, "hooks", "hooks.json"), encoding="utf-8") as f:
        hooks = json.load(f)["hooks"]["PreToolUse"][0]["hooks"][0]
    return hooks["command"]


@unittest.skipIf(SH is None, "sh não encontrado")
class Lancador(unittest.TestCase):
    def test_roda_script_do_plugin_com_argumentos(self):
        r = rodar(PLUGIN, "scripts/ler_fontes.py")
        self.assertNotEqual(r.returncode, 127, r.stderr)

    def test_sem_python_sai_com_127(self):
        vazio = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, vazio, True)
        r = rodar(PLUGIN, "hooks/sdd_gate.py", "status", env=dict(os.environ, PATH=vazio))
        self.assertEqual(r.returncode, 127)
        self.assertIn("Python 3.8+", r.stderr)

    def test_comandos_e_hook_usam_o_lancador(self):
        for pasta in (os.path.join(PLUGIN, "commands"), os.path.join(PLUGIN, "hooks")):
            for nome in os.listdir(pasta):
                if not nome.endswith((".md", ".json")):
                    continue
                with open(os.path.join(pasta, nome), encoding="utf-8") as f:
                    texto = f.read()
                self.assertNotIn('python3 "${CLAUDE_PLUGIN_ROOT}', texto, nome)

    def test_comando_que_chama_o_lancador_e_declara_a_permissao(self):
        """Com allowed-tools declarado, chamar o py.sh sem liberá-lo faria o comando pedir confirmação."""
        permissao = "Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/py.sh *)"
        pasta = os.path.join(PLUGIN, "commands")
        for nome in sorted(os.listdir(pasta)):
            if not nome.endswith(".md"):
                continue
            with open(os.path.join(pasta, nome), encoding="utf-8") as f:
                linhas = f.read().splitlines()
            permitidas = [l for l in linhas[:10] if l.startswith("allowed-tools:")]
            chama = any("scripts/py.sh" in l for l in linhas if not l.startswith("allowed-tools:"))
            if permitidas and chama:
                self.assertIn(permissao, permitidas[0], nome)

    def test_lancador_e_hooks_usam_quebra_de_linha_lf(self):
        """Um CR no py.sh ou no hooks.json quebra o Git Bash em clones do Windows com autocrlf."""
        for rel in (("scripts", "py.sh"), ("hooks", "hooks.json")):
            with open(os.path.join(PLUGIN, *rel), "rb") as f:
                self.assertNotIn(b"\r", f.read(), "/".join(rel))

    def test_funciona_com_espaco_no_caminho_do_plugin(self):
        base = tempfile.mkdtemp(prefix="sdd com espaco ")
        self.addCleanup(shutil.rmtree, base, True)
        copia = os.path.join(base, "sdd")
        for sub in ("scripts", "hooks"):
            shutil.copytree(os.path.join(PLUGIN, sub), os.path.join(copia, sub),
                            ignore=shutil.ignore_patterns("__pycache__"))
        repo = Repo()
        self.addCleanup(repo.fechar)
        r = rodar(copia, "hooks/sdd_gate.py", "status", cwd=repo.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Proximo numero livre: 001", r.stdout)


@unittest.skipIf(SH is None, "sh não encontrado")
class UsosDosComandos(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.addCleanup(self.r.fechar)

    def gate(self, *args):
        return rodar(PLUGIN, "hooks/sdd_gate.py", *args, cwd=self.r.dir)

    def test_status_mostra_tabela_e_proximo_numero(self):
        self.r.aprovar_ate("spec")
        r = self.gate("status")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("| Feature | Spec | Plano | Tarefas | Bug |", r.stdout)
        self.assertIn("001-login", r.stdout)
        self.assertIn("Proximo numero livre: 002", r.stdout)

    def test_base_imprime_a_ref_da_branch_principal(self):
        r = self.gate("base")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "main")

    def test_sincronia_na_principal_pede_branch_de_feature(self):
        r = self.gate("sincronia")
        self.assertEqual(r.returncode, 1)
        self.assertIn("voce esta na main", r.stdout)

    def test_sincronia_em_branch_de_feature_em_dia(self):
        self.r.git("switch", "-q", "-c", "feat/001-login")
        r = self.gate("sincronia")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("em dia com main", r.stdout)

    def test_ler_fontes_le_arquivo_pelo_lancador(self):
        self.r.escrever("fontes/necessidade.md", "# Necessidade\nExportar o ponto.\n")
        r = rodar(PLUGIN, "scripts/ler_fontes.py", posix(os.path.join(self.r.dir, "fontes", "necessidade.md")),
                  cwd=self.r.dir)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Exportar o ponto.", r.stdout)
        self.assertIn("lidos: 1", r.stdout)


@unittest.skipIf(SH is None, "sh não encontrado")
class HookDoPlugin(unittest.TestCase):
    """Executa o comando de hooks.json exatamente como o Claude Code o executa."""

    def setUp(self):
        self.r = Repo()
        self.addCleanup(self.r.fechar)

    def hook(self, env_extra=None, **entrada):
        if "file_path" in entrada:
            entrada["file_path"] = os.path.join(self.r.dir, entrada["file_path"])
        evento = {"tool_name": "Write", "tool_input": entrada, "cwd": self.r.dir}
        env = dict(os.environ, CLAUDE_PLUGIN_ROOT=posix(PLUGIN), CLAUDE_PROJECT_DIR=self.r.dir)
        env.update(env_extra or {})
        return subprocess.run([SH, "-c", comando_do_hook()], input=json.dumps(evento),
                              capture_output=True, text=True, cwd=self.r.dir, env=env)

    def test_gate_continua_bloqueando_codigo_sem_tarefas(self):
        p = self.hook(file_path="src/api/A.cs", content="class A {}")
        self.assertEqual(p.returncode, 0, p.stderr)
        saida = json.loads(p.stdout)["hookSpecificOutput"]
        self.assertEqual(saida["permissionDecision"], "deny")

    def test_gate_libera_arquivo_fora_dos_modulos(self):
        p = self.hook(file_path="docs/notas.md", content="x")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout.strip(), "")

    def test_sem_python_avisa_e_nao_bloqueia(self):
        vazio = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, vazio, True)
        p = self.hook(env_extra={"PATH": vazio}, file_path="src/api/A.cs", content="class A {}")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Python 3.8+ nao encontrado", json.loads(p.stdout)["systemMessage"])


if __name__ == "__main__":
    unittest.main()
