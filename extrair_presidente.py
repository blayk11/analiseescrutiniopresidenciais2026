#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extrai a votacao nominal para Presidente (1o e 2o turno, Eleicoes 2026)
dos JSON publicos de resultados.tse.jus.br, por municipio, e grava CSV + SQLite.

Uso:
    python extrair_presidente.py                 # Brasil inteiro, 2 turnos
    python extrair_presidente.py --ufs ac,sp     # so alguns estados
    python extrair_presidente.py --turnos 2      # so 2o turno
    python extrair_presidente.py --force         # rebaixa ignorando o cache

Os arquivos baixados ficam em cache/ -- rodar de novo sem --force nao
rebaixa nada, so reconstroi o CSV/SQLite a partir do cache.
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE = "https://resultados.tse.jus.br/oficial/ele2026"

# turno -> codigo da eleicao (vem do catalogo oficial/comum/config/ele-c.json)
ELEICOES = {1: 6257, 2: 6258}
CARGO_CD = 1
CARGO_NOME = "Presidente"

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ / "cache"
DADOS = RAIZ / "dados"
CSV_OUT = DADOS / "votos_presidente_2026.csv"
DB_OUT = DADOS / "votos_presidente_2026.db"
FALHAS = DADOS / "falhas.txt"

COLUNAS = [
    "turno", "uf", "cd_municipio", "cd_ibge", "municipio",
    "cargo", "cd_cargo", "nr_candidato", "sq_candidato",
    "nome_candidato", "nome_urna", "partido", "coligacao",
    "votos", "pct_municipio", "status", "eleito",
    "secoes_total", "secoes_apuradas", "pct_secoes",
    "eleitorado", "eleitorado_apurado",
    "votos_total", "votos_validos", "votos_brancos", "votos_nulos",
    "apuracao_encerrada", "gerado_em",
]

_print_lock = threading.Lock()


def num(valor):
    """'1.234' / '' / None -> int. O TSE manda numeros como string."""
    if valor in (None, ""):
        return None
    return int(str(valor))


def dec(valor):
    """'47,03' -> 47.03. String com virgula: Number() viraria NaN em silencio."""
    if valor in (None, ""):
        return None
    return float(str(valor).replace(".", "").replace(",", "."))


def url_municipio(eleicao: int, uf: str, cd_municipio: str) -> str:
    return (
        f"{BASE}/{eleicao}/dados/{uf}/"
        f"{uf}{cd_municipio}-c{CARGO_CD:04d}-e{eleicao:06d}-u.json"
    )


def baixar(url: str, destino: Path, force=False, tentativas=3) -> bytes | None:
    if destino.exists() and not force:
        return destino.read_bytes()

    erro = None
    for n in range(tentativas):
        try:
            req = urllib.request.Request(
                f"{url}?nocache={int(time.time() * 1000)}",
                headers={"User-Agent": "extrator-resultados-tse/1.0"},
            )
            with urllib.request.urlopen(req, timeout=45) as resp:
                corpo = resp.read()
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_bytes(corpo)
            return corpo
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None  # arquivo nao publicado para esse municipio
            erro = f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001 - rede: registra e tenta de novo
            erro = repr(exc)
        time.sleep(1.5 * (n + 1))
    raise RuntimeError(f"{erro} em {url}")


def parse_arquivo(bruto: bytes, turno: int, uf: str, uf_nome: str, mu: dict) -> list[dict]:
    d = json.loads(bruto.decode("utf-8"))

    s = d.get("s") or {}
    e = d.get("e") or {}
    v = d.get("v") or {}
    gerado = f"{d.get('dg', '')} {d.get('hg', '')}".strip()

    comuns = {
        "turno": turno,
        "uf": uf,
        "cd_municipio": mu["cd"],
        "cd_ibge": mu.get("cdi"),
        "municipio": mu["nm"],
        "cargo": CARGO_NOME,
        "cd_cargo": CARGO_CD,
        "secoes_total": num(s.get("ts")),
        "secoes_apuradas": num(s.get("st")),
        "pct_secoes": dec(s.get("pst")),
        "eleitorado": num(e.get("te")),
        "eleitorado_apurado": num(e.get("est")),
        "votos_total": num(v.get("tv")),
        "votos_validos": num(v.get("vv")),
        "votos_brancos": num(v.get("vb")),
        "votos_nulos": num(v.get("tvn")),
        "apuracao_encerrada": "S" if d.get("and") == "f" else "N",
        "gerado_em": gerado,
    }

    linhas = []
    for cargo in d.get("carg", []):
        for agr in cargo.get("agr", []):
            coligacao = agr.get("nm") if agr.get("tp") == "c" else ""
            for par in agr.get("par", []):
                for cand in par.get("cand", []):
                    st = (cand.get("st") or "").strip()
                    linha = dict(comuns)
                    linha.update(
                        {
                            "nr_candidato": cand.get("n"),
                            "sq_candidato": cand.get("sqcand"),
                            "nome_candidato": cand.get("nm"),
                            "nome_urna": cand.get("nmu") or cand.get("nm"),
                            "partido": par.get("sg"),
                            "coligacao": coligacao,
                            "votos": num(cand.get("vap")),
                            "pct_municipio": dec(cand.get("pvap")),
                            "status": st,
                            # "e" nao significa eleito: 's' = nao eliminado.
                            "eleito": "S" if st.startswith("Eleito") else "N",
                        }
                    )
                    linhas.append(linha)
    return linhas


def carregar_municipios(force=False) -> list[dict]:
    eleicao = ELEICOES[1]
    url = f"{BASE}/{eleicao}/config/mun-e{eleicao:06d}-cm.json"
    cfg = json.loads(baixar(url, CACHE / "config" / "municipios.json", force=force))

    itens = []
    for abr in cfg.get("abr", []):
        uf = abr["cd"]
        for mu in abr.get("mu", []):
            itens.append({"uf": uf, "uf_nome": abr.get("ds", uf.upper()), **mu})
    return itens


def main() -> int:
    ap = argparse.ArgumentParser(description="Extrai votos por municipio (Presidente 2026).")
    ap.add_argument("--ufs", help="lista de UFs separada por virgula (ex.: ac,sp). Padrao: todas.")
    ap.add_argument("--turnos", default="1,2", help="turnos separados por virgula (padrao: 1,2)")
    ap.add_argument("--workers", type=int, default=8, help="requisicoes simultaneas (padrao: 8)")
    ap.add_argument("--force", action="store_true", help="ignora o cache local e rebaixa")
    args = ap.parse_args()

    turnos = [int(t) for t in args.turnos.split(",") if t.strip()]
    for t in turnos:
        if t not in ELEICOES:
            ap.error(f"turno invalido: {t} (use 1 ou 2)")

    DADOS.mkdir(parents=True, exist_ok=True)

    print("Lendo lista de municipios...")
    municipios = carregar_municipios(force=args.force)
    if args.ufs:
        alvo = {u.strip().lower() for u in args.ufs.split(",") if u.strip()}
        municipios = [m for m in municipios if m["uf"] in alvo]
        if not municipios:
            ap.error(f"nenhum municipio para as UFs: {sorted(alvo)}")
    print(f"{len(municipios)} municipios em {len({m['uf'] for m in municipios})} UF(s)")

    tarefas = []
    for turno in turnos:
        eleicao = ELEICOES[turno]
        for mu in municipios:
            url = url_municipio(eleicao, mu["uf"], mu["cd"])
            destino = CACHE / str(turno) / mu["uf"] / f"{mu['uf']}{mu['cd']}.json"
            tarefas.append((turno, eleicao, mu, url, destino))

    print(f"Baixando/validando {len(tarefas)} arquivos (workers={args.workers})...")
    inicio = time.time()
    linhas: list[dict] = []
    falhas: list[str] = []
    concluidos = 0

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futuros = {
            pool.submit(baixar, url, destino, args.force): (turno, mu)
            for turno, _ele, mu, url, destino in tarefas
        }
        for fut in as_completed(futuros):
            turno, mu = futuros[fut]
            concluidos += 1
            try:
                bruto = fut.result()
            except Exception as exc:  # noqa: BLE001
                falhas.append(f"turno {turno} {mu['uf']} {mu['cd']} {mu['nm']}: {exc}")
                continue
            if bruto is None:
                falhas.append(
                    f"turno {turno} {mu['uf']} {mu['cd']} {mu['nm']}: 404 (arquivo nao publicado)"
                )
                continue
            try:
                linhas.extend(parse_arquivo(bruto, turno, mu["uf"], mu["uf_nome"], mu))
            except Exception as exc:  # noqa: BLE001
                falhas.append(f"turno {turno} {mu['uf']} {mu['cd']} {mu['nm']}: parse {exc!r}")

            if concluidos % 500 == 0 or concluidos == len(tarefas):
                with _print_lock:
                    print(f"  {concluidos}/{len(tarefas)} arquivos ({time.time() - inicio:.0f}s)")

    if not linhas:
        print("Nenhuma linha extraida.", file=sys.stderr)
        return 1

    linhas.sort(key=lambda r: (r["turno"], r["uf"], r["cd_municipio"], -(r["votos"] or 0)))

    print(f"Escrevendo CSV ({len(linhas)} linhas)...")
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)

    print("Escrevendo SQLite...")
    if DB_OUT.exists():
        DB_OUT.unlink()
    con = sqlite3.connect(DB_OUT)
    con.execute("""
        CREATE TABLE votos (
            turno INTEGER NOT NULL,
            uf TEXT NOT NULL,
            cd_municipio TEXT NOT NULL,
            cd_ibge TEXT,
            municipio TEXT NOT NULL,
            cargo TEXT NOT NULL,
            cd_cargo INTEGER NOT NULL,
            nr_candidato TEXT,
            sq_candidato TEXT,
            nome_candidato TEXT,
            nome_urna TEXT,
            partido TEXT,
            coligacao TEXT,
            votos INTEGER,
            pct_municipio REAL,
            status TEXT,
            eleito TEXT,
            secoes_total INTEGER,
            secoes_apuradas INTEGER,
            pct_secoes REAL,
            eleitorado INTEGER,
            eleitorado_apurado INTEGER,
            votos_total INTEGER,
            votos_validos INTEGER,
            votos_brancos INTEGER,
            votos_nulos INTEGER,
            apuracao_encerrada TEXT,
            gerado_em TEXT
        )
    """)
    con.executemany(
        f"INSERT INTO votos ({', '.join(COLUNAS)}) VALUES ({', '.join('?' * len(COLUNAS))})",
        [[r[c] for c in COLUNAS] for r in linhas],
    )
    con.execute("CREATE INDEX ix_votos_turno_uf ON votos (turno, uf)")
    con.execute("CREATE INDEX ix_votos_cand ON votos (turno, nome_candidato)")
    con.execute("CREATE INDEX ix_votos_mun ON votos (uf, municipio)")
    con.commit()
    con.close()

    if falhas:
        FALHAS.write_text("\n".join(falhas), encoding="utf-8")

    print()
    print(f"OK: {CSV_OUT}")
    print(f"OK: {DB_OUT}")
    if falhas:
        print(f"{len(falhas)} falha(s) registrada(s) em {FALHAS}")
    print(f"Tempo total: {time.time() - inicio:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
