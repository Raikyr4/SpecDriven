#!/usr/bin/env python3
"""Evals dos comandos do plugin sdd: roda cada caso num projeto descartável e confere o resultado.

Uso:
    python evals/rodar_evals.py [--caso ID ...] [--simular] [--repeticoes N] [--claude-args "..."]

Para cada caso: copia evals/fixture (e os extras do caso) para uma pasta temporária, cria um
repositório git com um `origin` local, roda `claude -p "<prompt>" --output-format json
--plugin-dir plugins/sdd`, e aplica as verificações de evals/casos.json. Grava o resultado em
evals/resultados/<data>.json (tokens por tipo, custo informado pelo CLI, tempo, verificações).

--simular não chama o Claude: só prepara o projeto e roda as verificações (útil para testar o
próprio runner). As permissões do Claude vêm de --claude-args (padrão: bypassPermissions, porque a
pasta é descartável; o hook do gate continua valendo).
"""
import argparse
import datetime
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PLUGIN = os.path.join(RAIZ, "plugins", "sdd")
GATE = os.path.join(PLUGIN, "hooks", "sdd_gate.py")
ARGS_PADRAO = "--permission-mode bypassPermissions"


def git(pasta, *args):
    return subprocess.run(("git",) + args, cwd=pasta, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def preparar(caso):
    base = tempfile.mkdtemp(prefix="sdd-eval-")
    projeto = os.path.join(base, "projeto")
    shutil.copytree(os.path.join(AQUI, "fixture"), projeto)
    if caso.get("extras"):
        shutil.copytree(os.path.join(AQUI, caso["extras"]), projeto, dirs_exist_ok=True)
    origem = os.path.join(base, "origin.git")
    git(base, "init", "-q", "--bare", "-b", "main", origem)
    for args in (("init", "-q", "-b", "main"), ("config", "user.email", "eval@example.com"),
                 ("config", "user.name", "Eval"), ("add", "-A"), ("commit", "-q", "-m", "inicio"),
                 ("remote", "add", "origin", origem), ("push", "-q", "-u", "origin", "main")):
        git(projeto, *args)
    if caso.get("branch"):
        git(projeto, "switch", "-q", "-c", caso["branch"])
    return base, projeto


def rodar_claude(projeto, prompt, extra):
    cmd = ["claude", "-p", prompt, "--output-format", "json", "--plugin-dir", PLUGIN] + shlex.split(extra)
    inicio = time.time()
    try:
        p = subprocess.run(cmd, cwd=projeto, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=1800)
    except FileNotFoundError:
        return {"erro": "comando 'claude' não encontrado no PATH"}, 0.0
    except subprocess.TimeoutExpired:
        return {"erro": "tempo esgotado (30 min)"}, time.time() - inicio
    try:
        saida = json.loads(p.stdout)
    except ValueError:
        saida = {"erro": "saída não é JSON", "stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:]}
    return saida, time.time() - inicio


def arquivos(projeto, padrao):
    return sorted(glob.glob(os.path.join(projeto, padrao)))


def ler(caminho):
    with open(caminho, encoding="utf-8", errors="replace") as f:
        return f.read()


def checar(projeto, v, commit_inicial):
    """(ok, detalhe) de uma verificação."""
    tipo = v["tipo"]
    if tipo == "arquivo_existe":
        achados = arquivos(projeto, v["glob"])
        return bool(achados), ", ".join(os.path.relpath(a, projeto) for a in achados) or "nenhum"
    if tipo in ("contem", "nao_contem"):
        achados = arquivos(projeto, v["glob"])
        if not achados:
            return tipo == "nao_contem", "nenhum arquivo"
        tem = any(v["texto"] in ler(a) for a in achados)
        return (tem if tipo == "contem" else not tem), "texto {}encontrado".format("" if tem else "não ")
    if tipo == "validar_ok":
        alvos = [os.path.relpath(a, projeto) for a in arquivos(projeto, v["alvo"])] or [v["alvo"]]
        p = subprocess.run([sys.executable, GATE, "validar"] + alvos, cwd=projeto,
                           capture_output=True, text=True, encoding="utf-8")
        return p.returncode == 0, p.stdout.strip()[-400:]
    if tipo == "cobertura_ok":
        p = subprocess.run([sys.executable, GATE, "cobertura", v["feature"]], cwd=projeto,
                           capture_output=True, text=True, encoding="utf-8")
        return p.returncode == 0, p.stdout.strip()[-400:]
    if tipo == "comando_ok":
        p = subprocess.run(v["comando"], cwd=projeto, capture_output=True, text=True, encoding="utf-8")
        return p.returncode == 0, (p.stdout + p.stderr).strip()[-300:]
    if tipo == "branch_casa":
        b = git(projeto, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        return re.search(v["regex"], b) is not None, b
    if tipo == "sem_commits_novos":
        atual = git(projeto, "rev-parse", "HEAD").stdout.strip()
        return atual == commit_inicial, "HEAD {}".format(atual[:8])
    if tipo == "sem_codigo_alterado":
        mudados = [l for l in git(projeto, "status", "--porcelain", "--", "app").stdout.splitlines() if l]
        return not mudados, "; ".join(mudados) or "nada alterado em app/"
    return False, "tipo de verificação desconhecido: " + tipo


def uso(saida):
    u = saida.get("usage") or {}
    return {k: int(u.get(k) or 0) for k in ("input_tokens", "output_tokens",
                                            "cache_creation_input_tokens", "cache_read_input_tokens")}


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--caso", nargs="*")
    ap.add_argument("--simular", action="store_true")
    ap.add_argument("--repeticoes", type=int, default=1)
    ap.add_argument("--claude-args", default=ARGS_PADRAO)
    ap.add_argument("--manter", action="store_true", help="não apaga as pastas temporárias")
    ap.add_argument("--sem-gravar", action="store_true")
    a = ap.parse_args(argv)
    with open(os.path.join(AQUI, "casos.json"), encoding="utf-8") as f:
        dados = json.load(f)
    casos = [c for c in dados["casos"] if not a.caso or c["id"] in a.caso]
    resultados, falhas = [], 0
    for caso in casos:
        for rep in range(1, a.repeticoes + 1):
            base, projeto = preparar(caso)
            commit = git(projeto, "rev-parse", "HEAD").stdout.strip()
            saida, segundos = ({"simulado": True}, 0.0) if a.simular else rodar_claude(
                projeto, caso["prompt"] + "\n\n" + dados["instrucao_sem_humano"], a.claude_args)
            checagens = []
            for v in caso["verificacoes"]:
                ok, detalhe = checar(projeto, v, commit)
                checagens.append({"tipo": v["tipo"], "ok": ok, "detalhe": detalhe})
            tokens = uso(saida)
            total = sum(tokens.values())
            dentro = a.simular or total <= caso.get("limite_tokens", total)
            r = {"caso": caso["id"], "repeticao": rep, "ok": all(c["ok"] for c in checagens) and dentro and "erro" not in saida,
                 "tokens": tokens, "total_tokens": total, "custo_usd": saida.get("total_cost_usd"),
                 "segundos": round(segundos, 1), "turnos": saida.get("num_turns"), "erro": saida.get("erro"),
                 "verificacoes": checagens}
            resultados.append(r)
            falhas += 0 if r["ok"] else 1
            if a.manter:
                r["pasta"] = projeto
            else:
                shutil.rmtree(base, ignore_errors=True)
    print("| Caso | Rep | OK | Verificações | Tokens | Custo USD | Tempo (s) |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for r in resultados:
        n_ok = sum(c["ok"] for c in r["verificacoes"])
        print("| {} | {} | {} | {}/{} | {} | {} | {} |".format(
            r["caso"], r["repeticao"], "sim" if r["ok"] else "NÃO", n_ok, len(r["verificacoes"]),
            r["total_tokens"], r["custo_usd"] if r["custo_usd"] is not None else "-", r["segundos"]))
        for c in r["verificacoes"]:
            if not c["ok"]:
                print("  - falhou {}: {}".format(c["tipo"], c["detalhe"].splitlines()[-1] if c["detalhe"] else ""))
        if r["erro"]:
            print("  - erro: {}".format(r["erro"]))
    if not a.sem_gravar:
        pasta = os.path.join(AQUI, "resultados")
        os.makedirs(pasta, exist_ok=True)
        nome = os.path.join(pasta, datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + (
            "-simulado" if a.simular else "") + ".json")
        with open(nome, "w", encoding="utf-8") as f:
            json.dump({"simulado": a.simular, "claude_args": a.claude_args, "resultados": resultados},
                      f, ensure_ascii=False, indent=2)
        print("\nResultado gravado em " + os.path.relpath(nome, RAIZ))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
