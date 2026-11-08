#!/usr/bin/env python3
"""Tokens de uma sessao do Claude Code, lidos do log da sessao (sem estimativa).

Uso:
    medir_sessao.py [ARQUIVO.jsonl] [--projeto DIR] [--json]
                    [--registrar ARQ --feature NNN --fase NOME]

Sem ARQUIVO, usa a sessao mais recente do projeto (pasta atual ou --projeto), em
<CLAUDE_CONFIG_DIR ou ~/.claude>/projects/<caminho codificado>/*.jsonl.

--registrar acrescenta uma linha JSON ao arquivo indicado (ex.: specs/.metricas/004.jsonl) com
os totais da sessao e o consumo desde o registro anterior da mesma sessao, que e o custo da fase.

Somente biblioteca padrao, Python 3.8+.
"""
import argparse
import collections
import datetime
import glob
import json
import os
import re
import sys

CAMPOS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def pasta_de_sessoes(projeto):
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    codificado = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(projeto))
    return os.path.join(base, "projects", codificado)


def sessao_mais_recente(projeto):
    arquivos = glob.glob(os.path.join(pasta_de_sessoes(projeto), "*.jsonl"))
    return max(arquivos, key=os.path.getmtime) if arquivos else None


def somar(caminho):
    """Totais por campo, chamadas ao modelo e ferramentas. Cada mensagem conta uma vez: o log pode
    repetir o mesmo id durante o streaming, e vale a ultima ocorrencia."""
    por_id = collections.OrderedDict()
    ferramentas = collections.Counter()
    sessao = None
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                ev = json.loads(linha)
            except ValueError:
                continue
            sessao = ev.get("sessionId") or sessao
            msg = ev.get("message") or {}
            if ev.get("type") != "assistant" or not isinstance(msg, dict) or "usage" not in msg:
                continue
            chave = msg.get("id") or ev.get("uuid") or len(por_id)
            por_id[chave] = msg["usage"] or {}
            for c in msg.get("content") or []:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    ferramentas[(chave, c.get("id"), c.get("name"))] += 1
    totais = {k: 0 for k in CAMPOS}
    for uso in por_id.values():
        for k in CAMPOS:
            totais[k] += int(uso.get(k) or 0)
    nomes = collections.Counter(nome for (_, _, nome) in ferramentas)
    return {"sessao": sessao, "arquivo": caminho, "chamadas": len(por_id),
            "ferramentas": dict(nomes.most_common()), **totais}


def ultimo_registro(arquivo, sessao):
    if not os.path.isfile(arquivo):
        return None
    ultimo = None
    with open(arquivo, encoding="utf-8") as f:
        for linha in f:
            try:
                r = json.loads(linha)
            except ValueError:
                continue
            if r.get("sessao") == sessao:
                ultimo = r
    return ultimo


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("arquivo", nargs="?")
    ap.add_argument("--projeto", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--registrar")
    ap.add_argument("--feature")
    ap.add_argument("--fase")
    a = ap.parse_args(argv)
    caminho = a.arquivo or sessao_mais_recente(a.projeto)
    if not caminho or not os.path.isfile(caminho):
        print("Nenhum log de sessao encontrado em {}.".format(pasta_de_sessoes(a.projeto)))
        return 2
    r = somar(caminho)
    total = sum(r[k] for k in CAMPOS)
    if a.registrar:
        anterior = ultimo_registro(a.registrar, r["sessao"])
        delta = {k: r[k] - (anterior or {}).get(k, 0) for k in CAMPOS + ("chamadas",)}
        linha = {"quando": datetime.datetime.now().isoformat(timespec="seconds"), "feature": a.feature,
                 "fase": a.fase, **{k: r[k] for k in ("sessao", "chamadas") + CAMPOS}, "desde_o_anterior": delta}
        os.makedirs(os.path.dirname(os.path.abspath(a.registrar)), exist_ok=True)
        with open(a.registrar, "a", encoding="utf-8") as f:
            f.write(json.dumps(linha, ensure_ascii=False) + "\n")
        r["desde_o_anterior"] = delta
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return 0
    print("Sessao {} ({})".format(r["sessao"], os.path.basename(caminho)))
    print("| Tipo | Tokens |\n| --- | --- |")
    for k, nome in zip(CAMPOS, ("Entrada nova", "Saida", "Gravacao de cache", "Leitura de cache")):
        print("| {} | {:,} |".format(nome, r[k]).replace(",", "."))
    print("| **Total** | {:,} |".format(total).replace(",", "."))
    print("\nChamadas ao modelo: {}. Ferramentas: {}.".format(
        r["chamadas"], ", ".join("{} {}".format(n, q) for n, q in r["ferramentas"].items()) or "nenhuma"))
    if a.registrar:
        d = r["desde_o_anterior"]
        print("Registrado em {}. Desde o registro anterior desta sessao: {:,} tokens em {} chamadas.".format(
            a.registrar, sum(d[k] for k in CAMPOS), d["chamadas"]).replace(",", "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
