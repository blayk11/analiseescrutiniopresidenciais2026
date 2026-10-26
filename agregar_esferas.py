#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Monta a base hierarquica (roll-up) da votacao presidencial de 2026:

    PAIS (1) -> MACRORREGIAO (5) -> ESTADO (27) -> REGIAO_INTERMEDIARIA (133) -> MUNICIPIO (5.571)
    mais uma linha EXTERIOR (todo o voto no exterior agregado).

Cada linha traz os mesmos campos, com os absolutos somados da esfera filha e os
percentuais recalculados sobre os denominadores corretos daquele nivel.

Saidas:
    saidas/base_hierarquica.csv
    dados/base_hierarquica.db   (tabela esferas)
    visualizacao/dados.js       (payload do drill-down)

Uso:
    python agregar_esferas.py
"""

from __future__ import annotations

import csv
import gzip
import json
import sqlite3
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DB_VOTOS = RAIZ / "dados" / "votos_presidente_2026.db"
DB_HIER = RAIZ / "dados" / "base_hierarquica.db"
CSV_HIER = RAIZ / "saidas" / "base_hierarquica.csv"
JS_HIER = RAIZ / "visualizacao" / "dados.js"
CACHE_IBGE = RAIZ / "cache" / "ibge_municipios.json"

IBGE = "https://servicodados.ibge.gov.br/api/v1/localidades"
# códigos IBGE das 27 UFs (não existe 34 nem 36..39)
UF_IDS = [11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29,
          31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53]

LULA = "LULA"
FLAVIO = "FLAVIO BOLSONARO"
TERCEIROS = ["ESCRITOR AUGUSTO CURY", "RENAN SANTOS", "RONALDO CAIADO"]

CAMPOS_ABS = [
    "eleitores_aptos_1t", "comparecimento_1t", "brancos_1t", "nulos_1t", "validos_1t",
    "lula_1t", "flavio_1t", "outros_1t", "cury_1t", "renan_1t", "caiado_1t",
    "eleitores_aptos_2t", "comparecimento_2t", "brancos_2t", "nulos_2t", "validos_2t",
    "lula_2t", "flavio_2t",
]

COLUNAS = [
    "esfera", "cod_ibge", "nome_localidade", "uf", "macrorregiao",
    "regiao_intermediaria", "cod_regiao_intermediaria",
] + CAMPOS_ABS + [
    "pct_comparecimento_1t", "pct_abstencao_1t", "pct_comparecimento_2t", "pct_abstencao_2t",
    "pct_brancos_1t", "pct_nulos_1t", "pct_brancos_2t", "pct_nulos_2t",
    "pct_lula_1t", "pct_flavio_1t", "pct_outros_1t", "pct_cury_1t", "pct_renan_1t", "pct_caiado_1t",
    "pct_lula_2t", "pct_flavio_2t",
    "pct_no_estado", "pct_no_brasil",
    "vencedor_1t", "vencedor_2t", "houve_virada", "saldo_virada",
]


def baixar_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "analise-tse/1.0"})
    raw = urllib.request.urlopen(req, timeout=120).read()
    if raw[:2] == b"\x1f\x8b":  # a API do IBGE força gzip
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def mapa_ibge() -> dict[str, dict]:
    """cod_ibge (7 dígitos) -> UF, macrorregião e região intermediária."""
    if CACHE_IBGE.exists():
        return json.loads(CACHE_IBGE.read_text(encoding="utf-8"))

    print("Baixando malha do IBGE (27 UFs)...")
    mapa: dict[str, dict] = {}
    for uf_id in UF_IDS:
        for mu in baixar_json(f"{IBGE}/estados/{uf_id}/municipios"):
            ri = (mu.get("regiao-imediata") or {}).get("regiao-intermediaria") or {}
            uf = (ri.get("UF") or {})
            mapa[str(mu["id"])] = {
                "uf": uf.get("sigla", ""),
                "macrorregiao": (uf.get("regiao") or {}).get("nome", ""),
                "ri": ri.get("nome", ""),
                "ri_id": ri.get("id"),
            }
        print(f"  UF {uf_id}: {len(mapa)} municípios acumulados")

    CACHE_IBGE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_IBGE.write_text(json.dumps(mapa, ensure_ascii=False), encoding="utf-8")
    return mapa


def votos_por_municipio() -> dict[tuple[str, str], dict]:
    con = sqlite3.connect(DB_VOTOS)
    sql = f"""
        SELECT uf, cd_municipio, MAX(cd_ibge), MAX(municipio), turno,
               MAX(eleitorado), MAX(votos_total), MAX(votos_brancos), MAX(votos_nulos),
               SUM(CASE WHEN nome_urna = ? THEN votos ELSE 0 END),
               SUM(CASE WHEN nome_urna = ? THEN votos ELSE 0 END),
               {" ".join(f"SUM(CASE WHEN nome_urna = '{t}' THEN votos ELSE 0 END)," for t in TERCEIROS)}
               SUM(votos)
        FROM votos
        GROUP BY uf, cd_municipio, turno
    """
    base: dict[tuple[str, str], dict] = {}
    for linha in con.execute(sql, (LULA, FLAVIO)):
        uf, cd, cd_ibge, nome, turno = linha[0], linha[1], linha[2], linha[3], linha[4]
        aptos, comp, brancos, nulos, lula, flavio, cury, renan, caiado, total = linha[5:]
        reg = base.setdefault((uf, cd), {
            "uf": uf, "cd": cd, "cd_ibge": cd_ibge, "municipio": nome,
        })
        t = turno
        reg[f"eleitores_aptos_{t}t"] = aptos
        reg[f"comparecimento_{t}t"] = comp
        reg[f"brancos_{t}t"] = brancos
        reg[f"nulos_{t}t"] = nulos
        reg[f"validos_{t}t"] = total
        reg[f"lula_{t}t"] = lula
        reg[f"flavio_{t}t"] = flavio
        reg[f"cury_{t}t"] = cury
        reg[f"renan_{t}t"] = renan
        reg[f"caiado_{t}t"] = caiado
        reg[f"outros_{t}t"] = total - lula - flavio
    con.close()
    return base


def agregar(itens: list[dict], esfera: str, **ident) -> dict:
    """Soma os campos absolutos de um conjunto de linhas."""
    soma = {c: 0 for c in CAMPOS_ABS}
    for it in itens:
        for c in CAMPOS_ABS:
            soma[c] += it[c]
    return {"esfera": esfera, **ident, **soma}


PREPOSICOES = {"de", "da", "do", "das", "dos", "e", "d'"}


def titulo(nome: str) -> str:
    partes = nome.lower().split()
    saida = [p if (p in PREPOSICOES and i > 0) else p[:1].upper() + p[1:]
             for i, p in enumerate(partes)]
    return " ".join(saida).replace("Flavio", "Flávio")


def nome_vencedor(lula: int, flavio: int) -> str:
    if lula > flavio:
        return "LULA"
    if flavio > lula:
        return "FLÁVIO BOLSONARO"
    return "EMPATE"


def finalizar(linhas: list[dict]) -> None:
    """Calcula percentuais, peso relativo e flag de virada em cada linha."""
    br = next(l for l in linhas if l["esfera"] == "PAIS")
    uf_peso = {l["uf"]: l["validos_2t"] for l in linhas if l["esfera"] == "ESTADO"}

    for l in linhas:
        for t in (1, 2):
            aptos = l[f"eleitores_aptos_{t}t"] or 0
            comp = l[f"comparecimento_{t}t"] or 0
            validos = l[f"validos_{t}t"] or 0
            l[f"pct_comparecimento_{t}t"] = comp / aptos * 100 if aptos else None
            l[f"pct_abstencao_{t}t"] = (aptos - comp) / aptos * 100 if aptos else None
            l[f"pct_brancos_{t}t"] = l[f"brancos_{t}t"] / comp * 100 if comp else None
            l[f"pct_nulos_{t}t"] = l[f"nulos_{t}t"] / comp * 100 if comp else None
            for cand in ("lula", "flavio", "outros", "cury", "renan", "caiado"):
                v = l.get(f"{cand}_{t}t")
                l[f"pct_{cand}_{t}t"] = v / validos * 100 if (v is not None and validos) else None

        l["vencedor_1t"] = nome_vencedor(l["lula_1t"], l["flavio_1t"])
        l["vencedor_2t"] = nome_vencedor(l["lula_2t"], l["flavio_2t"])
        decidido = "EMPATE" not in (l["vencedor_1t"], l["vencedor_2t"])
        l["houve_virada"] = "SIM" if (decidido and l["vencedor_1t"] != l["vencedor_2t"]) else "NÃO"
        l["saldo_virada"] = abs(l["lula_2t"] - l["flavio_2t"])

        l["pct_no_brasil"] = l["validos_2t"] / br["validos_2t"] * 100 if br["validos_2t"] else None
        if l["esfera"] in ("MUNICIPIO", "REGIAO_INTERMEDIARIA", "EXTERIOR"):
            base_uf = uf_peso.get(l["uf"])
            l["pct_no_estado"] = l["validos_2t"] / base_uf * 100 if base_uf else None
        else:
            l["pct_no_estado"] = None


def main() -> int:
    if not DB_VOTOS.exists():
        raise SystemExit(f"Banco não encontrado: {DB_VOTOS}\nRode antes: python extrair_presidente.py")

    ibge = mapa_ibge()
    base = votos_por_municipio()
    print(f"Municípios no TSE: {len(base)}")

    municipios, exterior = [], []
    sem_malha = []
    for (uf, cd), v in base.items():
        if uf == "zz":
            exterior.append(v)
            continue
        info = ibge.get(str(v["cd_ibge"]))
        if not info:
            sem_malha.append((uf, cd, v["municipio"], v["cd_ibge"]))
            continue
        municipios.append({
            "esfera": "MUNICIPIO",
            "cod_ibge": str(v["cd_ibge"]),
            "nome_localidade": titulo(v["municipio"]),
            "uf": info["uf"] or uf.upper(),
            "macrorregiao": info["macrorregiao"],
            "regiao_intermediaria": info["ri"],
            "cod_regiao_intermediaria": str(info["ri_id"]) if info["ri_id"] else "",
            **{c: v.get(c, 0) for c in CAMPOS_ABS},
        })

    if sem_malha:
        print(f"AVISO: {len(sem_malha)} municípios sem correspondência no IBGE (ex.: {sem_malha[0]})")

    # ---- regiões intermediárias
    por_ri: dict[tuple, list] = {}
    for m in municipios:
        por_ri.setdefault((m["macrorregiao"], m["uf"], m["regiao_intermediaria"],
                           m["cod_regiao_intermediaria"]), []).append(m)
    ris = [
        agregar(v, "REGIAO_INTERMEDIARIA",
                nome_localidade=k[2], macrorregiao=k[0], uf=k[1],
                regiao_intermediaria=k[2], cod_regiao_intermediaria=k[3], cod_ibge=k[3])
        for k, v in por_ri.items()
    ]

    # ---- UFs
    por_uf: dict[str, list] = {}
    for m in municipios:
        por_uf.setdefault(m["uf"], []).append(m)
    ufs = [
        agregar(v, "ESTADO", nome_localidade=uf, uf=uf,
                macrorregiao=v[0]["macrorregiao"], regiao_intermediaria="",
                cod_regiao_intermediaria="", cod_ibge="")
        for uf, v in por_uf.items()
    ]

    # ---- macrorregiões
    por_macro: dict[str, list] = {}
    for m in municipios:
        por_macro.setdefault(m["macrorregiao"], []).append(m)
    macros = [
        agregar(v, "MACRORREGIAO", nome_localidade=k, macrorregiao=k, uf="",
                regiao_intermediaria="", cod_regiao_intermediaria="", cod_ibge="")
        for k, v in por_macro.items()
    ]

    # ---- exterior: todos os postos no exterior em uma linha (fora da malha do IBGE)
    linhas_exterior = []
    if exterior:
        linhas_exterior.append(
            agregar(exterior, "EXTERIOR", nome_localidade="Voto no exterior", uf="ZZ",
                    macrorregiao="Exterior", regiao_intermediaria="Exterior",
                    cod_regiao_intermediaria="", cod_ibge="")
        )

    # ---- país = macrorregiões + exterior
    pais = agregar(macros + linhas_exterior, "PAIS", nome_localidade="BRASIL", uf="BR",
                   macrorregiao="BRASIL", regiao_intermediaria="",
                   cod_regiao_intermediaria="", cod_ibge="")

    ordem = {"PAIS": 0, "MACRORREGIAO": 1, "ESTADO": 2, "REGIAO_INTERMEDIARIA": 3,
             "MUNICIPIO": 4, "EXTERIOR": 5}
    linhas = [pais] + macros + linhas_exterior + ufs + ris + municipios
    linhas.sort(key=lambda l: (ordem[l["esfera"]], l["macrorregiao"], l["uf"],
                               l["regiao_intermediaria"], -(l["validos_2t"] or 0)))
    finalizar(linhas)

    # ---- CSV
    CSV_HIER.parent.mkdir(parents=True, exist_ok=True)
    with CSV_HIER.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUNAS, extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            w.writerow({c: (round(l[c], 4) if isinstance(l.get(c), float) else l.get(c, "")) for c in COLUNAS})

    # ---- SQLite
    if DB_HIER.exists():
        DB_HIER.unlink()
    con = sqlite3.connect(DB_HIER)
    tipos = {c: ("REAL" if c.startswith("pct_") else
                 "TEXT" if c in ("esfera", "cod_ibge", "nome_localidade", "uf", "macrorregiao",
                                 "regiao_intermediaria", "cod_regiao_intermediaria",
                                 "vencedor_1t", "vencedor_2t", "houve_virada") else "INTEGER")
             for c in COLUNAS}
    con.execute("CREATE TABLE esferas (" + ", ".join(f"{c} {tipos[c]}" for c in COLUNAS) + ")")
    con.executemany(
        f"INSERT INTO esferas ({', '.join(COLUNAS)}) VALUES ({', '.join('?' * len(COLUNAS))})",
        [[l.get(c) for c in COLUNAS] for l in linhas],
    )
    con.execute("CREATE INDEX ix_esfera ON esferas (esfera)")
    con.execute("CREATE INDEX ix_uf ON esferas (uf)")
    con.commit()
    con.close()

    # ---- payload do viewer
    JS_HIER.parent.mkdir(parents=True, exist_ok=True)
    def celula(linha, col):
        v = linha.get(col)
        if isinstance(v, float):
            return round(v, 2)
        return v if v is not None else ""

    payload = {"cols": COLUNAS, "rows": [[celula(l, c) for c in COLUNAS] for l in linhas]}
    JS_HIER.write_text(
        "window.HIER=" + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    contagem = {}
    for l in linhas:
        contagem[l["esfera"]] = contagem.get(l["esfera"], 0) + 1
    print(f"\nOK: {CSV_HIER}  ({len(linhas)} linhas)")
    print(f"OK: {DB_HIER}")
    print(f"OK: {JS_HIER}")
    print("  " + " | ".join(f"{k}: {v}" for k, v in sorted(contagem.items())))
    print(f"\nBrasil: válidos 1ºT {pais['validos_1t']:,} | 2ºT {pais['validos_2t']:,} | "
          f"viradas {sum(1 for l in linhas if l['houve_virada'] == 'SIM')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
