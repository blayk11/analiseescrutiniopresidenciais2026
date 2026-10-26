#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Camada histórica + motor de validação estatística.

Lê a base hierárquica de 2026 (dados/base_hierarquica.db) e o histórico 2018/2022
(dados/historico.db), calcula por localidade e regrava:

    dados/base_completa.db        tabela esferas (base + histórico + estatística)
    saidas/base_completa.csv
    site/dados.js                 payload do frontend

Definições (todas determinísticas, nenhuma estimativa de modelo):

    delta_pp       = pct Lula 2ºT - pct Lula 1ºT          (pontos percentuais sobre válidos)
    swing_22_26    = pct PT 2026 1ºT - pct PT 2022 1ºT     (p.p.)
    swing_18_22    = pct PT 2022 1ºT - pct PT 2018 1ºT     (p.p.)
    z              = (x - média da região intermediária) / desvio padrão amostral da região
    classificação  = |z| <= 1,5 padrão | <= 2,5 notável | > 2,5 outlier

Decomposição do ganho do vencedor (identidade contábil exata, sem hipótese):

    ΔW = ΔV - P - ΔL
      ΔV = variação dos votos válidos totais
      P  = votos de terceiros no 1º turno (deixam de existir no 2º)
      ΔL = variação do adversário (negativa => transferiu)

Uso:
    python estatistica.py
"""

from __future__ import annotations

import csv
import json
import math
import sqlite3
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DB_BASE = RAIZ / "dados" / "base_hierarquica.db"
DB_HIST = RAIZ / "dados" / "historico.db"
DB_OUT = RAIZ / "dados" / "base_completa.db"
CSV_OUT = RAIZ / "saidas" / "base_completa.csv"
JS_OUT = RAIZ / "site" / "dados.js"

ANOS = [2018, 2022]
MIN_N = 5          # regiões com menos municípios que isso não geram z-score
Z_LIMIAR = (1.5, 2.5)

HIST_COLS = []
for ano in ANOS:
    for t in (1, 2):
        HIST_COLS += [f"pt_{ano}_{t}t", f"polo_b_{ano}_{t}t", f"validos_{ano}_{t}t"]

DERIVADAS = [
    "pct_pt_2018", "pct_polo_b_2018", "pct_pt_2022", "pct_polo_b_2022",
    "swing_18_22", "swing_22_26",
    "margem_2018", "margem_2022", "margem_2026",
    "vencedor_2018", "vencedor_2022", "vencedor_2026", "perfil_historico",
    "delta_pp", "delta_abst_pp",
    "z_delta_ri", "z_delta_uf", "z_swing_ri", "z_swing_uf", "z_abst_ri",
    "z_delta_br", "base_z",
    "classificacao_z", "decomp_validos", "decomp_terceiros", "decomp_adversario",
    "motor_dominante", "motor_share",
    "media_delta_ri", "sd_delta_ri", "n_ri", "media_delta_uf", "sd_delta_uf",
    "n_consistente_a", "n_consistente_b", "n_inclinado_a", "n_inclinado_b",
    "n_pendulo", "n_sem_historico", "n_outliers", "z_medio", "n_viradas",
]

MUN_COLS_UI = [
    "indice", "pai", "esfera", "nome_localidade", "uf", "macrorregiao", "regiao_intermediaria",
    "cod_ibge", "eleitores_aptos_2t", "comparecimento_1t", "comparecimento_2t",
    "pct_comparecimento_2t", "pct_abstencao_2t",
    "brancos_2t", "nulos_2t", "pct_brancos_2t", "pct_nulos_2t", "validos_1t", "validos_2t",
    "lula_1t", "pct_lula_1t", "flavio_1t", "pct_flavio_1t",
    "lula_2t", "pct_lula_2t", "flavio_2t", "pct_flavio_2t",
    "outros_1t", "pct_outros_1t", "cury_1t", "renan_1t", "caiado_1t",
    "houve_virada", "vencedor_1t", "vencedor_2t", "saldo_virada",
    "pct_no_estado", "pct_no_brasil",
    "pt_2018_1t", "polo_b_2018_1t", "pt_2022_1t", "polo_b_2022_1t",
    "pct_pt_2018", "pct_pt_2022", "swing_18_22", "swing_22_26",
    "margem_2018", "margem_2022", "margem_2026",
    "vencedor_2018", "vencedor_2022", "vencedor_2026", "perfil_historico",
    "delta_pp", "delta_abst_pp",
    "z_delta_ri", "z_delta_uf", "z_swing_ri", "z_swing_uf", "z_abst_ri",
    "z_delta_br", "base_z",
    "classificacao_z", "decomp_validos", "decomp_terceiros", "decomp_adversario",
    "motor_dominante", "motor_share",
    "media_delta_ri", "sd_delta_ri", "n_ri", "media_delta_uf", "sd_delta_uf",
    "n_consistente_a", "n_consistente_b", "n_inclinado_a", "n_inclinado_b",
    "n_pendulo", "n_sem_historico", "n_outliers", "z_medio", "n_viradas",
]


def num(v):
    return None if v in (None, "") else float(v)


def pct(parte, total):
    return (parte / total * 100) if total else None


def media_sd(valores):
    vals = [v for v in valores if v is not None]
    n = len(vals)
    if n < MIN_N:
        return None, None
    m = sum(vals) / n
    var = sum((v - m) ** 2 for v in vals) / (n - 1)
    return m, math.sqrt(var)


def zscore(x, m, sd):
    if x is None or m is None or not sd:
        return None
    return (x - m) / sd


def classificar(z):
    if z is None:
        return "Sem base estatística"
    a = abs(z)
    if a <= Z_LIMIAR[0]:
        return "Padrão esperado"
    if a <= Z_LIMIAR[1]:
        return "Variação notável"
    return "Outlier estatístico"


def perfil(vencedores, margens):
    if any(v is None for v in vencedores) or any(m is None for m in margens):
        return "Sem histórico completo"
    if len(set(vencedores)) == 1:
        polo = vencedores[0]
        return f"Consistente Polo {polo}" if min(margens) > 10 else f"Inclinado Polo {polo}"
    return "Pêndulo"


def main() -> int:
    for arq in (DB_BASE, DB_HIST):
        if not arq.exists():
            raise SystemExit(f"Faltando {arq}\nRode: python extrair_presidente.py && "
                             "python agregar_esferas.py && python historico.py")

    hist_con = sqlite3.connect(DB_HIST)
    hist = {}
    for ano, turno, uf, cd, pt, pb, val in hist_con.execute(
        "SELECT ano, turno, uf, cd_municipio, votos_pt, votos_polo_b, votos_validos FROM historico"
    ):
        hist.setdefault((uf, cd), {})[(ano, turno)] = (pt, pb, val)
    hist_con.close()

    base = sqlite3.connect(DB_BASE)
    base.row_factory = sqlite3.Row
    linhas = [dict(r) for r in base.execute("SELECT * FROM esferas ORDER BY rowid")]
    base.close()

    for l in linhas:
        for c in HIST_COLS + DERIVADAS:
            l.setdefault(c, None)

    # ---------------------------------------------------------------- histórico
    pais = next(l for l in linhas if l["esfera"] == "PAIS")
    por_uf = {l["uf"]: l for l in linhas if l["esfera"] == "ESTADO"}
    por_macro = {l["macrorregiao"]: l for l in linhas if l["esfera"] == "MACRORREGIAO"}
    por_ri = {l["cod_regiao_intermediaria"]: l for l in linhas if l["esfera"] == "REGIAO_INTERMEDIARIA"}

    municipios = [l for l in linhas if l["esfera"] == "MUNICIPIO"]
    sem_hist = []
    for m in municipios:
        reg = hist.get((str(m["uf"]).lower(), str(m["cd_municipio"])))
        if not reg:
            sem_hist.append((m["uf"], m["cd_municipio"], m["nome_localidade"]))
            continue
        for ano in ANOS:
            for t in (1, 2):
                pt, pb, val = reg.get((ano, t), (0, 0, 0))
                m[f"pt_{ano}_{t}t"] = pt
                m[f"polo_b_{ano}_{t}t"] = pb
                m[f"validos_{ano}_{t}t"] = val

        # soma para as esferas superiores
        for alvo in (por_ri.get(m["cod_regiao_intermediaria"]), por_uf.get(m["uf"]),
                     por_macro.get(m["macrorregiao"]), pais):
            if alvo is None:
                continue
            for c in HIST_COLS:
                alvo[c] = (alvo[c] or 0) + (m[c] or 0)

    if sem_hist:
        print(f"AVISO: {len(sem_hist)} município(s) sem histórico: {sem_hist[:3]}")

    # ---------------------------------------------------------------- derivadas
    for l in linhas:
        v18, v22 = l.get("validos_2018_1t"), l.get("validos_2022_1t")
        l["pct_pt_2018"] = pct(l.get("pt_2018_1t"), v18)
        l["pct_polo_b_2018"] = pct(l.get("polo_b_2018_1t"), v18)
        l["pct_pt_2022"] = pct(l.get("pt_2022_1t"), v22)
        l["pct_polo_b_2022"] = pct(l.get("polo_b_2022_1t"), v22)

        if l["pct_pt_2018"] is not None and l["pct_pt_2022"] is not None:
            l["swing_18_22"] = l["pct_pt_2022"] - l["pct_pt_2018"]
        if l["pct_pt_2022"] is not None and l.get("pct_lula_1t") is not None:
            l["swing_22_26"] = l["pct_lula_1t"] - l["pct_pt_2022"]

        if l["pct_pt_2018"] is not None:
            l["margem_2018"] = abs(l["pct_pt_2018"] - l["pct_polo_b_2018"])
            l["vencedor_2018"] = "A" if l["pct_pt_2018"] > l["pct_polo_b_2018"] else "B"
        if l["pct_pt_2022"] is not None:
            l["margem_2022"] = abs(l["pct_pt_2022"] - l["pct_polo_b_2022"])
            l["vencedor_2022"] = "A" if l["pct_pt_2022"] > l["pct_polo_b_2022"] else "B"
        if l.get("pct_lula_1t") is not None and l.get("pct_flavio_1t") is not None:
            l["margem_2026"] = abs(l["pct_lula_1t"] - l["pct_flavio_1t"])
            l["vencedor_2026"] = "A" if l["pct_lula_1t"] > l["pct_flavio_1t"] else "B"

        l["perfil_historico"] = perfil(
            [l["vencedor_2018"], l["vencedor_2022"], l["vencedor_2026"]],
            [l["margem_2018"], l["margem_2022"], l["margem_2026"]],
        )

        if l.get("pct_lula_1t") is not None and l.get("pct_lula_2t") is not None:
            l["delta_pp"] = l["pct_lula_2t"] - l["pct_lula_1t"]
        if l.get("pct_abstencao_1t") is not None and l.get("pct_abstencao_2t") is not None:
            l["delta_abst_pp"] = l["pct_abstencao_2t"] - l["pct_abstencao_1t"]

        # decomposição exata do ganho do vencedor do 2º turno
        v1, v2 = l.get("validos_1t"), l.get("validos_2t")
        outros = l.get("outros_1t")
        if l.get("vencedor_2t") == "LULA":
            dw = (l.get("lula_2t") or 0) - (l.get("lula_1t") or 0)
            dl = (l.get("flavio_2t") or 0) - (l.get("flavio_1t") or 0)
        elif l.get("vencedor_2t") == "FLÁVIO BOLSONARO":
            dw = (l.get("flavio_2t") or 0) - (l.get("flavio_1t") or 0)
            dl = (l.get("lula_2t") or 0) - (l.get("lula_1t") or 0)
        else:
            dw = dl = None
        if dw is not None and v1 is not None and v2 is not None and outros is not None:
            c_validos = v2 - v1
            c_terceiros = -outros
            c_adversario = -dl
            l["decomp_validos"] = c_validos
            l["decomp_terceiros"] = c_terceiros
            l["decomp_adversario"] = c_adversario
            bruto = {"crescimento do colégio válido": c_validos,
                     "migração de terceiros": c_terceiros,
                     "conversão direta (perda do adversário)": c_adversario}
            dominante = max(bruto, key=lambda k: bruto[k])
            l["motor_dominante"] = dominante
            if dw:
                l["motor_share"] = bruto[dominante] / abs(dw) * 100

    # ---------------------------------------------------------------- z-scores
    def z_por_grupo(campo, chave, campo_z, prefixo=None):
        grupos: dict[str, list] = {}
        for m in municipios:
            grupos.setdefault(m[chave], []).append(m[campo])
        stats = {k: media_sd(v) for k, v in grupos.items()}
        for m in municipios:
            media, sd = stats.get(m[chave], (None, None))
            m[campo_z] = zscore(m[campo], media, sd)
            if prefixo:
                m[f"media_{prefixo}"] = media
                m[f"sd_{prefixo}"] = sd
                m[f"n_{prefixo.replace('delta_', '')}"] = len(grupos.get(m[chave], []))

    z_por_grupo("delta_pp", "cod_regiao_intermediaria", "z_delta_ri", "delta_ri")
    z_por_grupo("delta_pp", "uf", "z_delta_uf", "delta_uf")
    z_por_grupo("swing_22_26", "cod_regiao_intermediaria", "z_swing_ri")
    z_por_grupo("swing_22_26", "uf", "z_swing_uf")
    z_por_grupo("delta_abst_pp", "cod_regiao_intermediaria", "z_abst_ri")

    # fallback: regiões com menos de MIN_N municípios (ex.: DF) não têm desvio próprio
    media_br, sd_br = media_sd([m["delta_pp"] for m in municipios])
    for m in municipios:
        m["z_delta_br"] = zscore(m["delta_pp"], media_br, sd_br)
        if m["z_delta_ri"] is not None:
            m["base_z"] = "região intermediária"
        elif m["z_delta_br"] is not None:
            m["base_z"] = "Brasil"
        else:
            m["base_z"] = None
        m["classificacao_z"] = classificar(
            m["z_delta_ri"] if m["z_delta_ri"] is not None else m["z_delta_br"]
        )

    # ---------------------------------------------------------------- agregados
    pais_de = {}
    for m in municipios:
        for alvo in (por_ri.get(m["cod_regiao_intermediaria"]), por_uf.get(m["uf"]),
                     por_macro.get(m["macrorregiao"]), pais):
            if alvo is not None:
                pais_de.setdefault(id(alvo), []).append(m)

    for l in linhas:
        if l["esfera"] == "MUNICIPIO":
            continue  # contagens de perfil só fazem sentido em esfera agregada
        filhos = pais_de.get(id(l), [])
        contagem = {}
        for f in filhos:
            contagem[f["perfil_historico"]] = contagem.get(f["perfil_historico"], 0) + 1
        l["n_consistente_a"] = contagem.get("Consistente Polo A", 0)
        l["n_consistente_b"] = contagem.get("Consistente Polo B", 0)
        l["n_inclinado_a"] = contagem.get("Inclinado Polo A", 0)
        l["n_inclinado_b"] = contagem.get("Inclinado Polo B", 0)
        l["n_pendulo"] = contagem.get("Pêndulo", 0)
        l["n_sem_historico"] = contagem.get("Sem histórico completo", 0)
        l["n_outliers"] = sum(1 for f in filhos if f["classificacao_z"] == "Outlier estatístico")
        l["n_viradas"] = sum(1 for f in filhos if f["houve_virada"] == "SIM")
        zs = [f["z_delta_ri"] for f in filhos if f["z_delta_ri"] is not None]
        l["z_medio"] = (sum(zs) / len(zs)) if zs else None

    # ---------------------------------------------------------------- saídas
    campos = list(linhas[0].keys())
    for i, l in enumerate(linhas):
        l["indice"] = i

    indice_por = {}
    for i, l in enumerate(linhas):
        if l["esfera"] == "PAIS":
            indice_por["PAIS"] = i
        elif l["esfera"] == "MACRORREGIAO":
            indice_por["M:" + l["macrorregiao"]] = i
        elif l["esfera"] == "ESTADO":
            indice_por["U:" + l["uf"]] = i
        elif l["esfera"] == "REGIAO_INTERMEDIARIA":
            indice_por["R:" + l["cod_regiao_intermediaria"]] = i

    for i, l in enumerate(linhas):
        if l["esfera"] == "PAIS":
            l["pai"] = None
        elif l["esfera"] in ("MACRORREGIAO", "EXTERIOR"):
            l["pai"] = indice_por["PAIS"]
        elif l["esfera"] == "ESTADO":
            l["pai"] = indice_por.get("M:" + l["macrorregiao"])
        elif l["esfera"] == "REGIAO_INTERMEDIARIA":
            l["pai"] = indice_por.get("U:" + l["uf"])
        else:
            l["pai"] = indice_por.get("R:" + str(l["cod_regiao_intermediaria"]))

    campos = ["indice", "pai"] + [c for c in campos if c not in ("indice", "pai")]

    if DB_OUT.exists():
        DB_OUT.unlink()
    con = sqlite3.connect(DB_OUT)
    def tipo(col):
        vals = [l.get(col) for l in linhas if l.get(col) is not None]
        if not vals:
            return "TEXT"
        if all(isinstance(v, int) and not isinstance(v, bool) for v in vals):
            return "INTEGER"
        if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals):
            return "REAL"
        return "TEXT"

    defs = [f"{c} {tipo(c)}" for c in campos]
    con.execute("CREATE TABLE esferas (" + ", ".join(defs) + ")")
    con.executemany(
        f"INSERT INTO esferas ({', '.join(campos)}) VALUES ({', '.join('?' * len(campos))})",
        [[l.get(c) for c in campos] for l in linhas],
    )
    con.execute("CREATE INDEX ix_esfera ON esferas (esfera)")
    con.execute("CREATE INDEX ix_uf ON esferas (uf)")
    con.commit()
    con.close()

    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        for l in linhas:
            w.writerow({c: (round(l[c], 4) if isinstance(l.get(c), float) else l.get(c, "")) for c in campos})

    # ---------------------------------------------------------------- payload do site
    def celula(l, c):
        v = l.get(c)
        if isinstance(v, float):
            return round(v, 2)
        return v if v is not None else ""

    JS_OUT.parent.mkdir(parents=True, exist_ok=True)
    JS_OUT.write_text(
        "window.DADOS=" + json.dumps(
            {"cols": MUN_COLS_UI, "rows": [[celula(l, c) for c in MUN_COLS_UI] for l in linhas]},
            ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    # ---------------------------------------------------------------- resumo
    mun_ok = [m for m in municipios if m["z_delta_ri"] is not None]
    outliers = [m for m in mun_ok if m["classificacao_z"] == "Outlier estatístico"]
    notaveis = [m for m in mun_ok if m["classificacao_z"] == "Variação notável"]
    print(f"municípios com z calculado: {len(mun_ok)} de {len(municipios)}")
    print(f"  outliers (|z| > 2,5):   {len(outliers)}")
    print(f"  variação notável:       {len(notaveis)}")
    print(f"  padrão esperado:        {len(mun_ok) - len(outliers) - len(notaveis)}")
    perfis = {}
    for m in municipios:
        perfis[m["perfil_historico"]] = perfis.get(m["perfil_historico"], 0) + 1
    print("perfis históricos:", ", ".join(f"{k}={v}" for k, v in sorted(perfis.items())))
    print(f"\nOK: {DB_OUT}")
    print(f"OK: {CSV_OUT}")
    print(f"OK: {JS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
