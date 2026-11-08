#!/usr/bin/env python3
"""Gate do fluxo SDD: constituicao -> spec -> plan -> tasks -> implementacao.

Tres modos:

    sdd_gate.py hook            Hook PreToolUse do Claude Code (le o evento no stdin).
    sdd_gate.py ci --base REF [--head REF]
                                Check de pull request (Azure Pipelines, GitHub Actions ou
                                qualquer CI). HEAD = ultimo commit da branch do PR.
    sdd_gate.py base            Imprime a ref da branch base (origin/<branch_principal> ou a local).
    sdd_gate.py sincronia       A branch atual contem origin/<branch_principal>? (0 sim, 1 nao, 2 sem fetch)
    sdd_gate.py status [--json] Situacao das features em specs/ e o proximo numero livre.
    sdd_gate.py contexto [NNN] [--json]
                                Contexto minimo da proxima tarefa: linha da tarefa, modulo,
                                itens da spec e do plano que ela cita (leitura seletiva).
    sdd_gate.py validar [NNN|arquivo ...]
                                Checagem deterministica de forma dos artefatos (ids, EARS, RF/CA
                                citados, tarefas com modulo/origem/pronto, tamanho do plano).
    sdd_gate.py revisao [--base principal|REF] [--json]
                                Grava o diff num arquivo temporario e diz se o revisor de codigo
                                e o de seguranca sao necessarios (tamanho, arquivo novo, area
                                ou termo sensivel).
    sdd_gate.py cobertura [NNN] [--resultados TRX/JUnit ...] [--json]
                                Tabela CA -> testes (nome com F<NNN>_CA_<n>) -> resultado.
    sdd_gate.py consolidar [NNN] [--verificar]
                                Aplica as mudancas de comportamento da spec as specs vivas
                                (specs/vivas/<capacidade>.md); --verificar so confere.

O sinal humano e o commit. O agente nao commita e nao escreve `status: aprovado`,
portanto um artefato em HEAD com `status: aprovado` so pode ter sido promovido por
uma pessoa. O hook e guardrail contra acidente e deriva; a camada que nao pode ser
burlada e o modo `ci`, rodando no pull request com protecao de branch.

O projeto so e tratado como SDD quando existe `.claude/sdd.json`. Sem ele, o hook
nao faz nada, para o plugin poder ficar instalado globalmente.

Somente biblioteca padrao, Python 3.8+.
"""
import argparse
import json
import os
import re
import fnmatch
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

CONFIG_REL = ".claude/sdd.json"
VERSAO = "0.1.22"  # igual a plugins/sdd/.claude-plugin/plugin.json (teste garante)

PADRAO = {
    "versao": 1,
    "modo": "bloqueio",
    "specs": "specs",
    "agente_pode_commitar": False,
    "exigir_base_atualizada": True,
    "branch_principal": "main",
    "areas_sensiveis": [],
    "limite_revisao": 50,
    "specs_vivas_externas": [],
    "modulos": [],
    "extensoes_fonte": [
        ".cs", ".fs", ".vb", ".java", ".kt", ".kts", ".scala", ".go", ".rs",
        ".py", ".rb", ".php", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
        ".vue", ".svelte", ".dart", ".swift", ".m", ".mm", ".c", ".cc",
        ".cpp", ".cxx", ".h", ".hpp", ".sql", ".ps1", ".sh",
    ],
    "excluidos": [
        "/bin/", "/obj/", "/node_modules/", "/dist/", "/build/", "/.dart_tool/",
        "/vendor/", "/.venv/", "/__pycache__/", "/target/",
    ],
    "protegidos": [
        ".claude/sdd.json",
        ".claude/settings.json",
        ".sdd/",
        ".github/workflows/sdd-gate.yml",
        "azure-pipelines.sdd.yml",
    ],
    "padroes_proibidos": [
        "#pragma warning disable",
        "<NoWarn>",
        "SuppressMessage(",
        "[Fact(Skip",
        "[Ignore",
        "@Ignore",
        "@Disabled",
        "@pytest.mark.skip",
        "unittest.skip",
        "# type: ignore",
        "# noqa",
        "eslint-disable",
        "@ts-ignore",
        "@ts-nocheck",
        "it.skip(",
        "describe.skip(",
        "test.skip(",
        "xit(",
        "xdescribe(",
        "// ignore: ",
        "// ignore_for_file",
        "-Wno-",
        "#[ignore]",
        "--no-verify",
    ],
}

RE_ARTEFATO = re.compile(r"^(\d{3})-([a-z0-9][a-z0-9-]*)-(spec|plan|tasks|bug|checklist)\.md$")
RE_STATUS = re.compile(r"^status:\s*(\S+)\s*$", re.M)
RE_CAIXA = re.compile(r"^(\s*[-*]\s*)\[[xX ]\]", re.M)
RE_CAIXA_ABERTA = re.compile(r"^\s*[-*]\s*\[ \]", re.M)
RE_CAIXA_FECHADA = re.compile(r"^\s*[-*]\s*\[[xX]\]", re.M)
RE_APROVADO = re.compile(r"status:\s*[\"']?aprovado", re.I)
RE_GIT_COMMIT = re.compile(r"\bgit\b[^\n|;&]*\b(commit|push|tag)\b")
RE_BRANCH_FEATURE = re.compile(r"(?:^|/)(\d{3})-([a-z0-9][a-z0-9-]*)$")
RE_MODULOS_SPEC = re.compile(r"^\*\*M[oó]dulos afetados:\*\*(.*)$", re.MULTILINE | re.IGNORECASE)
RE_ABRIR_PR = re.compile(r"\b(gh\s+pr\s+create|az\s+repos\s+pr\s+create)\b")
RE_GIT_DESTRUTIVO = re.compile(
    r"\bgit\b[^\n|;&]*\b(reset\s+--hard|clean\s+-[a-z]*f|checkout\s+--\s|restore\s+\.|push\s+[^\n]*--force)"
)


# --------------------------------------------------------------------------- utilidades

def normalizar(p):
    """Caminho absoluto com barras normais, aceitando a forma /c/... do Git Bash."""
    p = p.replace("\\", "/")
    if os.name == "nt":
        m = re.match(r"^/([A-Za-z])/(.*)$", p)
        if m:
            p = "{}:/{}".format(m.group(1).upper(), m.group(2))
    return os.path.normpath(os.path.abspath(p)).replace("\\", "/")


class Projeto:
    def __init__(self, raiz):
        self.raiz = normalizar(raiz)
        self.config = None
        caminho = os.path.join(self.raiz, CONFIG_REL)
        if os.path.isfile(caminho):
            with open(caminho, encoding="utf-8") as f:
                lido = json.load(f)
            self.config = dict(PADRAO)
            self.config.update(lido)

    @property
    def ativo(self):
        return self.config is not None

    @property
    def specs(self):
        return self.config["specs"].strip("/")

    @property
    def aviso(self):
        return self.config.get("modo") == "aviso"

    # git ------------------------------------------------------------------

    def git(self, *args):
        try:
            p = subprocess.run(("git",) + args, cwd=self.raiz, capture_output=True,
                               text=True, encoding="utf-8", errors="replace")
        except OSError:
            return None
        return p.stdout if p.returncode == 0 else None

    def em_head(self, rel, ref="HEAD"):
        """Conteudo do arquivo no commit indicado, ou None."""
        return self.git("show", "{}:{}".format(ref, rel))

    def no_disco(self, rel):
        try:
            with open(os.path.join(self.raiz, rel), encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def listar_specs(self, ref="HEAD"):
        saida = self.git("ls-tree", "--name-only", ref, self.specs + "/") or ""
        return [l for l in saida.splitlines() if l]

    # classificacao --------------------------------------------------------

    def relativo(self, alvo):
        try:
            rel = os.path.relpath(normalizar(alvo), self.raiz).replace("\\", "/")
        except ValueError:
            return None
        return None if rel.startswith("..") else rel

    def branch_atual(self):
        return (self.git("rev-parse", "--abbrev-ref", "HEAD") or "").strip()

    def feature_da_branch(self):
        """Numero NNN quando a branch atual e de feature (feat/NNN-slug, fix/NNN-slug, NNN-slug)."""
        m = RE_BRANCH_FEATURE.search(self.branch_atual())
        return m.group(1) if m else None

    def modulo_de(self, rel):
        for mod in (self.config or {}).get("modulos") or []:
            base = mod.get("caminho", "").strip("/")
            if base and (rel == base or rel.startswith(base + "/")):
                return mod.get("nome") or base
        return None

    def artefato(self, rel):
        """(numero, slug, tipo) quando rel e um artefato em specs/, senao None."""
        if not rel.startswith(self.specs + "/"):
            return None
        m = RE_ARTEFATO.match(rel[len(self.specs) + 1:])
        return m.groups() if m else None

    def protegido(self, rel):
        for p in self.config["protegidos"]:
            if rel == p or (p.endswith("/") and rel.startswith(p)):
                return True
        return False

    def codigo(self, rel):
        """True quando rel e codigo-fonte de um modulo (o que exige tarefa aprovada)."""
        if rel.startswith(self.specs + "/") or rel.startswith(".claude/") or rel.startswith(".github/"):
            return False
        caminho = "/" + rel
        if any(e in caminho for e in self.config["excluidos"]):
            return False
        ext = os.path.splitext(rel)[1].lower()
        modulos = self.config.get("modulos") or []
        if not modulos:
            return ext in self.config["extensoes_fonte"]
        for mod in modulos:
            base = mod.get("caminho", "").strip("/")
            if base and not (rel == base or rel.startswith(base + "/")):
                continue
            exts = [e.lower() for e in (mod.get("extensoes") or self.config["extensoes_fonte"])]
            if ext in exts:
                return True
        return False


def lf(texto):
    """Quebras de linha normalizadas: no Windows com core.autocrlf o disco tem CRLF e o git, LF."""
    return None if texto is None else texto.replace("\r\n", "\n")


def status_de(texto):
    if texto is None:
        return None
    m = RE_STATUS.search(texto[:4096])
    return m.group(1).strip("\"'").lower() if m else None


def sem_caixas(texto):
    return RE_CAIXA.sub(r"\1[ ]", texto or "")


def ocorrencias(texto, padroes):
    texto = texto or ""
    return {p: texto.count(p) for p in padroes if p in texto}


# --------------------------------------------------------------------------- regras

def promovido(proj, rel):
    """Artefato em HEAD, sem alteracao pendente e com status aprovado."""
    head = proj.em_head(rel)
    return head is not None and status_de(head) == "aprovado" and lf(proj.no_disco(rel)) == lf(head)


RE_PLACEHOLDER = re.compile(r"<[^<>\n]+>")
RE_CRASE = re.compile(r"`[^`\n]*`")


def tem_placeholder(linha):
    """<algo> fora de crase: sobra do template (genericos como `List<T>` ficam em crase)."""
    return RE_PLACEHOLDER.search(RE_CRASE.sub("", linha)) is not None


def tarefas_reais(texto, abertas=False):
    """Linhas de tarefa preenchidas (sem <placeholder> do template); so as abertas, se pedido."""
    linhas = [m.group(0) for m in RE_TAREFA.finditer(texto or "") if not tem_placeholder(m.group(0))]
    return [l for l in linhas if RE_CAIXA_ABERTA.match(l)] if abertas else linhas


def e_trabalho(tipo, texto):
    """Artefato que libera codigo: tarefas, bug, ou plano compacto com tarefas preenchidas."""
    return tipo in ("tasks", "bug") or (tipo == "plan" and bool(tarefas_reais(texto)))


def trabalho_liberado(proj, rel):
    """Tarefas (ou bug) aprovadas em HEAD; no disco so mudam as caixas de marcacao."""
    head = proj.em_head(rel)
    disco = proj.no_disco(rel)
    if head is None or disco is None or status_de(head) != "aprovado":
        return False
    return status_de(disco) == "aprovado" and sem_caixas(lf(disco)) == sem_caixas(lf(head))


def tarefas_ativas(proj):
    """Tarefas (ou bug) aprovadas com item pendente. Numa branch de feature, so as dela."""
    ativas = []
    feature = proj.feature_da_branch()
    for rel in proj.listar_specs():
        art = proj.artefato(rel)
        if feature and art and art[0] != feature:
            continue
        if art and e_trabalho(art[2], proj.no_disco(rel)) and trabalho_liberado(proj, rel):
            if tarefas_reais(proj.no_disco(rel), abertas=True):
                ativas.append(rel)
    return ativas


def novo_conteudo(ferramenta, entrada):
    """(texto_novo, texto_antigo) que a escrita introduz, para comparar padroes."""
    if ferramenta == "Write":
        return entrada.get("content") or "", None
    if ferramenta == "Edit":
        return entrada.get("new_string") or "", entrada.get("old_string") or ""
    if ferramenta == "MultiEdit":
        edits = entrada.get("edits") or []
        return ("\n".join(e.get("new_string") or "" for e in edits),
                "\n".join(e.get("old_string") or "" for e in edits))
    if ferramenta == "NotebookEdit":
        return entrada.get("new_source") or "", None
    return "", ""


def so_caixas(ferramenta, entrada):
    """A edicao so marca/desmarca tarefas?"""
    if ferramenta == "Edit":
        pares = [(entrada.get("old_string") or "", entrada.get("new_string") or "")]
    elif ferramenta == "MultiEdit":
        pares = [(e.get("old_string") or "", e.get("new_string") or "") for e in entrada.get("edits") or []]
    else:
        return False
    return bool(pares) and all(sem_caixas(lf(a)) == sem_caixas(lf(n)) for a, n in pares)


class Decisao(Exception):
    def __init__(self, tipo, motivo, branda=False):
        super().__init__(motivo)
        self.tipo = tipo          # deny | ask
        self.motivo = motivo
        self.branda = branda      # vira aviso quando o projeto esta em modo "aviso"


def avaliar_escrita(proj, ferramenta, entrada):
    alvo = entrada.get("file_path") or entrada.get("notebook_path") or ""
    if not alvo:
        return
    rel = proj.relativo(alvo)
    if rel is None:
        return

    novo, antigo = novo_conteudo(ferramenta, entrada)
    if antigo is None:
        antigo = proj.no_disco(rel) or ""

    # 1. Configuracao e gates sao do humano.
    if proj.protegido(rel):
        raise Decisao("ask", "SDD: {} controla o gate do projeto. Alteracao so com confirmacao humana.".format(rel))

    constituicao = proj.specs + "/constitution.md"
    if rel == constituicao:
        head = proj.em_head(rel)
        if RE_APROVADO.search(novo) and status_de(head) != "aprovado":
            raise Decisao("deny", "SDD: 'status: aprovado' e escrito so por uma pessoa. Deixe 'status: rascunho' e peca revisao humana.")
        if status_de(head) == "aprovado":
            raise Decisao("ask", "SDD: a constituicao aprovada so muda por emenda datada. Confirme, e registre a emenda na secao 'Emendas'.")
        return

    # Brief da descoberta: nao libera nada, mas a aprovacao continua humana.
    if rel.startswith("docs/descoberta/") and rel.endswith(".md"):
        if RE_APROVADO.search(novo) and status_de(proj.em_head(rel)) != "aprovado":
            raise Decisao("deny", "SDD: 'status: aprovado' e escrito so por uma pessoa. Deixe 'status: rascunho' e peca revisao humana.")
        return

    art = proj.artefato(rel)
    if art:
        num, slug, tipo = art
        head = proj.em_head(rel)
        aprovado_em_head = status_de(head) == "aprovado"

        # 2. O agente nunca promove um artefato.
        if RE_APROVADO.search(novo) and not aprovado_em_head:
            raise Decisao("deny", "SDD: 'status: aprovado' e escrito so por uma pessoa. Deixe 'status: rascunho' e peca revisao humana.")

        # 3. Artefato aprovado nao muda sem voltar a rascunho (exceto marcar tarefas).
        if aprovado_em_head:
            if tipo in ("tasks", "bug", "plan") and so_caixas(ferramenta, entrada):
                return
            raise Decisao("ask", "SDD: {} ja foi aprovado. Altera-lo reabre a revisao: confirme, e o humano volta o status para rascunho.".format(rel))

        # 4. Ordem das fases.
        base = "{}/{}-{}".format(proj.specs, num, slug)
        if tipo in ("spec", "bug") and not promovido(proj, constituicao):
            raise Decisao("deny", "SDD: a primeira feature espera a constituicao. {} precisa estar commitada, sem alteracao pendente e com 'status: aprovado'.".format(constituicao), branda=True)
        if tipo == "plan" and not promovido(proj, base + "-spec.md"):
            raise Decisao("deny", "SDD: /planejar bloqueado. {}-spec.md precisa estar commitado, sem alteracao pendente e com 'status: aprovado'.".format(base), branda=True)
        if tipo == "tasks" and not promovido(proj, base + "-plan.md"):
            raise Decisao("deny", "SDD: /tarefas bloqueado. {}-plan.md precisa estar commitado, sem alteracao pendente e com 'status: aprovado'.".format(base), branda=True)
        if tipo == "checklist" and proj.no_disco(base + "-spec.md") is None:
            raise Decisao("deny", "SDD: crie a spec antes do checklist.", branda=True)
        return

    # 5. Codigo de modulo so com tarefa aprovada e pendente.
    if proj.codigo(rel):
        if not tarefas_ativas(proj):
            feature = proj.feature_da_branch()
            if feature:
                raise Decisao("deny",
                              "SDD: /implementar bloqueado. A branch {b} e da feature {f} e nao ha "
                              "{s}/{f}-*-tasks.md (ou -bug.md) commitado, aprovado e com tarefa pendente. "
                              "Tarefas de outra feature nao liberam codigo nesta branch.".format(
                                  b=proj.branch_atual(), f=feature, s=proj.specs), branda=True)
            raise Decisao("deny",
                          "SDD: /implementar bloqueado. Nenhum {s}/NNN-slug-tasks.md (ou -bug.md) esta commitado, "
                          "aprovado e com tarefa pendente. Rode /especificar, /planejar e /tarefas (ou /corrigir), "
                          "com revisao humana entre as fases.".format(s=proj.specs), branda=True)

        # 6. Nada de desligar verificacao para "passar".
        antes = ocorrencias(antigo, proj.config["padroes_proibidos"])
        depois = ocorrencias(novo, proj.config["padroes_proibidos"])
        novos = [p for p, n in depois.items() if n > antes.get(p, 0)]
        if novos:
            raise Decisao("deny", "SDD: a escrita desativa verificacao ({}). Corrija o codigo, nao a verificacao. "
                                  "Se for inevitavel, explique ao humano e peca que ele faca a mudanca.".format(", ".join(novos)))


def avaliar_bash(proj, entrada):
    cmd = entrada.get("command") or ""
    if "--no-verify" in cmd:
        raise Decisao("deny", "SDD: --no-verify desliga as verificacoes do projeto.")
    if RE_APROVADO.search(cmd):
        raise Decisao("deny", "SDD: 'status: aprovado' e escrito so por uma pessoa.")
    if not proj.config.get("agente_pode_commitar") and RE_GIT_COMMIT.search(cmd):
        raise Decisao("deny", "SDD: commit, tag e push sao do humano. Diga o que esta pronto para commit e em qual modulo.")
    if RE_GIT_DESTRUTIVO.search(cmd):
        raise Decisao("ask", "SDD: comando git destrutivo. Confirme antes de executar.")
    if RE_ABRIR_PR.search(cmd) and proj.config.get("exigir_base_atualizada", True):
        base = base_de(proj)
        atraso = base_atrasada(proj, base, "HEAD") if base else None
        if atraso:
            raise Decisao("deny", "SDD: " + atraso, branda=True)


def modo_hook():
    try:
        evento = json.load(sys.stdin)
    except ValueError:
        return 0
    raiz = os.environ.get("CLAUDE_PROJECT_DIR") or evento.get("cwd") or os.getcwd()
    proj = Projeto(raiz)
    if not proj.ativo:
        return 0
    ferramenta = evento.get("tool_name") or ""
    entrada = evento.get("tool_input") or {}
    try:
        if ferramenta in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
            avaliar_escrita(proj, ferramenta, entrada)
        elif ferramenta == "Bash":
            avaliar_bash(proj, entrada)
    except Decisao as d:
        if d.branda and proj.aviso:
            print(json.dumps({"systemMessage": "[modo aviso] " + d.motivo}))
            return 0
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": d.tipo,
            "permissionDecisionReason": d.motivo,
        }}))
    return 0


# --------------------------------------------------------------------------- CI

def anotar(nivel, msg):
    """Anotacao no formato do CI em uso (Azure Pipelines ou GitHub Actions)."""
    if os.environ.get("TF_BUILD"):
        print("##vso[task.logissue type={}]{}".format(nivel, msg))
    else:
        print("::{}::{}".format(nivel, msg))


def base_atrasada(proj, base, head):
    """Mensagem de erro se `head` nao contem o ultimo commit de `base`, ou None.

    No PR o CI costuma fazer checkout do commit de merge (que ja contem a base); por isso
    o pipeline passa em `head` o ultimo commit da branch de origem.
    """
    if proj.git("rev-parse", "--verify", "--quiet", head + "^{commit}") is None:
        return "nao encontrei o commit de origem do PR ({}). Faca o checkout com historico completo.".format(head)
    if proj.git("merge-base", "--is-ancestor", base, head) is not None:
        return None
    atras = (proj.git("rev-list", "--count", "{}..{}".format(head, base)) or "?").strip()
    destino = base.split("/", 1)[1] if base.startswith("origin/") else base
    return ("a branch esta {} commit(s) atras de {}. Traga a {} para a branch antes do PR: "
            "git fetch origin && git merge {} (resolva conflitos, rode build e testes, commite e de push).").format(
                atras, base, destino, base)


def modo_ci(base, head="HEAD"):
    proj = Projeto(os.getcwd())
    base = re.sub(r"^refs/heads/", "origin/", base or base_de(proj) or "origin/" + principal_de(proj))
    if not proj.ativo:
        print("SDD: {} nao encontrado; nada a verificar.".format(CONFIG_REL))
        return 0
    merge_base = (proj.git("merge-base", base, "HEAD") or "").strip()
    if not merge_base:
        anotar("error", "SDD: nao encontrei o merge-base com {}. Faca o checkout com historico completo.".format(base))
        return 1
    mudados = [l for l in (proj.git("diff", "--name-only", "--diff-filter=ACMR", merge_base, "HEAD") or "").splitlines() if l]

    erros = []
    if proj.config.get("exigir_base_atualizada", True):
        atraso = base_atrasada(proj, base, head or "HEAD")
        if atraso:
            erros.append(atraso)
    codigo = [r for r in mudados if proj.codigo(r)]
    artefatos = [r for r in mudados if proj.artefato(r)]

    na_base = {}
    for rel in proj.listar_specs(base):
        art = proj.artefato(rel)
        if art:
            na_base.setdefault(art[0], set()).add(art[1])
    for rel in artefatos:
        num, slug, tipo = proj.artefato(rel)
        outros = na_base.get(num, set()) - {slug}
        if outros:
            erros.append("{} usa o numero {} que ja pertence a {}-{} em {}. Renumere a feature "
                         "(rode o status para ver o proximo livre).".format(rel, num, num, sorted(outros)[0], base))
        st = status_de(proj.em_head(rel))
        base_rel = "{}/{}-{}".format(proj.specs, num, slug)
        if codigo and st != "aprovado" and tipo != "checklist":
            erros.append("{} esta '{}' e o PR tambem altera codigo. Aprove o artefato em um PR proprio ou antes do codigo.".format(rel, st))
        if tipo == "plan" and status_de(proj.em_head(base_rel + "-spec.md")) != "aprovado":
            erros.append("{} existe sem {}-spec.md aprovado.".format(rel, base_rel))
        if tipo == "tasks" and status_de(proj.em_head(base_rel + "-plan.md")) != "aprovado":
            erros.append("{} existe sem {}-plan.md aprovado.".format(rel, base_rel))

    if codigo:
        trabalho = [r for r in artefatos if e_trabalho(proj.artefato(r)[2], proj.em_head(r))
                    and status_de(proj.em_head(r)) == "aprovado"]
        if not trabalho:
            erros.append("O PR altera codigo ({} arquivo(s)) mas nao marca nenhuma tarefa de um "
                         "-tasks.md, -bug.md ou plano compacto aprovado. Toda mudanca de codigo rastreia para uma tarefa.".format(len(codigo)))
        for rel in trabalho:
            antes = proj.em_head(rel, merge_base)
            if antes is not None and status_de(antes) == "aprovado" and sem_caixas(antes) != sem_caixas(proj.em_head(rel)):
                erros.append("{} foi alterado alem das caixas de marcacao depois de aprovado.".format(rel))
            # Feature concluida: as specs vivas precisam refletir as mudancas de comportamento.
            atual = proj.em_head(rel) or ""
            if RE_TAREFA.search(atual) and not RE_CAIXA_ABERTA.search(atual):
                num = proj.artefato(rel)[0]
                _, spec = spec_da_feature(proj, num)
                deltas = deltas_da_spec(spec)
                if deltas:
                    _, pendencias, erros_d = aplicar_deltas(proj, num, deltas)
                    erros.extend("{}: {}".format(rel, e) for e in erros_d)
                    if pendencias:
                        erros.append("feature {} concluida mas {}/vivas/ nao reflete a spec ({}). Rode "
                                     "sdd_gate.py consolidar {} e commite.".format(num, proj.specs, "; ".join(pendencias), num))

        diff = proj.git("diff", "-U0", merge_base, "HEAD", "--", *codigo) or ""
        adicionadas = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
        texto = "\n".join(adicionadas)
        for p in proj.config["padroes_proibidos"]:
            if p in texto:
                erros.append("Linha adicionada desativa verificacao: '{}'.".format(p))

    nivel = "warning" if proj.aviso else "error"
    for e in erros:
        anotar(nivel, "SDD: " + e)
    if not erros:
        print("SDD: ok ({} arquivo(s) de codigo, {} artefato(s)).".format(len(codigo), len(artefatos)))
        return 0
    return 0 if proj.aviso else 1


# --------------------------------------------------------------------------- sincronia

def principal_de(proj):
    return (proj.config or PADRAO).get("branch_principal") or "main"


def base_de(proj):
    """Ref da branch base: origin/<principal> quando existe, senao a branch local, senao None."""
    principal = principal_de(proj)
    for ref in ("origin/" + principal, principal):
        if proj.git("rev-parse", "--verify", "--quiet", ref + "^{commit}") is not None:
            return ref
    return None


def modo_sincronia():
    """0 = branch de trabalho com a principal em dia; 1 = na principal ou atrasada; 2 = sem a base."""
    proj = Projeto(os.getcwd())
    principal = principal_de(proj)
    base = base_de(proj)
    if base is None:
        print("SDD: a branch base {p} nao existe neste clone (nem origin/{p}). Rode git fetch origin "
              "ou corrija branch_principal em {c}.".format(p=principal, c=CONFIG_REL))
        return 2
    atual = (proj.git("rev-parse", "--abbrev-ref", "HEAD") or "").strip()
    if atual == principal:
        print("SDD: voce esta na {p}. Crie a branch da feature a partir dela atualizada: "
              "git switch {p} && git pull && git switch -c feat/<NNN>-<slug> (o /especificar faz isso por voce)".format(p=principal))
        return 1
    atraso = base_atrasada(proj, base, "HEAD")
    if atraso:
        print("SDD: " + atraso)
        return 1
    print("SDD: branch {} em dia com {}.".format(atual, base))
    return 0


# --------------------------------------------------------------------------- status

def refs_de_trabalho(proj):
    """Branches locais e remotas, menos a principal e HEAD simbolico."""
    principal = principal_de(proj)
    saida = proj.git("for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/remotes") or ""
    refs = []
    for r in saida.splitlines():
        r = r.strip()
        nome = r.split("/", 1)[1] if r.startswith("origin/") else r
        if not r or r.endswith("/HEAD") or nome == principal or r == "origin":
            continue
        refs.append(r)
    return refs


def numeros_reservados(proj, refs):
    """{NNN: [onde]} vindos dos nomes de branch e dos artefatos em specs/ de cada branch."""
    usados = {}
    for r in refs:
        m = RE_BRANCH_FEATURE.search(r)
        if m:
            usados.setdefault(m.group(1), set()).add(r)
        for rel in proj.listar_specs(r):
            nome = rel.rsplit("/", 1)[-1]
            ma = RE_ARTEFATO.match(nome)
            if ma:
                usados.setdefault(ma.group(1), set()).add(r)
    return {k: sorted(v) for k, v in usados.items()}


def features_em_andamento(proj, refs):
    """{NNN: {"refs": [...], "modulos": set}} das branches de feature ainda nao integradas."""
    base = base_de(proj) or principal_de(proj)
    nomes = {(m.get("nome") or "").lower(): m.get("nome") for m in (proj.config or {}).get("modulos") or []}
    andamento = {}
    for r in refs:
        m = RE_BRANCH_FEATURE.search(r)
        if not m:
            continue
        mb = (proj.git("merge-base", base, r) or "").strip()
        if not mb:
            continue
        mudados = [l for l in (proj.git("diff", "--name-only", mb, r) or "").splitlines() if l]
        if not mudados:
            continue
        f = andamento.setdefault(m.group(1), {"refs": [], "modulos": set()})
        f["refs"].append(r)
        for rel in mudados:
            mod = proj.modulo_de(rel)
            if mod:
                f["modulos"].add(mod)
            art = proj.artefato(rel)
            if art and art[2] in ("spec", "bug"):
                ms = RE_MODULOS_SPEC.search(proj.em_head(rel, r) or "")
                for palavra in re.findall(r"[\w.-]+", ms.group(1) if ms else ""):
                    if palavra.lower() in nomes:
                        f["modulos"].add(nomes[palavra.lower()])
    return andamento


def sobreposicoes(andamento):
    """[(modulo, [NNN, ...])] com mais de uma feature em andamento."""
    por_modulo = {}
    for num, f in andamento.items():
        for mod in f["modulos"]:
            por_modulo.setdefault(mod, set()).add(num)
    return sorted((m, sorted(n)) for m, n in por_modulo.items() if len(n) > 1)


def modo_status(como_json):
    proj = Projeto(os.getcwd())
    specs_dir = os.path.join(proj.raiz, proj.specs if proj.ativo else "specs")
    features = {}
    maior = 0
    if os.path.isdir(specs_dir):
        for nome in sorted(os.listdir(specs_dir)):
            m = RE_ARTEFATO.match(nome)
            if not m:
                continue
            num, slug, tipo = m.groups()
            maior = max(maior, int(num))
            with open(os.path.join(specs_dir, nome), encoding="utf-8") as arq:
                texto = arq.read()
            f = features.setdefault(num, {"numero": num, "slug": slug})
            item = {"status": status_de(texto)}
            if tipo in ("tasks", "bug"):
                item["feitas"] = len(RE_CAIXA_FECHADA.findall(texto))
                item["total"] = item["feitas"] + len(RE_CAIXA_ABERTA.findall(texto))
            f[tipo] = item
    lista = [features[k] for k in sorted(features)]
    refs = refs_de_trabalho(proj)
    reservados = numeros_reservados(proj, refs)
    maior = max([maior] + [int(n) for n in reservados])
    proximo = "{:03d}".format(maior + 1)
    andamento = features_em_andamento(proj, refs) if proj.ativo else {}
    conflitos = sobreposicoes(andamento)
    copia = proj.no_disco(".sdd/sdd_gate.py") if proj.ativo else None
    mv = re.search(r'^VERSAO = "([^"]+)"', copia or "", re.M)
    versao_copia = mv.group(1) if mv else ("anterior a 0.1.22" if copia else None)
    if como_json:
        print(json.dumps({
            "sdd": proj.ativo, "proximo": proximo, "features": lista,
            "em_andamento": {k: {"refs": v["refs"], "modulos": sorted(v["modulos"])} for k, v in sorted(andamento.items())},
            "sobreposicoes": [{"modulo": m, "features": n} for m, n in conflitos],
            "gate": {"plugin": VERSAO, "projeto": versao_copia},
        }, ensure_ascii=False, indent=2))
        return 0
    if not proj.ativo:
        print("Projeto sem {} (rode /prepararsdd).".format(CONFIG_REL))
    print("| Feature | Spec | Plano | Tarefas | Bug |")
    print("| --- | --- | --- | --- | --- |")
    for f in lista:
        def cel(t):
            i = f.get(t)
            if not i:
                return "-"
            s = i["status"] or "?"
            return "{} ({}/{})".format(s, i["feitas"], i["total"]) if "total" in i else s
        print("| {}-{} | {} | {} | {} | {} |".format(f["numero"], f["slug"], cel("spec"), cel("plan"), cel("tasks"), cel("bug")))
    if andamento:
        print("\nEm andamento em outras branches:")
        for num, f in sorted(andamento.items()):
            print("- {}: {} (modulos: {})".format(num, ", ".join(f["refs"]), ", ".join(sorted(f["modulos"])) or "?"))
    for mod, nums in conflitos:
        print("\nATENCAO: as features {} mexem no modulo {} ao mesmo tempo. Combine a ordem de merge "
              "ou junte as duas antes de implementar.".format(", ".join(nums), mod))
    if versao_copia and versao_copia != VERSAO:
        print("\nATENCAO: .sdd/sdd_gate.py do projeto e da versao {}; o plugin e {}. O check do PR roda "
              "a copia do projeto: atualize com cp \"<plugin>/hooks/sdd_gate.py\" .sdd/ (o /prepararsdd mostra o "
              "caminho) e commite.".format(versao_copia, VERSAO))
    print("\nProximo numero livre: {} (considerando {} branch(es))".format(proximo, len(refs)))
    return 0


# --------------------------------------------------------------------------- contexto

RE_TAREFA = re.compile(r"^\s*[-*]\s*\[([ xX])\]\s*(T-\d+)\b(.*)$", re.M)
RE_DEPENDE = re.compile(r"depende\s+de\s+([^·]+)", re.I)
RE_ID_T = re.compile(r"\bT-\d+\b")
RE_IDS = re.compile(r"\b(?:RF|RNF|CA|US|QA|U|D|R)-\d+\b")
RE_MODULO_TAREFA = re.compile(r"m[oó]dulos?\s+([\w./-]+)", re.I)
RE_ITEM_ID = re.compile(r"^\s*[-*]\s*\*\*((?:RF|RNF|CA|US|QA|U|D|R)-\d+)\*\*")
LIMITE_TRECHO = 40


def arquivos_da_feature(proj, numero):
    """{tipo: rel} dos artefatos da feature no disco."""
    achados = {}
    pasta = os.path.join(proj.raiz, proj.specs)
    if os.path.isdir(pasta):
        for nome in sorted(os.listdir(pasta)):
            m = RE_ARTEFATO.match(nome)
            if m and m.group(1) == numero:
                achados[m.group(3)] = proj.specs + "/" + nome
    return achados


def tarefas_de(texto):
    """[{id, feita, linha, depende}] na ordem do arquivo."""
    tarefas = []
    for m in RE_TAREFA.finditer(texto or ""):
        linha = m.group(0).strip()
        dep = RE_DEPENDE.search(m.group(3))
        tarefas.append({
            "id": m.group(2), "feita": m.group(1) != " ", "linha": linha,
            "depende": RE_ID_T.findall(dep.group(1)) if dep else [],
        })
    return tarefas


def proxima_tarefa(tarefas):
    feitas = {t["id"] for t in tarefas if t["feita"]}
    for t in tarefas:
        if not t["feita"] and all(d in feitas for d in t["depende"]):
            return t
    return None


def trechos(texto, ids):
    """Itens `- **ID**` e linhas de tabela que citam algum dos ids; CA que citam um RF pedido."""
    saida = []
    for linha in (texto or "").splitlines():
        m = RE_ITEM_ID.match(linha)
        if m:
            citados = set(RE_IDS.findall(linha))
            if m.group(1) in ids or (m.group(1).startswith("CA-") and citados & ids):
                saida.append(linha.rstrip())
        elif linha.lstrip().startswith("|") and set(RE_IDS.findall(linha)) & ids:
            saida.append(linha.rstrip())
    return saida[:LIMITE_TRECHO]


def linhas_do_modulo(texto, modulo):
    """Linhas de tabela do plano cuja primeira coluna e o modulo."""
    saida = []
    for linha in (texto or "").splitlines():
        cels = [c.strip().strip("`") for c in linha.strip().strip("|").split("|")]
        if linha.lstrip().startswith("|") and cels and cels[0].lower() == modulo.lower():
            saida.append(linha.rstrip())
    return saida[:LIMITE_TRECHO]


def resolver_feature(proj, numero):
    if numero:
        return numero.zfill(3)
    feature = proj.feature_da_branch()
    if feature:
        return feature
    nums = sorted({proj.artefato(rel)[0] for rel in tarefas_ativas(proj)})
    return nums[0] if len(nums) == 1 else None


def modo_contexto(numero, como_json):
    """Contexto minimo para implementar a proxima tarefa: so o que a linha da tarefa cita."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # artefatos tem acento e travessao; no Windows o padrao e cp1252
    proj = Projeto(os.getcwd())
    if not proj.ativo:
        print("SDD: projeto sem {} (rode /prepararsdd).".format(CONFIG_REL))
        return 2
    num = resolver_feature(proj, numero)
    if not num:
        print("SDD: informe a feature (ex.: contexto 004). Nao deu para deduzir pela branch "
              "nem por uma unica lista de tarefas aprovada com pendencias.")
        return 2
    arqs = arquivos_da_feature(proj, num)
    trabalho = arqs.get("tasks") or arqs.get("bug")
    if not trabalho and arqs.get("plan") and e_trabalho("plan", proj.no_disco(arqs["plan"])):
        trabalho = arqs["plan"]
    if not trabalho:
        print("SDD: a feature {} nao tem {}/{}-*-tasks.md nem -bug.md.".format(num, proj.specs, num))
        return 2
    texto_trabalho = lf(proj.no_disco(trabalho)) or ""
    tarefas = tarefas_de(texto_trabalho)
    prox = proxima_tarefa(tarefas)
    resultado = {
        "feature": num,
        "arquivos": arqs,
        "liberado": trabalho_liberado(proj, trabalho),
        "feitas": sum(1 for t in tarefas if t["feita"]),
        "total": len(tarefas),
        "tarefa": prox,
        "pendentes_bloqueadas": [t["linha"] for t in tarefas if not t["feita"] and t is not prox],
    }
    if prox:
        ids = set(RE_IDS.findall(prox["linha"]))
        mod_nome = None
        mm = RE_MODULO_TAREFA.search(prox["linha"])
        if mm:
            mod_nome = mm.group(1).rstrip(".,;")
        modulo = None
        for mod in proj.config.get("modulos") or []:
            if mod_nome and (mod.get("nome") or "").lower() == mod_nome.lower():
                modulo = {
                    "nome": mod.get("nome"),
                    "caminho": mod.get("caminho"),
                    "instructions": mod.get("instructions") or "instructions/{}.md".format(mod.get("nome")),
                    "verificacao": mod.get("verificacao") or [],
                }
        resultado["modulo"] = modulo or ({"nome": mod_nome} if mod_nome else None)
        fonte_spec = arqs.get("spec") or arqs.get("bug")
        resultado["spec"] = trechos(lf(proj.no_disco(fonte_spec)) if fonte_spec else "", ids)
        plano = lf(proj.no_disco(arqs["plan"])) if arqs.get("plan") else ""
        doplano = trechos(plano, ids)
        if modulo and not any(l.lstrip().startswith("|") for l in doplano):
            doplano += [l for l in linhas_do_modulo(plano, modulo["nome"]) if l not in doplano]
        resultado["plano"] = doplano[:LIMITE_TRECHO]
    if como_json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0

    print("# Contexto da feature {}".format(num))
    print("Arquivos: " + ", ".join("{}={}".format(k, v) for k, v in sorted(arqs.items())))
    print("Tarefas: {}/{} feitas. Lista liberada pelo gate: {}.".format(
        resultado["feitas"], resultado["total"], "sim" if resultado["liberado"] else
        "NAO (precisa estar commitada, aprovada e sem alteracao alem das caixas)"))
    if not prox:
        if resultado["pendentes_bloqueadas"]:
            print("\nNenhuma tarefa pendente com dependencias prontas:")
            for l in resultado["pendentes_bloqueadas"]:
                print("- " + l)
        else:
            print("\nSem tarefas pendentes: o proximo passo e /verificar {}.".format(num))
        return 0
    print("\n## Proxima tarefa\n" + prox["linha"])
    mod = resultado["modulo"]
    if mod:
        print("\n## Modulo")
        print("- nome: {}".format(mod["nome"]))
        if mod.get("instructions"):
            print("- leia antes: {}".format(mod["instructions"]))
            print("- caminho: {}".format(mod.get("caminho")))
            for c in mod.get("verificacao") or []:
                print("- verificacao: `{}`".format(c))
    print("\n## Da spec ({} citados pela tarefa)".format(", ".join(sorted(ids)) or "nenhum id"))
    print("\n".join(resultado["spec"]) or "(nada encontrado: abra a spec)")
    print("\n## Do plano")
    print("\n".join(resultado["plano"]) or "(nada encontrado: abra o plano)")
    print("\nSe isto nao bastar (contrato entre modulos, decisao D-n, ADR), abra o arquivo completo e diga por que.")
    return 0


# --------------------------------------------------------------------------- revisao

RE_SENSIVEL = re.compile(
    r"(?i)(senha|password|passwd|secret|segredo|(?<!cancellation)token|jwt|bearer|api[_-]?key|connection\s*string|"
    r"authoriz|authenticat|autentica|autoriza|\bcpf\b|\bcnpj\b|crypt|cookie|cors)")


def diff_para_revisao(proj, base):
    """(texto do diff, arquivos mudados, arquivos novos). Sem base: mudancas nao commitadas."""
    if base:
        ref = (proj.git("merge-base", base, "HEAD") or "").strip()
        if not ref:
            return None, [], []
    else:
        ref = "HEAD"
    diff = proj.git("diff", ref) or ""
    arquivos = [l for l in (proj.git("diff", "--name-only", ref) or "").splitlines() if l]
    criados = [l for l in (proj.git("diff", "--name-only", "--diff-filter=A", ref) or "").splitlines() if l]
    novos = [l for l in (proj.git("ls-files", "--others", "--exclude-standard") or "").splitlines() if l]
    for rel in novos:
        texto = proj.no_disco(rel)
        if texto is None:
            continue
        linhas = texto.splitlines()
        diff += "diff --git a/{0} b/{0}\nnew file\n--- /dev/null\n+++ b/{0}\n@@ -0,0 +1,{1} @@\n{2}\n".format(
            rel, len(linhas), "\n".join("+" + l for l in linhas))
        arquivos.append(rel)
    return diff, sorted(set(arquivos)), sorted(set(criados + novos))


def sensivel(proj, rel):
    for padrao in proj.config.get("areas_sensiveis") or []:
        if padrao.endswith("/") and rel.startswith(padrao):
            return True
        if fnmatch.fnmatch(rel, padrao):
            return True
    return False


def modo_revisao(base, como_json):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    proj = Projeto(os.getcwd())
    if not proj.ativo:
        print("SDD: projeto sem {}.".format(CONFIG_REL))
        return 2
    if base == "principal":
        base = base_de(proj) or principal_de(proj)
    diff, arquivos, criados = diff_para_revisao(proj, base)
    if diff is None:
        print("SDD: nao encontrei o merge-base com {}.".format(base))
        return 2
    codigo = [r for r in arquivos if proj.codigo(r)]
    adicionadas = [l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++")]
    removidas = [l for l in diff.splitlines() if l.startswith("-") and not l.startswith("---")]
    por_area = [r for r in arquivos if sensivel(proj, r)]
    por_conteudo = sorted({m.group(1).lower() for l in adicionadas for m in [RE_SENSIVEL.search(l)] if m})
    limite = int(proj.config.get("limite_revisao") or 50)
    tamanho = len(adicionadas) + len(removidas)
    git_dir = (proj.git("rev-parse", "--absolute-git-dir") or "").strip()
    pasta = os.path.join(git_dir, "sdd") if git_dir else None
    if pasta:
        os.makedirs(pasta, exist_ok=True)
        antigos = sorted((os.path.join(pasta, n) for n in os.listdir(pasta) if n.startswith("revisao-")),
                         key=os.path.getmtime)
        for antigo in antigos[:-4]:  # mantem so os diffs mais recentes
            try:
                os.remove(antigo)
            except OSError:
                pass
    fd, caminho = tempfile.mkstemp(prefix="revisao-", suffix=".diff", dir=pasta)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(diff)
    motivos_codigo = []
    if codigo and tamanho >= limite:
        motivos_codigo.append("{} linhas alteradas (limite {})".format(tamanho, limite))
    novos_codigo = [r for r in codigo if r in criados]
    if novos_codigo:
        motivos_codigo.append("arquivo(s) de codigo novo(s): " + ", ".join(novos_codigo))
    motivos_seg = []
    if por_area:
        motivos_seg.append("area sensivel: " + ", ".join(por_area))
    if por_conteudo:
        motivos_seg.append("termos sensiveis nas linhas adicionadas: " + ", ".join(por_conteudo))
    resultado = {
        "diff": caminho.replace("\\", "/"), "base": base, "arquivos": arquivos, "codigo": codigo,
        "linhas": tamanho, "revisor_de_codigo": bool(motivos_codigo), "motivos_codigo": motivos_codigo,
        "revisor_de_seguranca": bool(motivos_seg), "motivos_seguranca": motivos_seg,
    }
    if como_json:
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
        return 0
    print("Diff gravado em {} ({} arquivo(s), {} de codigo, {} linhas).".format(
        resultado["diff"], len(arquivos), len(codigo), tamanho))
    print("- revisor-de-codigo: {}".format("SIM — " + "; ".join(motivos_codigo) if motivos_codigo else
                                           "dispensado (mudanca pequena, sem arquivo novo)"))
    print("- revisor-de-seguranca: {}".format("SIM — " + "; ".join(motivos_seg) if motivos_seg else
                                              "dispensado (nada sensivel no diff)"))
    print("Passe ao revisor o caminho do diff, nao o texto.")
    return 0


# --------------------------------------------------------------------------- cobertura

RE_CA_TESTE = re.compile(r"F(\d{3})_CA_?(\d+)(?!\d)")


def arquivos_de_teste(proj):
    bases = [m.get("caminho", "").strip("/") for m in proj.config.get("modulos") or [] if m.get("caminho")] or [""]
    exts = set(proj.config["extensoes_fonte"])
    for base in bases:
        raiz = os.path.join(proj.raiz, base)
        for pasta, dirs, nomes in os.walk(raiz):
            rel_pasta = os.path.relpath(pasta, proj.raiz).replace("\\", "/")
            dirs[:] = [d for d in dirs if not d.startswith(".") and
                       not any(e.strip("/") == d for e in proj.config["excluidos"])]
            for nome in nomes:
                if os.path.splitext(nome)[1].lower() in exts and re.search(r"(?i)test|spec", rel_pasta + "/" + nome):
                    yield (nome if rel_pasta == "." else rel_pasta + "/" + nome)


def resultados_de_testes(caminhos):
    """{nome do teste: passou|falhou|ignorado} de arquivos TRX (dotnet) ou JUnit XML."""
    saida = {}
    for caminho in caminhos:
        try:
            raiz = ET.parse(caminho).getroot()
        except (ET.ParseError, OSError) as e:
            print("AVISO: nao li {}: {}".format(caminho, e))
            continue
        for el in raiz.iter():
            tag = el.tag.split("}")[-1]
            if tag == "UnitTestResult":
                desfecho = (el.get("outcome") or "").lower()
                saida[el.get("testName") or ""] = {"passed": "passou", "failed": "falhou"}.get(desfecho, "ignorado")
            elif tag == "testcase":
                filhos = {c.tag.split("}")[-1] for c in el}
                estado = "falhou" if filhos & {"failure", "error"} else "ignorado" if "skipped" in filhos else "passou"
                saida["{}.{}".format(el.get("classname") or "", el.get("name") or "")] = estado
    return saida


def modo_cobertura(numero, resultados, como_json):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    proj = Projeto(os.getcwd())
    num = resolver_feature(proj, numero) if proj.ativo else None
    if not num:
        print("SDD: informe a feature (ex.: cobertura 004).")
        return 2
    _, spec = spec_da_feature(proj, num)
    cas = [i for i, _ in itens(spec or "", "CA")]
    if not cas:
        print("SDD: a feature {} nao tem criterios de aceite.".format(num))
        return 2
    achados = {ca: [] for ca in cas}
    for rel in arquivos_de_teste(proj):
        texto = proj.no_disco(rel) or ""
        for n, linha in enumerate(texto.splitlines(), 1):
            for m in RE_CA_TESTE.finditer(linha):
                ca = "CA-" + str(int(m.group(2)))
                if m.group(1) == num and ca in achados:
                    nome = re.search(r"\w*" + re.escape(m.group(0)) + r"\w*", linha).group(0)
                    achados[ca].append({"onde": "{}:{}".format(rel, n), "teste": nome})
    execucao = resultados_de_testes(resultados or [])
    linhas, falhas = [], 0
    for ca in cas:
        testes = achados[ca]
        estados = []
        for t in testes:
            casou = [v for k, v in execucao.items() if t["teste"] in k]
            t["resultado"] = ("falhou" if "falhou" in casou else "ignorado" if "ignorado" in casou else
                              "passou" if casou else "nao executado")
            estados.append(t["resultado"])
        if not testes:
            situacao = "SEM TESTE"
        elif "falhou" in estados or "ignorado" in estados:
            situacao = "FALHOU" if "falhou" in estados else "IGNORADO"
        elif execucao and all(e == "passou" for e in estados):
            situacao = "OK"
        else:
            situacao = "nao executado" if not execucao else "PARCIAL"
        if situacao in ("SEM TESTE", "FALHOU", "IGNORADO", "PARCIAL"):
            falhas += 1
        linhas.append({"ca": ca, "situacao": situacao, "testes": testes})
    if como_json:
        print(json.dumps({"feature": num, "criterios": linhas}, ensure_ascii=False, indent=2))
    else:
        print("| CA | Situacao | Testes |")
        print("| --- | --- | --- |")
        for l in linhas:
            print("| {} | {} | {} |".format(l["ca"], l["situacao"], "; ".join(
                "{} ({}) {}".format(t["teste"], t["onde"], t["resultado"]) for t in l["testes"]) or "-"))
        print("\nConvencao: o nome do teste contem F{}_CA_<n> (ex.: F{}_CA_2_bloqueia_apos_5_falhas).".format(num, num))
        if not resultados:
            print("Sem --resultados: so a existencia dos testes foi conferida. Gere TRX (dotnet test --logger trx) "
                  "ou JUnit XML e passe os arquivos.")
    return 1 if falhas else 0


# --------------------------------------------------------------------------- specs vivas

RE_CAPACIDADE = re.compile(r"^###\s+Capacidade:\s*(\S+)\s*$", re.M)
RE_OPERACAO = re.compile(r"^####\s+(ADICIONADO|ALTERADO|REMOVIDO)\s*$", re.M | re.I)
RE_REQUISITO = re.compile(r"^#{3,5}\s+Requisito:\s*(.+?)\s*$", re.M)
RE_NOME_CAPACIDADE = re.compile(r"^[a-z0-9][a-z0-9-]*(?:/[a-z0-9][a-z0-9-]*)*$")
SECAO_DELTAS = "Mudanças no comportamento vigente"


def secao(texto, titulo):
    """Texto da secao `## ... titulo` ate o proximo `## `, ou None."""
    m = re.search(r"^##\s+(?:\d+\.\s*)?" + re.escape(titulo) + r"\s*$", texto or "", re.M)
    if not m:
        return None
    resto = texto[m.end():]
    fim = re.search(r"^##\s", resto, re.M)
    return resto[:fim.start()] if fim else resto


def blocos(texto, regex):
    """[(titulo, corpo)] para cada cabecalho que casa com regex."""
    achados = list(regex.finditer(texto or ""))
    saida = []
    for i, m in enumerate(achados):
        fim = achados[i + 1].start() if i + 1 < len(achados) else len(texto)
        saida.append((m.group(1).strip(), texto[m.end():fim]))
    return saida


def normalizar_corpo(corpo):
    linhas = [l.rstrip() for l in (corpo or "").strip().splitlines() if not l.strip().startswith("<!--")]
    return "\n".join(linhas).strip()


def deltas_da_spec(texto):
    """{capacidade: [(operacao, titulo, corpo)]} da secao de mudancas no comportamento vigente."""
    sec = secao(texto, SECAO_DELTAS)
    if sec is None:
        return {}
    deltas = {}
    for cap, corpo_cap in blocos(sec, RE_CAPACIDADE):
        lista = deltas.setdefault(cap, [])
        for op, corpo_op in blocos(corpo_cap, RE_OPERACAO):
            for titulo, corpo in blocos(corpo_op, RE_REQUISITO):
                lista.append((op.upper(), titulo, normalizar_corpo(corpo)))
    return deltas


def caminho_viva(proj, cap):
    return "{}/vivas/{}.md".format(proj.specs, cap)


def viva_externa(proj, cap):
    """Caminho da spec viva da capacidade num repositorio externo (somente leitura), ou None."""
    for pasta in proj.config.get("specs_vivas_externas") or []:
        caminho = os.path.normpath(os.path.join(proj.raiz, pasta, cap + ".md"))
        if os.path.isfile(caminho):
            return caminho.replace("\\", "/")
    return None


def requisitos_vivos(texto):
    """[(titulo, corpo)] na ordem do arquivo."""
    return [(t, normalizar_corpo(c)) for t, c in blocos(texto or "", RE_REQUISITO)]


def montar_viva(cap, requisitos, cabecalho=None):
    if cabecalho and cabecalho.strip():
        partes = [cabecalho.strip() + "\n"]
    else:
        partes = ["# Capacidade: {}\n".format(cap),
                  "Comportamento vigente. Atualizado por `sdd_gate.py consolidar` ao fim de cada feature, "
                  "a partir da secao \"{}\" da spec.\n".format(SECAO_DELTAS)]
    for titulo, corpo, origem in requisitos:
        partes.append("### Requisito: {}\n<!-- origem: {} -->\n{}\n".format(titulo, origem, corpo))
    return "\n".join(partes)


def aplicar_deltas(proj, num, deltas):
    """(novos_textos {rel: texto}, pendencias [str], erros [str]) sem gravar nada."""
    novos, pendencias, erros = {}, [], []
    for cap, ops in sorted(deltas.items()):
        if not RE_NOME_CAPACIDADE.match(cap):
            erros.append("capacidade '{}' invalida: use kebab-case, com / para subniveis".format(cap))
            continue
        rel = caminho_viva(proj, cap)
        atual = lf(proj.no_disco(rel))
        externa = viva_externa(proj, cap) if atual is None else None
        if externa:
            erros.append("{}: capacidade de outro repositorio ({}), somente leitura aqui. Mude-a por PR "
                         "no repositorio dono e cite a mudanca na spec, fora da secao de mudancas.".format(cap, externa))
            continue
        origem_de = {}
        for m in re.finditer(r"^###\s+Requisito:\s*(.+?)\s*\n<!--\s*origem:\s*(\S+)\s*-->", atual or "", re.M):
            origem_de[m.group(1).strip()] = m.group(2)
        reqs = [[t, c, origem_de.get(t, "?")] for t, c in requisitos_vivos(atual)]
        por_titulo = {r[0]: r for r in reqs}
        mudou = False
        for op, titulo, corpo in ops:
            existente = por_titulo.get(titulo)
            if op == "ADICIONADO":
                if existente is None:
                    reqs.append([titulo, corpo, num]); por_titulo[titulo] = reqs[-1]; mudou = True
                    pendencias.append("{}: adicionar '{}'".format(cap, titulo))
                elif existente[1] != corpo:
                    erros.append("{}: '{}' ja existe com outro texto; use ALTERADO".format(cap, titulo))
            elif op == "ALTERADO":
                if existente is None:
                    erros.append("{}: '{}' nao existe na spec viva {}; use o titulo exato ou ADICIONADO".format(cap, titulo, rel))
                elif existente[1] != corpo:
                    existente[1], existente[2] = corpo, num; mudou = True
                    pendencias.append("{}: alterar '{}'".format(cap, titulo))
            elif op == "REMOVIDO":
                if existente is not None:
                    reqs.remove(existente); del por_titulo[titulo]; mudou = True
                    pendencias.append("{}: remover '{}'".format(cap, titulo))
        if mudou:
            primeiro = RE_REQUISITO.search(atual or "")
            cabecalho = (atual or "")[:primeiro.start()] if primeiro else atual
            novos[rel] = montar_viva(cap, reqs, cabecalho)
    return novos, pendencias, erros


def spec_da_feature(proj, num):
    arqs = arquivos_da_feature(proj, num)
    rel = arqs.get("spec") or arqs.get("bug")
    return rel, lf(proj.no_disco(rel)) if rel else None


def modo_consolidar(numero, so_verificar):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    proj = Projeto(os.getcwd())
    num = resolver_feature(proj, numero) if proj.ativo else None
    if not num:
        print("SDD: informe a feature (ex.: consolidar 004).")
        return 2
    rel, texto = spec_da_feature(proj, num)
    if not rel:
        print("SDD: a feature {} nao tem spec nem bug.".format(num))
        return 2
    deltas = deltas_da_spec(texto)
    if not deltas:
        print("SDD: {} nao tem a secao \"{}\"; nada a consolidar.".format(rel, SECAO_DELTAS))
        return 0
    novos, pendencias, erros = aplicar_deltas(proj, num, deltas)
    for e in erros:
        print("ERRO: " + e)
    if erros:
        return 1
    if not pendencias:
        print("SDD: specs vivas ja refletem {}.".format(rel))
        return 0
    if so_verificar:
        print("SDD: specs vivas desatualizadas em relacao a {}:".format(rel))
        for p in pendencias:
            print("- " + p)
        print("Rode: sdd_gate.py consolidar {} e inclua o resultado no PR.".format(num))
        return 1
    for alvo, conteudo in novos.items():
        caminho = os.path.join(proj.raiz, alvo)
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            f.write(conteudo)
    for p in pendencias:
        print("- " + p)
    print("SDD: consolidado em {}. Revise o diff e inclua no PR da feature.".format(", ".join(sorted(novos))))
    return 0


# --------------------------------------------------------------------------- validar

RE_EARS = re.compile(r"^(Quando|Se|Enquanto|Onde|O sistema deve|Sempre que)\b", re.I)
RE_TECNICO = re.compile(r"`[^`]*(?:/|\(|\.(?:cs|ts|tsx|js|py|java|sql|json|ya?ml|dart|go|rs)\b)[^`]*`")
LIMITE_PLANO = 8000  # ~2.000 tokens; o alvo e 900-1600 tokens


def itens(texto, prefixo):
    """[(id, linha)] dos itens `- **PREFIXO-n**`."""
    saida = []
    for linha in (texto or "").splitlines():
        m = RE_ITEM_ID.match(linha)
        if m and m.group(1).split("-")[0] == prefixo:
            saida.append((m.group(1), linha))
    return saida


def validar_spec(texto, problemas, proj=None, num=None):
    rfs = itens(texto, "RF")
    ids = [i for i, _ in rfs]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        problemas.append(("ERRO", "{} aparece mais de uma vez".format(i)))
    cas = itens(texto, "CA")
    if not cas:
        problemas.append(("ERRO", "nenhum criterio de aceite (- **CA-n**)"))
    for ca, linha in cas:
        citados = set(re.findall(r"\bRF-\d+\b", linha))
        if rfs and not citados:
            problemas.append(("ERRO", "{} nao cita nenhum RF".format(ca)))
        for rf in sorted(citados - set(ids)):
            problemas.append(("ERRO", "{} cita {} que nao existe".format(ca, rf)))
        frase = re.split(r"\s[—-]\s", linha, maxsplit=1)
        if len(frase) < 2 or not RE_EARS.match(frase[1].strip()):
            problemas.append(("AVISO", "{} nao comeca em EARS (Quando/Se/Enquanto/Onde/O sistema deve)".format(ca)))
    for rnf, linha in itens(texto, "RNF"):
        if not re.search(r"\d", linha.split("**", 2)[-1]):
            problemas.append(("AVISO", "{} sem numero e unidade".format(rnf)))
    for m in RE_TECNICO.finditer(secao(texto, "Requisitos funcionais") or ""):
        problemas.append(("AVISO", "possivel solucao tecnica nos requisitos: {}".format(m.group(0))))
    abertas = itens(texto, "QA")
    if abertas:
        problemas.append(("AVISO", "{} questao(oes) em aberto: resolva antes de aprovar ou deixe explicito".format(len(abertas))))
    deltas = deltas_da_spec(texto)
    if secao(texto, SECAO_DELTAS) is not None and not deltas:
        problemas.append(("ERRO", "secao \"{}\" sem '### Capacidade:' / '#### ADICIONADO|ALTERADO|REMOVIDO' / "
                          "'##### Requisito:'".format(SECAO_DELTAS)))
    if proj is not None and deltas:
        _, _, erros = aplicar_deltas(proj, num or "?", deltas)
        problemas.extend(("ERRO", e) for e in erros)
    return {i for i, _ in rfs}, {i for i, _ in cas}


def validar_tarefas(texto, problemas, cas_esperados, bug=False):
    tarefas = tarefas_de(texto)
    if not tarefas:
        problemas.append(("ERRO", "nenhuma tarefa (- [ ] T-n — ...)"))
        return
    ids = [t["id"] for t in tarefas]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        problemas.append(("ERRO", "{} aparece mais de uma vez".format(i)))
    cobertos = set()
    for t in tarefas:
        linha = t["linha"]
        if tem_placeholder(linha):
            problemas.append(("ERRO", "{} ainda tem <placeholder> do template; preencha ou apague a linha".format(t["id"])))
        cobertos |= set(re.findall(r"\bCA-\d+\b", linha))
        if not re.search(r"pronto\s*:", linha, re.I):
            problemas.append(("ERRO", "{} sem criterio de pronto ('pronto: ...')".format(t["id"])))
        if not bug:
            if not RE_MODULO_TAREFA.search(linha):
                problemas.append(("ERRO", "{} sem modulo ('modulo <nome>')".format(t["id"])))
            if not re.search(r"origem", linha, re.I):
                problemas.append(("AVISO", "{} sem origem (RF/CA ou unidade do plano)".format(t["id"])))
        for d in t["depende"]:
            if d not in ids:
                problemas.append(("ERRO", "{} depende de {} que nao existe".format(t["id"], d)))
            elif ids.index(d) > ids.index(t["id"]):
                problemas.append(("AVISO", "{} depende de {} que vem depois na lista".format(t["id"], d)))
    if bug or cas_esperados:
        alvo = cas_esperados if cas_esperados else set()
        for ca in sorted(alvo - cobertos, key=lambda x: int(x.split("-")[1])):
            problemas.append(("AVISO", "{} nao aparece em nenhuma tarefa".format(ca)))


RE_ITEM_BRIEF = re.compile(r"^\s*[-*]\s*\*\*((M|O|RP|F|RI|PA)-\d+)\*\*(.*)$", re.M)
MODOS_BRIEF = {
    "brief": [],
    "brainstorm": ["Opções"],
    "prfaq": ["Comunicado", "FAQ"],
    "prd": ["Requisitos de produto", "Features candidatas"],
}
SECOES_BRIEF = ["Problema", "Quem tem o problema", "Por que agora", "Sucesso", "Escopo",
                "Fora de escopo", "Perguntas abertas"]


def validar_brief(texto, problemas):
    """Forma do brief de docs/descoberta/<slug>/brief.md."""
    m = re.search(r"^modo:\s*(\S+)\s*$", texto[:2000], re.M)
    modo = m.group(1) if m else None
    if modo not in MODOS_BRIEF:
        problemas.append(("ERRO", "frontmatter com modo invalido: use brief, brainstorm, prfaq ou prd"))
        modo = "brief"
    for titulo in SECOES_BRIEF + MODOS_BRIEF[modo]:
        corpo = secao(texto, titulo)
        if corpo is None:
            problemas.append(("ERRO", "secao '## {}' ausente".format(titulo)))
        elif not re.sub(r"<!--.*?-->", "", corpo, flags=re.S).strip():
            problemas.append(("AVISO", "secao '## {}' vazia".format(titulo)))
    for outro, secoes in MODOS_BRIEF.items():
        if outro != modo:
            for titulo in secoes:
                if secao(texto, titulo) is not None:
                    problemas.append(("AVISO", "secao '## {}' e do modo {}; remova".format(titulo, outro)))
    itens_b = {}
    for i in RE_ITEM_BRIEF.finditer(texto):
        itens_b.setdefault(i.group(2), []).append((i.group(1), i.group(3)))
    metricas = itens_b.get("M", [])
    if not metricas:
        problemas.append(("ERRO", "sucesso sem metrica (- **M-n** — ...)"))
    for mid, resto in metricas:
        if not re.search(r"\d", re.sub(r"<[^>]*>", "", resto)):
            problemas.append(("AVISO", "{} sem numero; sem numero, vira pergunta aberta".format(mid)))
    if modo == "brainstorm" and len(itens_b.get("O", [])) < 2:
        problemas.append(("ERRO", "modo brainstorm precisa de ao menos duas opcoes (- **O-n**)"))
    if modo == "prd":
        rps = {i for i, _ in itens_b.get("RP", [])}
        if not rps:
            problemas.append(("ERRO", "modo prd sem requisitos de produto (- **RP-n**)"))
        features = itens_b.get("F", [])
        if not features:
            problemas.append(("ERRO", "modo prd sem features candidatas (- **F-n**)"))
        for fid, resto in features:
            for rp in sorted(set(re.findall(r"\bRP-\d+\b", resto)) - rps):
                problemas.append(("ERRO", "{} cita {} que nao existe".format(fid, rp)))
            if "classe" not in resto.lower():
                problemas.append(("AVISO", "{} sem classe sugerida".format(fid)))
    for titulo in ("Problema", "Escopo"):
        for tm in RE_TECNICO.finditer(secao(texto, titulo) or ""):
            problemas.append(("AVISO", "possivel solucao tecnica em '{}': {}".format(titulo, tm.group(0))))
    vazios = len(re.findall(r"<[a-zçãéêó][^<>\n]{2,}>", texto))
    if vazios:
        problemas.append(("AVISO", "{} placeholder(s) <...> nao preenchido(s)".format(vazios)))


def validar_arquivo(proj, rel):
    texto = lf(proj.no_disco(rel))
    if texto is None:
        return [("ERRO", "arquivo nao encontrado")]
    problemas = []
    if status_de(texto) not in ("rascunho", "aprovado"):
        problemas.append(("ERRO", "frontmatter sem 'status: rascunho' ou 'status: aprovado'"))
    art = proj.artefato(rel)
    if not art:
        if re.search(r"^fase:\s*descoberta\s*$", texto[:2000], re.M):
            validar_brief(texto, problemas)
        return problemas
    num, _, tipo = art
    arqs = arquivos_da_feature(proj, num)
    if tipo == "spec":
        validar_spec(texto, problemas, proj, num)
    elif tipo == "bug":
        _, cas = validar_spec(texto, problemas, proj, num)
        validar_tarefas(texto, problemas, cas, bug=True)
    elif tipo in ("plan", "tasks"):
        spec = lf(proj.no_disco(arqs["spec"])) if arqs.get("spec") else ""
        rfs = {i for i, _ in itens(spec, "RF")}
        cas = {i for i, _ in itens(spec, "CA")}
        if tipo == "plan":
            for i in sorted(rfs | cas, key=lambda x: (x[:2], int(x.split("-")[1]))):
                if not re.search(r"\b{}\b".format(re.escape(i)), texto):
                    problemas.append(("ERRO", "{} da spec nao aparece no plano".format(i)))
            tamanho = len(texto.encode("utf-8"))
            if tamanho > LIMITE_PLANO:
                problemas.append(("AVISO", "plano com ~{} tokens; o alvo e 900-1600. Corte o que nao muda "
                                  "a implementacao".format(tamanho // 4)))
            if RE_TAREFA.search(texto):
                validar_tarefas(texto, problemas, cas)
        else:
            validar_tarefas(texto, problemas, cas)
    return problemas


def modo_validar(alvos):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    proj = Projeto(os.getcwd())
    if not proj.ativo:
        print("SDD: projeto sem {} (rode /prepararsdd).".format(CONFIG_REL))
        return 2
    arquivos = []
    for alvo in alvos or [proj.feature_da_branch() or ""]:
        if re.fullmatch(r"\d{1,3}", alvo or ""):
            arquivos += [v for _, v in sorted(arquivos_da_feature(proj, alvo.zfill(3)).items())]
        elif alvo:
            arquivos.append(proj.relativo(os.path.join(proj.raiz, alvo)) or alvo)
    if not arquivos:
        print("SDD: informe a feature ou o arquivo (ex.: validar 004).")
        return 2
    erros = 0
    for rel in arquivos:
        problemas = validar_arquivo(proj, rel)
        erros += sum(1 for n, _ in problemas if n == "ERRO")
        if not problemas:
            print("{}: ok".format(rel))
            continue
        print("{}:".format(rel))
        for nivel, msg in problemas:
            print("- {}: {}".format(nivel, msg))
    return 1 if erros else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="modo", required=True)
    sub.add_parser("hook")
    ci = sub.add_parser("ci")
    ci.add_argument("--base", default=None, help="padrao: origin/<branch_principal>")
    ci.add_argument("--head", "--fonte", dest="head", default="HEAD",
                    help="ultimo commit da branch de origem do PR (o CI faz checkout do merge)")
    sub.add_parser("sincronia")
    sub.add_parser("base")
    st = sub.add_parser("status")
    st.add_argument("--json", action="store_true")
    cx = sub.add_parser("contexto")
    cx.add_argument("feature", nargs="?", default=None, help="NNN; padrao: a da branch")
    cx.add_argument("--json", action="store_true")
    va = sub.add_parser("validar")
    va.add_argument("alvos", nargs="*", help="NNN ou caminhos de artefatos; padrao: a feature da branch")
    co = sub.add_parser("consolidar")
    co.add_argument("feature", nargs="?", default=None)
    co.add_argument("--verificar", action="store_true", help="so confere; sai com 1 se faltar consolidar")
    rv = sub.add_parser("revisao")
    rv.add_argument("--base", default=None,
                    help="sem base: mudancas nao commitadas; 'principal' ou uma ref: tudo desde o merge-base")
    rv.add_argument("--json", action="store_true")
    cb = sub.add_parser("cobertura")
    cb.add_argument("feature", nargs="?", default=None)
    cb.add_argument("--resultados", nargs="*", default=[], help="arquivos TRX ou JUnit XML")
    cb.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.modo == "revisao":
        return modo_revisao(args.base, args.json)
    if args.modo == "cobertura":
        return modo_cobertura(args.feature, args.resultados, args.json)
    if args.modo == "validar":
        return modo_validar(args.alvos)
    if args.modo == "consolidar":
        return modo_consolidar(args.feature, args.verificar)
    if args.modo == "contexto":
        return modo_contexto(args.feature, args.json)
    if args.modo == "hook":
        return modo_hook()
    if args.modo == "ci":
        return modo_ci(args.base, args.head)
    if args.modo == "sincronia":
        return modo_sincronia()
    if args.modo == "base":
        proj = Projeto(os.getcwd())
        base = base_de(proj)
        print(base or principal_de(proj))
        return 0 if base else 2
    return modo_status(args.json)


if __name__ == "__main__":
    sys.exit(main())
