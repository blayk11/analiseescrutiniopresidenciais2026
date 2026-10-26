#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Camada histórica: votos para Presidente por município em 2018 e 2022.

Fonte oficial e rastreável: Portal de Dados Abertos do TSE
    https://dadosabertos.tse.jus.br/dataset/resultados-{ano}
    https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona/votacao_partido_munzona_{ano}.zip

Por que o arquivo de partido e não o de candidato: o de candidato tem 395 MB (2018)
e 643 MB (2022); o de partido tem 28 MB e 26 MB e basta para comparar os dois polos,
porque o voto nominal é atribuído ao partido do candidato.

Polo A = PT (13). Polo B = PSL (17) em 2018, PL (22) em 2022 -- os partidos de
Bolsonaro nas duas eleições. Nos dois casos o 2º turno foi PT x esse partido.

Saídas:
    dados/historico.db          tabela historico
    saidas/historico_municipios.csv

Uso:
    python historico.py
"""

from __future__ import annotations

import csv
import io
import sqlite3
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ / "cache" / "historico"
DB_HIST = RAIZ / "dados" / "historico.db"
CSV_HIST = RAIZ / "saidas" / "historico_municipios.csv"

BASE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona"
ANOS = {2018: "PSL", 2022: "PL"}
PT = "PT"
CARGO = "Presidente"

COLUNAS = ["ano", "turno", "uf", "cd_municipio", "municipio",
           "votos_pt", "votos_polo_b", "votos_validos"]


def baixar(ano: int) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    destino = CACHE / f"partido_munzona_{ano}.zip"
    if not destino.exists():
        url = f"{BASE_URL}/votacao_partido_munzona_{ano}.zip"
        print(f"  baixando {url} ...")
        urllib.request.urlretrieve(url, destino)
    return destino


def processar(ano: int) -> dict[tuple, list]:
    polo_b = ANOS[ano]
    caminho = baixar(ano)
    z = zipfile.ZipFile(caminho)

    # O ZIP traz 29 CSV: 27 UFs (só cargos estaduais, sem Presidente), "_BR.csv"
    # (todo o país, inclui Presidente e o exterior) e "_BRASIL.csv" (cópia idêntica
    # do _BR). Ler os dois duplicaria todos os votos, então só o _BR é lido.
    membros = [n for n in z.namelist() if n.lower().endswith("_br.csv")]
    if len(membros) != 1:
        raise RuntimeError(f"{caminho.name}: esperava 1 arquivo _BR.csv, achei {membros}")

    agregado: dict[tuple, list] = {}
    linhas_lidas = 0
    for membro in membros:
        with z.open(membro) as fh:
            leitor = csv.reader(io.TextIOWrapper(fh, encoding="latin-1", newline=""), delimiter=";")
            cabecalho = next(leitor)
            ix = {c: i for i, c in enumerate(cabecalho)}
            i_cargo = ix["DS_CARGO"]
            i_turno = ix["NR_TURNO"]
            i_uf = ix["SG_UF"]
            i_cd = ix["CD_MUNICIPIO"]
            i_nome = ix["NM_MUNICIPIO"]
            i_partido = ix["SG_PARTIDO"]
            i_votos = ix["QT_VOTOS_NOMINAIS_VALIDOS"]

            for linha in leitor:
                linhas_lidas += 1
                if linha[i_cargo] != CARGO:
                    continue
                turno = linha[i_turno]
                if turno not in ("1", "2"):
                    continue
                # 2018 grava "01007" e 2022 grava "1007": normaliza para 5 dígitos
                chave = (ano, int(turno), linha[i_uf].lower(), str(linha[i_cd]).strip().zfill(5))
                registro = agregado.get(chave)
                if registro is None:
                    registro = [linha[i_nome], 0, 0, 0]
                    agregado[chave] = registro
                votos = int(linha[i_votos] or 0)
                registro[3] += votos
                sg = linha[i_partido]
                if sg == PT:
                    registro[1] += votos
                elif sg == polo_b:
                    registro[2] += votos

        print(f"  {membro}: {len(agregado)} municípios/turnos acumulados")

    print(f"  {ano}: {linhas_lidas:,} linhas lidas")
    return agregado


def main() -> int:
    linhas = []
    for ano in ANOS:
        print(f"\n[{ano}] presidente por município (fonte: dados abertos TSE)")
        for (a, turno, uf, cd), (nome, pt, pb, validos) in sorted(processar(ano).items()):
            linhas.append({
                "ano": a, "turno": turno, "uf": uf, "cd_municipio": cd,
                "municipio": nome, "votos_pt": pt, "votos_polo_b": pb,
                "votos_validos": validos,
            })

    if not linhas:
        raise SystemExit("Nada extraído — verifique os ZIPs em cache/historico/")

    RAIZ.joinpath("dados").mkdir(exist_ok=True)
    if DB_HIST.exists():
        DB_HIST.unlink()
    con = sqlite3.connect(DB_HIST)
    con.execute("""
        CREATE TABLE historico (
            ano INTEGER, turno INTEGER, uf TEXT, cd_municipio TEXT, municipio TEXT,
            votos_pt INTEGER, votos_polo_b INTEGER, votos_validos INTEGER,
            PRIMARY KEY (ano, turno, uf, cd_municipio)
        )
    """)
    con.executemany(
        f"INSERT INTO historico ({', '.join(COLUNAS)}) VALUES ({', '.join('?' * len(COLUNAS))})",
        [[l[c] for c in COLUNAS] for l in linhas],
    )
    con.commit()

    CSV_HIST.parent.mkdir(exist_ok=True)
    with CSV_HIST.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUNAS)
        w.writeheader()
        w.writerows(linhas)

    print()
    for ano in ANOS:
        total_pt = con.execute("SELECT SUM(votos_pt) FROM historico WHERE ano = ? AND turno = 1",
                               (ano,)).fetchone()[0]
        total_b = con.execute("SELECT SUM(votos_polo_b) FROM historico WHERE ano = ? AND turno = 1",
                              (ano,)).fetchone()[0]
        print(f"{ano} 1º turno: PT {total_pt:>12,} | {ANOS[ano]} {total_b:>12,}")
    con.close()
    print(f"\nOK: {DB_HIST}")
    print(f"OK: {CSV_HIST}  ({len(linhas)} linhas)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
