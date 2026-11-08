"""Testes do gate de fases (plugins/sdd/hooks/sdd_gate.py).

Cada teste monta um repositorio git temporario e chama o gate como o Claude Code
chama: evento JSON no stdin, decisao JSON no stdout.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(AQUI, "..", "plugins", "sdd", "hooks", "sdd_gate.py")

SDD_JSON = {
    "versao": 1,
    "modo": "bloqueio",
    "specs": "specs",
    "modulos": [{"nome": "api", "caminho": "src/api", "extensoes": [".cs"]}],
}


def artefato(feature, fase, status, corpo=""):
    return textwrap.dedent("""\
        ---
        feature: {f}
        fase: {fase}
        status: {s}
        ---

        # Titulo

        {c}
        """).format(f=feature, fase=fase, s=status, c=corpo)


class Repo:
    def __init__(self, config=SDD_JSON, constituicao=True):
        self.dir = tempfile.mkdtemp(prefix="sdd-")
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "dev@example.com")
        self.git("config", "user.name", "Dev")
        if config is not None:
            self.escrever(".claude/sdd.json", json.dumps(config))
        self.escrever("README.md", "x")
        if constituicao:
            self.escrever("specs/constitution.md", "---\nfase: constituicao\nstatus: aprovado\n---\n# C\n")
        self.commit("inicio")

    def git(self, *args):
        return subprocess.run(("git",) + args, cwd=self.dir, check=True, capture_output=True, text=True).stdout

    def escrever(self, rel, texto):
        caminho = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            f.write(texto)

    def ler(self, rel):
        with open(os.path.join(self.dir, rel), encoding="utf-8") as f:
            return f.read()

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg, "--allow-empty")

    def hook(self, ferramenta, **entrada):
        if "file_path" in entrada:
            entrada["file_path"] = os.path.join(self.dir, entrada["file_path"])
        evento = {"tool_name": ferramenta, "tool_input": entrada, "cwd": self.dir}
        env = dict(os.environ, CLAUDE_PROJECT_DIR=self.dir)
        p = subprocess.run([sys.executable, GATE, "hook"], input=json.dumps(evento),
                           capture_output=True, text=True, env=env, check=True)
        if not p.stdout.strip():
            return "allow", ""
        saida = json.loads(p.stdout)
        if "hookSpecificOutput" in saida:
            h = saida["hookSpecificOutput"]
            return h["permissionDecision"], h["permissionDecisionReason"]
        return "aviso", saida.get("systemMessage", "")

    def ci(self, base="main", env=None, head=None):
        extra = ["--head", head] if head else []
        p = subprocess.run([sys.executable, GATE, "ci", "--base", base] + extra, cwd=self.dir,
                           capture_output=True, text=True, env=env)
        return p.returncode, p.stdout

    def aprovar_ate(self, fase):
        """Cria e aprova (commit humano) os artefatos da feature 001 ate a fase indicada."""
        self.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado"))
        if fase in ("plan", "tasks"):
            self.escrever("specs/001-login-plan.md", artefato("001-login", "plan", "aprovado"))
        if fase == "tasks":
            self.escrever("specs/001-login-tasks.md", artefato(
                "001-login", "tasks", "aprovado", "- [ ] T-1 — Rota de login\n- [ ] T-2 — Testes"))
        self.commit("aprova " + fase)

    def fechar(self):
        shutil.rmtree(self.dir, ignore_errors=True)


class GateDoHook(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.fechar()

    def test_projeto_sem_sdd_json_nao_e_afetado(self):
        r = Repo(config=None)
        try:
            self.assertEqual(r.hook("Write", file_path="src/api/A.cs", content="x")[0], "allow")
        finally:
            r.fechar()

    def test_codigo_sem_tarefas_aprovadas_e_bloqueado(self):
        decisao, motivo = self.r.hook("Write", file_path="src/api/A.cs", content="class A {}")
        self.assertEqual(decisao, "deny")
        self.assertIn("/implementar bloqueado", motivo)

    def test_arquivo_fora_dos_modulos_e_livre(self):
        self.assertEqual(self.r.hook("Write", file_path="docs/notas.md", content="x")[0], "allow")
        self.assertEqual(self.r.hook("Write", file_path="tools/x.cs", content="x")[0], "allow")

    def test_spec_em_rascunho_e_livre(self):
        d, _ = self.r.hook("Write", file_path="specs/001-login-spec.md",
                           content=artefato("001-login", "spec", "rascunho"))
        self.assertEqual(d, "allow")

    def test_agente_nao_escreve_status_aprovado(self):
        d, motivo = self.r.hook("Write", file_path="specs/001-login-spec.md",
                                content=artefato("001-login", "spec", "aprovado"))
        self.assertEqual(d, "deny")
        self.assertIn("so por uma pessoa", motivo)

    def test_plano_exige_spec_commitada_e_aprovada(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "rascunho"))
        self.r.commit("spec rascunho")
        d, _ = self.r.hook("Write", file_path="specs/001-login-plan.md",
                           content=artefato("001-login", "plan", "rascunho"))
        self.assertEqual(d, "deny")

    def test_plano_liberado_com_spec_aprovada(self):
        self.r.aprovar_ate("spec")
        d, _ = self.r.hook("Write", file_path="specs/001-login-plan.md",
                           content=artefato("001-login", "plan", "rascunho"))
        self.assertEqual(d, "allow")

    def test_spec_aprovada_com_alteracao_pendente_nao_libera_plano(self):
        self.r.aprovar_ate("spec")
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado", "mudou"))
        d, _ = self.r.hook("Write", file_path="specs/001-login-plan.md",
                           content=artefato("001-login", "plan", "rascunho"))
        self.assertEqual(d, "deny")

    def test_tarefas_exigem_plano_aprovado(self):
        self.r.aprovar_ate("spec")
        d, _ = self.r.hook("Write", file_path="specs/001-login-tasks.md",
                           content=artefato("001-login", "tasks", "rascunho"))
        self.assertEqual(d, "deny")

    def test_codigo_liberado_com_tarefa_aprovada_e_pendente(self):
        self.r.aprovar_ate("tasks")
        self.assertEqual(self.r.hook("Write", file_path="src/api/A.cs", content="class A {}")[0], "allow")

    def test_marcar_tarefa_mantem_codigo_liberado(self):
        self.r.aprovar_ate("tasks")
        d, _ = self.r.hook("Edit", file_path="specs/001-login-tasks.md",
                           old_string="- [ ] T-1", new_string="- [x] T-1")
        self.assertEqual(d, "allow")
        caminho = "specs/001-login-tasks.md"
        texto = self.r.ler(caminho)
        self.r.escrever(caminho, texto.replace("- [ ] T-1", "- [x] T-1"))
        self.assertEqual(self.r.hook("Write", file_path="src/api/A.cs", content="class A {}")[0], "allow")

    def test_artefatos_com_crlf_no_disco_continuam_aprovados(self):
        # Windows com core.autocrlf=true: git guarda LF, o disco tem CRLF
        self.r.aprovar_ate("tasks")
        for rel in ("specs/001-login-spec.md", "specs/001-login-plan.md", "specs/001-login-tasks.md"):
            caminho = os.path.join(self.r.dir, rel)
            with open(caminho, "rb") as f:
                dados = f.read()
            with open(caminho, "wb") as f:
                f.write(dados.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.assertEqual(self.r.hook("Write", file_path="specs/001-login-tasks.md",
                                     content="x")[0], "ask")
        self.assertEqual(self.r.hook("Write", file_path="src/api/A.cs", content="x")[0], "allow")
        d, _ = self.r.hook("Edit", file_path="specs/001-login-tasks.md",
                           old_string="- [ ] T-1 — Rota\r\n", new_string="- [x] T-1 — Rota\r\n")
        self.assertEqual(d, "allow")

    def test_todas_as_tarefas_feitas_fecha_o_codigo(self):
        self.r.aprovar_ate("tasks")
        caminho = "specs/001-login-tasks.md"
        texto = self.r.ler(caminho)
        self.r.escrever(caminho, texto.replace("- [ ]", "- [x]"))
        self.assertEqual(self.r.hook("Write", file_path="src/api/A.cs", content="x")[0], "deny")

    def test_editar_texto_de_tarefas_aprovadas_pede_confirmacao(self):
        self.r.aprovar_ate("tasks")
        d, _ = self.r.hook("Edit", file_path="specs/001-login-tasks.md",
                           old_string="Rota de login", new_string="Rota de logout")
        self.assertEqual(d, "ask")

    def test_bug_aprovado_libera_codigo(self):
        self.r.escrever("specs/002-erro-no-login-bug.md",
                        artefato("002-erro-no-login", "bug", "aprovado", "- [ ] T-1 — Corrigir"))
        self.r.commit("aprova bug")
        self.assertEqual(self.r.hook("Write", file_path="src/api/A.cs", content="x")[0], "allow")

    def test_desativar_aviso_e_bloqueado(self):
        self.r.aprovar_ate("tasks")
        d, motivo = self.r.hook("Write", file_path="src/api/A.cs",
                                content="#pragma warning disable CS0168\nclass A {}")
        self.assertEqual(d, "deny")
        self.assertIn("#pragma warning disable", motivo)

    def test_padrao_ja_existente_no_trecho_nao_bloqueia(self):
        self.r.aprovar_ate("tasks")
        d, _ = self.r.hook("Edit", file_path="src/api/A.cs",
                           old_string="#pragma warning disable X\nint a;",
                           new_string="#pragma warning disable X\nint b;")
        self.assertEqual(d, "allow")

    def test_arquivo_protegido_pede_confirmacao(self):
        self.assertEqual(self.r.hook("Edit", file_path=".claude/sdd.json",
                                     old_string="bloqueio", new_string="aviso")[0], "ask")

    def test_agente_nao_commita(self):
        self.assertEqual(self.r.hook("Bash", command="git add -A && git commit -m x")[0], "deny")
        self.assertEqual(self.r.hook("Bash", command="git push origin main")[0], "deny")
        self.assertEqual(self.r.hook("Bash", command="git status")[0], "allow")

    def test_no_verify_e_bloqueado(self):
        self.assertEqual(self.r.hook("Bash", command="npm test --no-verify")[0], "deny")

    def test_bash_nao_aprova_artefato(self):
        d, _ = self.r.hook("Bash", command="sed -i 's/rascunho/aprovado/' specs/001-x-spec.md && echo 'status: aprovado'")
        self.assertEqual(d, "deny")

    def test_git_destrutivo_pede_confirmacao(self):
        self.assertEqual(self.r.hook("Bash", command="git reset --hard HEAD~1")[0], "ask")

    def test_modo_aviso_nao_bloqueia_fase(self):
        r = Repo(config=dict(SDD_JSON, modo="aviso"))
        try:
            d, motivo = r.hook("Write", file_path="src/api/A.cs", content="x")
            self.assertEqual(d, "aviso")
            self.assertIn("modo aviso", motivo)
            # a aprovacao continua exclusiva do humano mesmo em modo aviso
            d, _ = r.hook("Write", file_path="specs/001-a-spec.md", content=artefato("001-a", "spec", "aprovado"))
            self.assertEqual(d, "deny")
        finally:
            r.fechar()

    def test_spec_exige_constituicao_aprovada(self):
        r = Repo(constituicao=False)
        try:
            r.escrever("specs/constitution.md", "---\nstatus: rascunho\n---\n")
            r.commit("constituicao em rascunho")
            d, motivo = r.hook("Write", file_path="specs/001-a-spec.md", content=artefato("001-a", "spec", "rascunho"))
            self.assertEqual(d, "deny")
            self.assertIn("constituicao", motivo)
        finally:
            r.fechar()

    def test_constituicao_aprovada_so_muda_com_confirmacao(self):
        d, _ = self.r.hook("Edit", file_path="specs/constitution.md", old_string="# C", new_string="# D")
        self.assertEqual(d, "ask")

    def test_agente_nao_aprova_constituicao(self):
        r = Repo(constituicao=False)
        try:
            d, _ = r.hook("Write", file_path="specs/constitution.md", content="---\nstatus: aprovado\n---\n")
            self.assertEqual(d, "deny")
        finally:
            r.fechar()

    def test_sem_modulos_vale_qualquer_extensao_de_fonte(self):
        r = Repo(config={"versao": 1})
        try:
            self.assertEqual(r.hook("Write", file_path="app/main.py", content="x")[0], "deny")
            self.assertEqual(r.hook("Write", file_path="app/README.md", content="x")[0], "allow")
        finally:
            r.fechar()


class CheckDoPullRequest(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.r.git("checkout", "-q", "-b", "feature")

    def tearDown(self):
        self.r.fechar()

    def test_pr_so_com_artefatos_passa(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "rascunho"))
        self.r.commit("spec")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 0, saida)

    def test_codigo_sem_tarefa_falha(self):
        self.r.escrever("src/api/A.cs", "class A {}")
        self.r.commit("codigo")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 1)
        self.assertIn("nao marca nenhuma tarefa", saida)

    def test_codigo_com_tarefa_marcada_passa(self):
        self.r.git("checkout", "-q", "main")
        self.r.aprovar_ate("tasks")
        self.r.git("checkout", "-q", "-B", "feature")
        caminho = "specs/001-login-tasks.md"
        texto = self.r.ler(caminho)
        self.r.escrever(caminho, texto.replace("- [ ] T-1", "- [x] T-1"))
        self.r.escrever("src/api/A.cs", "class A {}")
        self.r.commit("task 001 T-1")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 0, saida)

    def test_tarefa_reescrita_depois_de_aprovada_falha(self):
        self.r.git("checkout", "-q", "main")
        self.r.aprovar_ate("tasks")
        self.r.git("checkout", "-q", "-B", "feature")
        caminho = "specs/001-login-tasks.md"
        texto = self.r.ler(caminho)
        self.r.escrever(caminho, texto.replace("- [ ] T-1 — Rota de login", "- [x] T-1 — Outra coisa"))
        self.r.escrever("src/api/A.cs", "class A {}")
        self.r.commit("task")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 1)
        self.assertIn("alem das caixas", saida)

    def test_linha_que_desativa_teste_falha(self):
        self.r.git("checkout", "-q", "main")
        self.r.aprovar_ate("tasks")
        self.r.git("checkout", "-q", "-B", "feature")
        caminho = "specs/001-login-tasks.md"
        texto = self.r.ler(caminho)
        self.r.escrever(caminho, texto.replace("- [ ] T-1", "- [x] T-1"))
        self.r.escrever("src/api/A.cs", "#pragma warning disable CS1\nclass A {}")
        self.r.commit("task")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 1)
        self.assertIn("#pragma warning disable", saida)

    def test_plano_sem_spec_aprovada_falha(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "rascunho"))
        self.r.escrever("specs/001-login-plan.md", artefato("001-login", "plan", "rascunho"))
        self.r.commit("plano")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 1)
        self.assertIn("sem specs/001-login-spec.md aprovado", saida)

    def test_modo_aviso_nao_falha(self):
        self.r.escrever(".claude/sdd.json", json.dumps(dict(SDD_JSON, modo="aviso")))
        self.r.escrever("src/api/A.cs", "class A {}")
        self.r.commit("codigo")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 0)
        self.assertIn("::warning::", saida)


    def test_formato_do_azure_pipelines(self):
        self.r.escrever("src/api/A.cs", "class A {}")
        self.r.commit("codigo")
        env = dict(os.environ, TF_BUILD="True")
        env.pop("GITHUB_ACTIONS", None)
        codigo, saida = self.r.ci(env=env)
        self.assertEqual(codigo, 1)
        self.assertIn("##vso[task.logissue type=error]SDD:", saida)

    def avancar_main(self):
        self.r.git("checkout", "-q", "main")
        self.r.escrever("README.md", "outra feature entrou")
        self.r.commit("outra feature")
        self.r.git("checkout", "-q", "feature")

    def test_branch_atras_da_base_falha(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "rascunho"))
        self.r.commit("spec")
        self.avancar_main()
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 1)
        self.assertIn("1 commit(s) atras de main", saida)
        self.assertIn("git merge main", saida)

    def test_branch_com_base_trazida_passa(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "rascunho"))
        self.r.commit("spec")
        self.avancar_main()
        self.r.git("merge", "-q", "--no-edit", "main")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 0, saida)

    def test_checkout_de_merge_usa_o_head_da_branch(self):
        """Como no Azure e no GitHub: HEAD e o merge do PR; --head e o ultimo commit da branch."""
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "rascunho"))
        self.r.commit("spec")
        origem = self.r.git("rev-parse", "HEAD").strip()
        self.avancar_main()
        self.r.git("checkout", "-q", "--detach", "main")
        self.r.git("merge", "-q", "--no-edit", origem)
        self.assertEqual(self.r.ci()[0], 0)
        codigo, saida = self.r.ci(head=origem)
        self.assertEqual(codigo, 1)
        self.assertIn("atras de main", saida)

    def test_branch_atras_em_modo_aviso_so_avisa(self):
        self.r.escrever(".claude/sdd.json", json.dumps(dict(SDD_JSON, modo="aviso")))
        self.r.commit("aviso")
        self.avancar_main()
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 0)
        self.assertIn("::warning::SDD: a branch esta 1 commit(s) atras", saida)

    def test_exigencia_desligada_na_configuracao(self):
        self.r.escrever(".claude/sdd.json", json.dumps(dict(SDD_JSON, exigir_base_atualizada=False)))
        self.r.commit("config")
        self.avancar_main()
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 0, saida)

    def test_head_inexistente_falha(self):
        codigo, saida = self.r.ci(head="0123456789abcdef0123456789abcdef01234567")
        self.assertEqual(codigo, 1)
        self.assertIn("nao encontrei o commit de origem", saida)


class Sincronia(unittest.TestCase):
    """Branch de trabalho em dia com origin/main antes de comecar e antes do PR."""

    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.fechar()

    def publicar_main(self):
        self.r.git("update-ref", "refs/remotes/origin/main", "main")

    def sincronia(self):
        p = subprocess.run([sys.executable, GATE, "sincronia"], cwd=self.r.dir,
                           capture_output=True, text=True)
        return p.returncode, p.stdout

    def nova_feature_na_main(self):
        self.r.git("checkout", "-q", "main")
        self.r.escrever("README.md", "outra feature")
        self.r.commit("outra feature")
        self.publicar_main()
        self.r.git("checkout", "-q", "feature")

    def test_base_inexistente_pede_fetch(self):
        self.r.escrever(".claude/sdd.json", json.dumps(dict(SDD_JSON, branch_principal="develop")))
        self.r.commit("config")
        codigo, saida = self.sincronia()
        self.assertEqual(codigo, 2)
        self.assertIn("git fetch origin", saida)

    def test_na_main_pede_branch(self):
        self.publicar_main()
        codigo, saida = self.sincronia()
        self.assertEqual(codigo, 1)
        self.assertIn("git switch -c", saida)

    def test_branch_em_dia(self):
        self.publicar_main()
        self.r.git("checkout", "-q", "-b", "feature")
        self.assertEqual(self.sincronia()[0], 0)

    def test_branch_atrasada(self):
        self.publicar_main()
        self.r.git("checkout", "-q", "-b", "feature")
        self.nova_feature_na_main()
        codigo, saida = self.sincronia()
        self.assertEqual(codigo, 1)
        self.assertIn("git merge origin/main", saida)

    def test_branch_principal_configuravel(self):
        self.r.escrever(".claude/sdd.json", json.dumps(dict(SDD_JSON, branch_principal="develop")))
        self.r.commit("config")
        self.r.git("update-ref", "refs/remotes/origin/develop", "main")
        codigo, saida = self.sincronia()
        self.assertEqual(codigo, 0, saida)

    def test_base_so_local_quando_nao_ha_origin(self):
        """Piloto em branch que so existe na maquina: a base e a branch local."""
        self.r.escrever(".claude/sdd.json", json.dumps(dict(SDD_JSON, branch_principal="piloto")))
        self.r.commit("config")
        self.r.git("branch", "piloto")
        p = subprocess.run([sys.executable, GATE, "base"], cwd=self.r.dir, capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout.strip()), (0, "piloto"))
        self.r.git("checkout", "-q", "-b", "feat/001-x", "piloto")
        self.assertEqual(self.sincronia()[0], 0)
        self.r.git("checkout", "-q", "piloto")
        self.r.escrever("README.md", "mudou")
        self.r.commit("avanca piloto")
        self.r.git("checkout", "-q", "feat/001-x")
        codigo, saida = self.sincronia()
        self.assertEqual(codigo, 1)
        self.assertIn("atras de piloto", saida)

    def test_base_prefere_origin(self):
        self.publicar_main()
        p = subprocess.run([sys.executable, GATE, "base"], cwd=self.r.dir, capture_output=True, text=True)
        self.assertEqual(p.stdout.strip(), "origin/main")

    def test_abrir_pr_com_branch_atrasada_e_negado(self):
        self.publicar_main()
        self.r.git("checkout", "-q", "-b", "feature")
        self.assertEqual(self.r.hook("Bash", command="gh pr create --fill")[0], "allow")
        self.nova_feature_na_main()
        d, motivo = self.r.hook("Bash", command="az repos pr create --target-branch main")
        self.assertEqual(d, "deny")
        self.assertIn("atras de origin/main", motivo)

    def test_ci_sem_base_usa_branch_principal(self):
        self.publicar_main()
        self.r.git("checkout", "-q", "-b", "feature")
        self.nova_feature_na_main()
        p = subprocess.run([sys.executable, GATE, "ci"], cwd=self.r.dir, capture_output=True, text=True)
        self.assertEqual(p.returncode, 1)
        self.assertIn("atras de origin/main", p.stdout)


class Paralelismo(unittest.TestCase):
    """Varias features em branches (e pastas) diferentes ao mesmo tempo."""

    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.fechar()

    def status(self):
        p = subprocess.run([sys.executable, GATE, "status", "--json"], cwd=self.r.dir,
                           capture_output=True, text=True, check=True)
        return json.loads(p.stdout)

    def feature(self, branch, arquivos):
        self.r.git("checkout", "-q", "-b", branch, "main")
        for rel, texto in arquivos.items():
            self.r.escrever(rel, texto)
        self.r.commit(branch)
        self.r.git("checkout", "-q", "main")

    def test_numero_considera_branches_locais_e_remotas(self):
        self.r.escrever("specs/003-relatorio-spec.md", artefato("003-relatorio", "spec", "aprovado"))
        self.r.commit("003")
        self.r.git("branch", "feat/004-exportar-espelho")
        self.assertEqual(self.status()["proximo"], "005")
        self.feature("outra", {"specs/005-alerta-spec.md": artefato("005-alerta", "spec", "rascunho")})
        self.r.git("update-ref", "refs/remotes/origin/outra", "outra")
        self.r.git("branch", "-D", "outra")
        self.assertEqual(self.status()["proximo"], "006")

    def test_tarefas_de_outra_feature_nao_liberam_codigo(self):
        self.r.aprovar_ate("tasks")
        self.r.git("checkout", "-q", "-b", "feat/002-exportar")
        d, motivo = self.r.hook("Write", file_path="src/api/A.cs", content="class A {}")
        self.assertEqual(d, "deny")
        self.assertIn("Tarefas de outra feature", motivo)
        self.r.git("checkout", "-q", "-b", "feat/001-login", "main")
        self.assertEqual(self.r.hook("Write", file_path="src/api/A.cs", content="class A {}")[0], "allow")

    def test_branch_sem_numero_mantem_a_regra_geral(self):
        self.r.aprovar_ate("tasks")
        self.r.git("checkout", "-q", "-b", "hotfix")
        self.assertEqual(self.r.hook("Write", file_path="src/api/A.cs", content="class A {}")[0], "allow")

    def test_duas_features_no_mesmo_modulo_geram_aviso(self):
        self.feature("feat/002-exportar", {"src/api/A.cs": "class A {}"})
        self.feature("feat/003-alerta", {"src/api/B.cs": "class B {}"})
        self.feature("feat/004-docs", {"docs/x.md": "x"})
        st = self.status()
        self.assertEqual(sorted(st["em_andamento"]), ["002", "003", "004"])
        self.assertEqual(st["em_andamento"]["004"]["modulos"], [])
        self.assertEqual(st["sobreposicoes"], [{"modulo": "api", "features": ["002", "003"]}])
        p = subprocess.run([sys.executable, GATE, "status"], cwd=self.r.dir, capture_output=True, text=True)
        self.assertIn("ATENCAO: as features 002, 003 mexem no modulo api", p.stdout)

    def test_modulo_declarado_na_spec_conta_para_sobreposicao(self):
        self.feature("feat/002-exportar", {"specs/002-exportar-spec.md": artefato(
            "002-exportar", "spec", "rascunho", "**Módulos afetados:** api\n")})
        self.feature("feat/003-alerta", {"src/api/B.cs": "class B {}"})
        self.assertEqual(self.status()["sobreposicoes"], [{"modulo": "api", "features": ["002", "003"]}])

    def test_ci_barra_numero_ja_usado_na_base(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado"))
        self.r.commit("001")
        self.r.git("checkout", "-q", "-b", "feat/001-exportar")
        self.r.escrever("specs/001-exportar-spec.md", artefato("001-exportar", "spec", "rascunho"))
        self.r.commit("spec")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 1)
        self.assertIn("ja pertence a 001-login", saida)


class Status(unittest.TestCase):
    def test_lista_features_e_proximo_numero(self):
        r = Repo()
        try:
            r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado"))
            r.escrever("specs/001-login-tasks.md", artefato("001-login", "tasks", "rascunho", "- [x] T-1\n- [ ] T-2"))
            r.escrever("specs/004-relatorio-spec.md", artefato("004-relatorio", "spec", "rascunho"))
            p = subprocess.run([sys.executable, GATE, "status", "--json"], cwd=r.dir,
                               capture_output=True, text=True, check=True)
            dados = json.loads(p.stdout)
            self.assertEqual(dados["proximo"], "005")
            self.assertEqual(dados["features"][0]["tasks"], {"status": "rascunho", "feitas": 1, "total": 2})
        finally:
            r.fechar()


SPEC_CONTEXTO = """\
- **RF-1** — O sistema deve autenticar por senha.
- **RF-2** — O sistema deve bloquear apos 5 tentativas.
- **CA-1** (RF-1) — Quando a senha confere, o sistema deve abrir a sessao.
- **CA-2** (RF-2) — Se houver 5 falhas, entao o sistema deve bloquear a conta.
"""

PLANO_CONTEXTO = """\
| Modulo | Arquivo | Mudanca | Origem (RF/CA) |
| --- | --- | --- | --- |
| api | src/api/Login.cs | alterar | RF-1 |
| web | src/web/login.tsx | criar | RF-1 |
| api | src/api/Bloqueio.cs | criar | RF-2 |

- **U-1** — Login por senha (modulo api)
- **U-2** — Bloqueio por tentativas (modulo api)
"""

TAREFAS_CONTEXTO = """\
- [x] T-1 — Login por senha · módulo api · origem RF-1 / plano U-1 · pronto: CA_1 passa
- [ ] T-2 — Bloqueio · módulo api · depende de T-1 · origem RF-2, CA-2 / plano U-2 · pronto: CA_2 passa
- [ ] T-3 — Tela · módulo web · depende de T-2 · origem RF-1 · pronto: teste da tela passa
"""


class Contexto(unittest.TestCase):
    def setUp(self):
        config = dict(SDD_JSON, modulos=[
            {"nome": "api", "caminho": "src/api", "extensoes": [".cs"],
             "instructions": "instructions/api.md", "verificacao": ["dotnet build", "dotnet test"]},
            {"nome": "web", "caminho": "src/web", "extensoes": [".tsx"]},
        ])
        self.r = Repo(config=config)
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado", SPEC_CONTEXTO))
        self.r.escrever("specs/001-login-plan.md", artefato("001-login", "plan", "aprovado", PLANO_CONTEXTO))
        self.r.escrever("specs/001-login-tasks.md", artefato("001-login", "tasks", "aprovado", TAREFAS_CONTEXTO))
        self.r.commit("aprova 001")

    def tearDown(self):
        self.r.fechar()

    def contexto(self, *args):
        return subprocess.run([sys.executable, GATE, "contexto"] + list(args), cwd=self.r.dir,
                              capture_output=True, text=True, encoding="utf-8")

    def test_proxima_tarefa_respeita_dependencias(self):
        dados = json.loads(self.contexto("001", "--json").stdout)
        self.assertEqual(dados["tarefa"]["id"], "T-2")
        self.assertEqual(dados["tarefa"]["depende"], ["T-1"])
        self.assertTrue(dados["liberado"])
        self.assertEqual((dados["feitas"], dados["total"]), (1, 3))

    def test_traz_so_os_itens_citados_pela_tarefa(self):
        dados = json.loads(self.contexto("001", "--json").stdout)
        spec = "\n".join(dados["spec"])
        self.assertIn("RF-2", spec)
        self.assertIn("CA-2", spec)
        self.assertNotIn("RF-1**", spec)
        self.assertNotIn("CA-1", spec)
        plano = "\n".join(dados["plano"])
        self.assertIn("U-2", plano)
        self.assertIn("Bloqueio.cs", plano)
        self.assertNotIn("login.tsx", plano)
        self.assertNotIn("Login.cs", plano)
        self.assertNotIn("U-1", plano)

    def test_sem_linha_citada_no_plano_traz_as_do_modulo(self):
        self.r.escrever("specs/001-login-plan.md", artefato(
            "001-login", "plan", "aprovado", PLANO_CONTEXTO.replace("RF-2 |", "- |").replace("**U-2**", "**U-9**")))
        plano = "\n".join(json.loads(self.contexto("001", "--json").stdout)["plano"])
        self.assertIn("Bloqueio.cs", plano)
        self.assertIn("Login.cs", plano)
        self.assertNotIn("login.tsx", plano)

    def test_modulo_com_instructions_e_verificacao(self):
        dados = json.loads(self.contexto("001", "--json").stdout)
        self.assertEqual(dados["modulo"]["instructions"], "instructions/api.md")
        self.assertEqual(dados["modulo"]["verificacao"], ["dotnet build", "dotnet test"])

    def test_feature_deduzida_pela_branch(self):
        self.r.git("switch", "-q", "-c", "feat/001-login")
        p = self.contexto()
        self.assertEqual(p.returncode, 0)
        self.assertIn("T-2 — Bloqueio", p.stdout)
        self.assertIn("leia antes: instructions/api.md", p.stdout)

    def test_feature_inexistente(self):
        p = self.contexto("009")
        self.assertEqual(p.returncode, 2)
        self.assertIn("009", p.stdout)

    def test_sem_pendencias_aponta_verificar(self):
        self.r.escrever("specs/001-login-tasks.md", artefato(
            "001-login", "tasks", "aprovado", TAREFAS_CONTEXTO.replace("[ ]", "[x]")))
        p = self.contexto("001")
        self.assertIn("/verificar 001", p.stdout)

    def test_lista_em_rascunho_nao_esta_liberada(self):
        self.r.escrever("specs/001-login-tasks.md", artefato("001-login", "tasks", "rascunho", TAREFAS_CONTEXTO))
        dados = json.loads(self.contexto("001", "--json").stdout)
        self.assertFalse(dados["liberado"])

    def test_bug_usa_o_proprio_arquivo_como_spec(self):
        self.r.escrever("specs/002-fuso-bug.md", artefato("002-fuso", "bug", "aprovado", SPEC_CONTEXTO + "\n" + TAREFAS_CONTEXTO))
        dados = json.loads(self.contexto("002", "--json").stdout)
        self.assertEqual(dados["tarefa"]["id"], "T-2")
        self.assertIn("CA-2", "\n".join(dados["spec"]))


def rodar(r, *args):
    return subprocess.run([sys.executable, GATE] + list(args), cwd=r.dir,
                          capture_output=True, text=True, encoding="utf-8")


DELTAS = """\
## 8. Mudanças no comportamento vigente

### Capacidade: autenticacao
#### ADICIONADO
##### Requisito: Bloqueio por tentativas
Quando houver 5 falhas seguidas, o sistema deve bloquear a conta por 15 minutos.
#### ALTERADO
##### Requisito: Login por senha
O sistema deve autenticar por senha com no minimo 12 caracteres.
"""

VIVA = """\
# Capacidade: autenticacao

### Requisito: Login por senha
<!-- origem: 001 -->
O sistema deve autenticar por senha.

### Requisito: Lembrar usuario
<!-- origem: 001 -->
O sistema deve lembrar o ultimo usuario.
"""


class Validar(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.fechar()

    def test_spec_correta_passa(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "rascunho", SPEC_CONTEXTO))
        p = rodar(self.r, "validar", "001")
        self.assertEqual(p.returncode, 0, p.stdout)

    def test_ca_sem_rf_e_rf_inexistente(self):
        spec = SPEC_CONTEXTO + "- **CA-3** — Quando algo, o sistema deve reagir.\n- **CA-4** (RF-9) — Quando x, o sistema deve y.\n"
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "rascunho", spec))
        p = rodar(self.r, "validar", "001")
        self.assertEqual(p.returncode, 1)
        self.assertIn("CA-3 nao cita nenhum RF", p.stdout)
        self.assertIn("CA-4 cita RF-9 que nao existe", p.stdout)

    def test_ca_fora_de_ears_e_aviso(self):
        spec = SPEC_CONTEXTO + "- **CA-3** (RF-1) — O login funciona bem.\n"
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "rascunho", spec))
        p = rodar(self.r, "validar", "001")
        self.assertEqual(p.returncode, 0)
        self.assertIn("AVISO: CA-3 nao comeca em EARS", p.stdout)

    def test_plano_sem_rf_da_spec(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado", SPEC_CONTEXTO))
        self.r.escrever("specs/001-login-plan.md", artefato("001-login", "plan", "rascunho", "| api | a.cs | criar | RF-1, CA-1 |"))
        p = rodar(self.r, "validar", "specs/001-login-plan.md")
        self.assertEqual(p.returncode, 1)
        self.assertIn("RF-2 da spec nao aparece no plano", p.stdout)
        self.assertIn("CA-2 da spec nao aparece no plano", p.stdout)

    def test_plano_grande_gera_aviso(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado", SPEC_CONTEXTO))
        corpo = "RF-1 RF-2 CA-1 CA-2\n" + "texto longo do plano\n" * 500
        self.r.escrever("specs/001-login-plan.md", artefato("001-login", "plan", "rascunho", corpo))
        p = rodar(self.r, "validar", "specs/001-login-plan.md")
        self.assertIn("o alvo e 900-1600", p.stdout)

    def test_tarefas_sem_pronto_modulo_e_dependencia_inexistente(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado", SPEC_CONTEXTO))
        tarefas = "- [ ] T-1 — Algo · origem CA-1\n- [ ] T-2 — Outro · módulo api · depende de T-7 · origem CA-2 · pronto: ok\n"
        self.r.escrever("specs/001-login-tasks.md", artefato("001-login", "tasks", "rascunho", tarefas))
        p = rodar(self.r, "validar", "specs/001-login-tasks.md")
        self.assertEqual(p.returncode, 1)
        self.assertIn("T-1 sem criterio de pronto", p.stdout)
        self.assertIn("T-1 sem modulo", p.stdout)
        self.assertIn("T-2 depende de T-7 que nao existe", p.stdout)

    def test_ca_sem_tarefa_e_aviso(self):
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado", SPEC_CONTEXTO))
        tarefas = "- [ ] T-1 — Algo · módulo api · origem CA-1 · pronto: ok\n"
        self.r.escrever("specs/001-login-tasks.md", artefato("001-login", "tasks", "rascunho", tarefas))
        p = rodar(self.r, "validar", "specs/001-login-tasks.md")
        self.assertIn("CA-2 nao aparece em nenhuma tarefa", p.stdout)

    def test_alterado_de_requisito_inexistente_e_erro(self):
        self.r.escrever("specs/vivas/autenticacao.md", VIVA.replace("Login por senha", "Outro"))
        self.r.escrever("specs/002-bloqueio-spec.md", artefato("002-bloqueio", "spec", "rascunho", SPEC_CONTEXTO + "\n" + DELTAS))
        p = rodar(self.r, "validar", "002")
        self.assertEqual(p.returncode, 1)
        self.assertIn("'Login por senha' nao existe na spec viva", p.stdout)


class SpecsVivas(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.r.escrever("specs/vivas/autenticacao.md", VIVA)
        self.r.escrever("specs/002-bloqueio-spec.md", artefato("002-bloqueio", "spec", "aprovado", SPEC_CONTEXTO + "\n" + DELTAS))
        self.r.commit("spec 002")

    def tearDown(self):
        self.r.fechar()

    def test_consolidar_aplica_e_e_idempotente(self):
        self.assertEqual(rodar(self.r, "consolidar", "002", "--verificar").returncode, 1)
        p = rodar(self.r, "consolidar", "002")
        self.assertEqual(p.returncode, 0, p.stdout)
        viva = self.r.ler("specs/vivas/autenticacao.md")
        self.assertIn("### Requisito: Bloqueio por tentativas\n<!-- origem: 002 -->", viva)
        self.assertIn("no minimo 12 caracteres", viva)
        self.assertIn("Lembrar usuario", viva)
        self.assertEqual(rodar(self.r, "consolidar", "002", "--verificar").returncode, 0)
        self.assertEqual(rodar(self.r, "consolidar", "002").returncode, 0)
        self.assertEqual(self.r.ler("specs/vivas/autenticacao.md"), viva)

    def test_removido_e_capacidade_nova(self):
        spec = SPEC_CONTEXTO + """
## 8. Mudanças no comportamento vigente

### Capacidade: autenticacao
#### REMOVIDO
##### Requisito: Lembrar usuario

### Capacidade: auditoria/acessos
#### ADICIONADO
##### Requisito: Registrar login
Quando um login ocorrer, o sistema deve registrar data e usuario.
"""
        self.r.escrever("specs/003-auditoria-spec.md", artefato("003-auditoria", "spec", "aprovado", spec))
        p = rodar(self.r, "consolidar", "003")
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertNotIn("Lembrar usuario", self.r.ler("specs/vivas/autenticacao.md"))
        self.assertIn("Registrar login", self.r.ler("specs/vivas/auditoria/acessos.md"))

    def test_escrever_spec_viva_nao_e_bloqueado(self):
        self.assertEqual(self.r.hook("Write", file_path="specs/vivas/autenticacao.md", content="x")[0], "allow")

    def test_ci_barra_feature_concluida_sem_consolidar(self):
        self.r.escrever("specs/002-bloqueio-plan.md", artefato("002-bloqueio", "plan", "aprovado", "RF-1 RF-2 CA-1 CA-2"))
        self.r.escrever("specs/002-bloqueio-tasks.md", artefato("002-bloqueio", "tasks", "aprovado",
                                                               "- [ ] T-1 — Bloqueio · módulo api · origem CA-2 · pronto: ok"))
        self.r.commit("aprova 002")
        self.r.git("switch", "-q", "-c", "feat/002-bloqueio")
        self.r.escrever("src/api/Bloqueio.cs", "class Bloqueio {}")
        self.r.escrever("specs/002-bloqueio-tasks.md", artefato("002-bloqueio", "tasks", "aprovado",
                                                               "- [x] T-1 — Bloqueio · módulo api · origem CA-2 · pronto: ok"))
        self.r.commit("task 002 T-1")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 1)
        self.assertIn("consolidar 002", saida)
        rodar(self.r, "consolidar", "002")
        self.r.commit("consolida 002")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 0, saida)


class VivasExternas(unittest.TestCase):
    def test_capacidade_de_outro_repositorio_e_somente_leitura(self):
        r = Repo(config=dict(SDD_JSON, specs_vivas_externas=["../plataforma/specs/vivas"]))
        externo = os.path.join(os.path.dirname(r.dir), "plataforma", "specs", "vivas")
        try:
            os.makedirs(externo, exist_ok=True)
            with open(os.path.join(externo, "autenticacao.md"), "w", encoding="utf-8") as f:
                f.write(VIVA)
            r.escrever("specs/002-bloqueio-spec.md", artefato("002-bloqueio", "spec", "rascunho", SPEC_CONTEXTO + DELTAS))
            p = rodar(r, "validar", "002")
            self.assertEqual(p.returncode, 1)
            self.assertIn("capacidade de outro repositorio", p.stdout)
            self.assertEqual(rodar(r, "consolidar", "002").returncode, 1)
            self.assertFalse(os.path.exists(os.path.join(r.dir, "specs", "vivas", "autenticacao.md")))
        finally:
            shutil.rmtree(os.path.join(os.path.dirname(r.dir), "plataforma"), ignore_errors=True)
            r.fechar()

    def test_capacidade_local_nao_e_afetada(self):
        r = Repo(config=dict(SDD_JSON, specs_vivas_externas=["../nao-existe"]))
        try:
            r.escrever("specs/vivas/autenticacao.md", VIVA)
            r.escrever("specs/002-bloqueio-spec.md", artefato("002-bloqueio", "spec", "rascunho", SPEC_CONTEXTO + DELTAS))
            self.assertEqual(rodar(r, "consolidar", "002").returncode, 0)
        finally:
            r.fechar()


BRIEF = """\
---
fase: descoberta
modo: {modo}
status: rascunho
---

# Brief — Portal do cliente

## Problema

Clientes ligam para saber o status do pedido.

## Quem tem o problema

Clientes com pedidos em andamento e o atendimento.

## Por que agora

O volume de ligacoes dobrou no ultimo trimestre.

## Sucesso

- **M-1** — reduzir de 400 para 150 ligacoes por semana ate 2027-03

## Escopo

- Consultar status do pedido.

## Fora de escopo

- Alterar pedidos.

## Perguntas abertas

- **PA-1** — Pedidos antigos entram?
{extra}"""

PRD_EXTRA = """
## Requisitos de produto

- **RP-1** — O cliente consulta o status sem ligar.

## Features candidatas

- **F-1** — Consulta de status · cobre RP-1 · classe sugerida: media · depende de: nada
- **F-2** — Avisos por e-mail · cobre RP-9 · depende de: F-1
"""


class Descoberta(unittest.TestCase):
    def setUp(self):
        self.r = Repo()

    def tearDown(self):
        self.r.fechar()

    def validar(self, texto):
        self.r.escrever("docs/descoberta/portal/brief.md", texto)
        return rodar(self.r, "validar", "docs/descoberta/portal/brief.md")

    def test_brief_completo_passa(self):
        p = self.validar(BRIEF.format(modo="brief", extra=""))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn("ok", p.stdout)

    def test_secao_e_metrica_faltando(self):
        texto = BRIEF.format(modo="brief", extra="").replace("## Por que agora", "## Outra coisa")
        texto = texto.replace("- **M-1** — reduzir de 400 para 150 ligacoes por semana ate 2027-03", "Melhorar.")
        p = self.validar(texto)
        self.assertEqual(p.returncode, 1)
        self.assertIn("secao '## Por que agora' ausente", p.stdout)
        self.assertIn("sucesso sem metrica", p.stdout)

    def test_metrica_sem_numero_e_aviso(self):
        p = self.validar(BRIEF.format(modo="brief", extra="").replace(
            "reduzir de 400 para 150 ligacoes por semana ate 2027-03", "reduzir ligacoes"))
        self.assertEqual(p.returncode, 0)
        self.assertIn("M-1 sem numero", p.stdout)

    def test_prd_valida_features(self):
        p = self.validar(BRIEF.format(modo="prd", extra=PRD_EXTRA))
        self.assertEqual(p.returncode, 1)
        self.assertIn("F-2 cita RP-9 que nao existe", p.stdout)
        self.assertIn("F-2 sem classe sugerida", p.stdout)

    def test_brainstorm_precisa_de_duas_opcoes(self):
        extra = "\n## Opções\n\n- **O-1** — Portal web.\n"
        p = self.validar(BRIEF.format(modo="brainstorm", extra=extra))
        self.assertEqual(p.returncode, 1)
        self.assertIn("ao menos duas opcoes", p.stdout)

    def test_secao_de_outro_modo_e_aviso(self):
        p = self.validar(BRIEF.format(modo="brief", extra=PRD_EXTRA.replace("RP-9", "RP-1")))
        self.assertIn("e do modo prd; remova", p.stdout)

    def test_template_do_plugin_tem_a_forma_esperada(self):
        with open(os.path.join(AQUI, "..", "plugins", "sdd", "templates", "artefatos", "brief.md"), encoding="utf-8") as f:
            modelo = f.read().replace("<brief | brainstorm | prfaq | prd>", "brief")
        p = self.validar(modelo)
        self.assertNotIn("ausente", p.stdout)
        self.assertIn("placeholder", p.stdout)

    def test_agente_nao_aprova_o_brief(self):
        decisao, _ = self.r.hook("Write", file_path="docs/descoberta/portal/brief.md",
                                 content=BRIEF.format(modo="brief", extra="").replace("rascunho", "aprovado"))
        self.assertEqual(decisao, "deny")
        decisao, _ = self.r.hook("Write", file_path="docs/descoberta/portal/brief.md",
                                 content=BRIEF.format(modo="brief", extra=""))
        self.assertEqual(decisao, "allow")


class PlanoCompacto(unittest.TestCase):
    """Caminho medio: o plano aprovado traz as tarefas e libera codigo sem -tasks.md."""

    def setUp(self):
        self.r = Repo()
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado", SPEC_CONTEXTO))
        self.r.escrever("specs/001-login-plan.md", artefato("001-login", "plan", "aprovado",
                                                            PLANO_CONTEXTO + "\n## Tarefas\n\n" + TAREFAS_CONTEXTO))
        self.r.commit("aprova 001")

    def tearDown(self):
        self.r.fechar()

    def test_plano_com_tarefas_libera_codigo(self):
        self.assertEqual(self.r.hook("Write", file_path="src/api/A.cs", content="class A {}")[0], "allow")

    def test_marcar_tarefa_no_plano_aprovado_e_permitido(self):
        decisao, _ = self.r.hook("Edit", file_path="specs/001-login-plan.md",
                                 old_string="- [ ] T-2", new_string="- [x] T-2")
        self.assertEqual(decisao, "allow")

    def test_mudar_texto_do_plano_aprovado_pede_confirmacao(self):
        decisao, _ = self.r.hook("Edit", file_path="specs/001-login-plan.md",
                                 old_string="Bloqueio por tentativas", new_string="Outra coisa")
        self.assertEqual(decisao, "ask")

    def test_contexto_usa_o_plano(self):
        dados = json.loads(rodar(self.r, "contexto", "001", "--json").stdout)
        self.assertEqual(dados["tarefa"]["id"], "T-2")
        self.assertTrue(dados["liberado"])

    def test_ci_aceita_tarefa_marcada_no_plano(self):
        self.r.git("switch", "-q", "-c", "feat/001-login")
        self.r.escrever("src/api/A.cs", "class A {}")
        self.r.escrever("specs/001-login-plan.md", self.r.ler("specs/001-login-plan.md").replace("- [ ] T-2", "- [x] T-2"))
        self.r.commit("task 001 T-2")
        codigo, saida = self.r.ci()
        self.assertEqual(codigo, 0, saida)

    def test_plano_sem_tarefas_nao_libera(self):
        r = Repo()
        try:
            r.aprovar_ate("plan")
            self.assertEqual(r.hook("Write", file_path="src/api/A.cs", content="class A {}")[0], "deny")
        finally:
            r.fechar()


class Revisao(unittest.TestCase):
    def setUp(self):
        self.r = Repo(config=dict(SDD_JSON, areas_sensiveis=["src/api/Auth/"], limite_revisao=10))
        self.r.escrever("src/api/A.cs", "class A {}\n")
        self.r.commit("base")

    def tearDown(self):
        self.r.fechar()

    def revisao(self, *args):
        return json.loads(rodar(self.r, "revisao", "--json", *args).stdout)

    def test_mudanca_pequena_dispensa_revisores(self):
        self.r.escrever("src/api/A.cs", "class A { int x; }\n")
        dados = self.revisao()
        self.assertFalse(dados["revisor_de_codigo"])
        self.assertFalse(dados["revisor_de_seguranca"])
        with open(dados["diff"], encoding="utf-8") as f:
            self.assertIn("int x", f.read())
        self.assertFalse(os.path.abspath(dados["diff"]).startswith(os.path.abspath(self.r.dir)))

    def test_arquivo_novo_e_diff_grande_pedem_revisor(self):
        self.r.escrever("src/api/B.cs", "class B {}\n")
        dados = self.revisao()
        self.assertTrue(dados["revisor_de_codigo"])
        self.assertIn("src/api/B.cs", " ".join(dados["motivos_codigo"]))
        self.r.commit("b")
        self.r.escrever("src/api/A.cs", "".join("// linha {}\n".format(i) for i in range(20)))
        self.assertTrue(self.revisao()["revisor_de_codigo"])

    def test_area_e_termo_sensiveis_pedem_seguranca(self):
        self.r.escrever("src/api/Auth/Login.cs", "class Login {}\n")
        self.assertTrue(self.revisao()["revisor_de_seguranca"])
        self.r.commit("login")
        self.r.escrever("src/api/A.cs", "class A { string senha; }\n")
        dados = self.revisao()
        self.assertTrue(dados["revisor_de_seguranca"])
        self.assertIn("senha", " ".join(dados["motivos_seguranca"]))

    def test_base_principal_pega_toda_a_branch(self):
        self.r.git("switch", "-q", "-c", "feat/001-login")
        self.r.escrever("src/api/C.cs", "class C {}\n")
        self.r.commit("c")
        dados = self.revisao("--base", "principal")
        self.assertIn("src/api/C.cs", dados["arquivos"])


TRX = """<?xml version="1.0" encoding="utf-8"?>
<TestRun xmlns="http://microsoft.com/schemas/VisualStudio/TeamTest/2010"><Results>
<UnitTestResult testName="Api.Tests.LoginTests.F001_CA_1_abre_sessao" outcome="Passed" />
<UnitTestResult testName="Api.Tests.LoginTests.F001_CA2_bloqueia" outcome="Failed" />
</Results></TestRun>"""

JUNIT = """<?xml version="1.0"?><testsuites><testsuite name="web">
<testcase classname="login" name="F001_CA_1 mostra erro"/>
<testcase classname="login" name="F001_CA_2 tela bloqueada"><skipped/></testcase>
</testsuite></testsuites>"""


class Cobertura(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.r.escrever("specs/001-login-spec.md", artefato("001-login", "spec", "aprovado", SPEC_CONTEXTO))
        self.r.escrever("src/api/Tests/LoginTests.cs",
                        "public void F001_CA_1_abre_sessao() {}\npublic void F001_CA2_bloqueia() {}\n"
                        "public void F004_CA_1_de_outra_feature() {}\n")
        self.r.commit("testes")

    def tearDown(self):
        self.r.fechar()

    def test_sem_resultados_confere_existencia(self):
        p = rodar(self.r, "cobertura", "001", "--json")
        dados = {c["ca"]: c for c in json.loads(p.stdout)["criterios"]}
        self.assertEqual(dados["CA-1"]["testes"][0]["onde"], "src/api/Tests/LoginTests.cs:1")
        self.assertEqual(len(dados["CA-1"]["testes"]), 1)
        self.assertEqual(dados["CA-2"]["situacao"], "nao executado")
        self.assertEqual(p.returncode, 0)

    def test_ca_sem_teste_falha(self):
        self.r.escrever("src/api/Tests/LoginTests.cs", "public void F001_CA_1_abre_sessao() {}\n")
        p = rodar(self.r, "cobertura", "001")
        self.assertEqual(p.returncode, 1)
        self.assertIn("| CA-2 | SEM TESTE |", p.stdout)

    def test_resultados_trx_e_junit(self):
        trx = os.path.join(self.r.dir, "r.trx")
        junit = os.path.join(self.r.dir, "r.xml")
        self.r.escrever("r.trx", TRX)
        self.r.escrever("r.xml", JUNIT)
        p = rodar(self.r, "cobertura", "001", "--json", "--resultados", trx, junit)
        dados = {c["ca"]: c["situacao"] for c in json.loads(p.stdout)["criterios"]}
        self.assertEqual(dados, {"CA-1": "OK", "CA-2": "FALHOU"})
        self.assertEqual(p.returncode, 1)


if __name__ == "__main__":
    unittest.main()
