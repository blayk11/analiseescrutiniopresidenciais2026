#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verificação de integridade de ponta a ponta.

Cobre: dataset de 2026, base hierárquica, histórico 2018/2022, motor estatístico
e o payload do site. Sai com código 1 se qualquer checagem falhar.

Uso:
    python verificar.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DB_VOTOS = RAIZ / "dados" / "votos_presidente_2026.db"
DB_HIER = RAIZ / "dados" / "base_hierarquica.db"
DB_HIST = RAIZ / "dados" / "historico.db"
DB_FINAL = RAIZ / "dados" / "base_completa.db"
JS_SITE = RAIZ / "site" / "dados.js"

ABSOLUTOS = [
    "eleitores_aptos_1t", "comparecimento_1t", "brancos_1t", "nulos_1t", "validos_1t",
    "lula_1t", "flavio_1t", "outros_1t",
    "eleitores_aptos_2t", "comparecimento_2t", "brancos_2t", "nulos_2t", "validos_2t",
    "lula_2t", "flavio_2t",
]
HIST_ABS = [f"{c}_{ano}_{t}t" for ano in (2018, 2022) for t in (1, 2)
            for c in ("pt", "polo_b", "validos")]

falhas: list[str] = []


def checar(condicao: bool, descricao: str, detalhe: str = "") -> None:
    print(("  OK    " if condicao else "  FALHA ") + descricao +
          (f"  [{detalhe}]" if detalhe and not condicao else ""))
    if not condicao:
        falhas.append(descricao + (f" — {detalhe}" if detalhe else ""))


def main() -> int:
    for arq in (DB_VOTOS, DB_HIER, DB_HIST, DB_FINAL, JS_SITE):
        if not arq.exists():
            raise SystemExit(f"Faltando {arq}\nRode o pipeline completo (veja o README).")

    votos = sqlite3.connect(DB_VOTOS)
    hier = sqlite3.connect(DB_HIER)
    hist = sqlite3.connect(DB_HIST)
    final = sqlite3.connect(DB_FINAL)
    final.row_factory = sqlite3.Row

    print("\n[1] Dataset de votos 2026")
    mun_tse = votos.execute("SELECT COUNT(DISTINCT uf || cd_municipio) FROM votos").fetchone()[0]
    checar(mun_tse == 5757, f"5.757 unidades (5.571 municípios + 186 exterior): {mun_tse}")
    dup = votos.execute("""SELECT COUNT(*) FROM (SELECT turno, uf, cd_municipio, nr_candidato,
                           COUNT(*) c FROM votos GROUP BY 1,2,3,4 HAVING c > 1)""").fetchone()[0]
    checar(dup == 0, "sem duplicata de candidato/município/turno", str(dup))
    checar(votos.execute("SELECT COUNT(*) FROM votos WHERE votos IS NULL").fetchone()[0] == 0,
           "sem linha com votos nulos")

    print("\n[2] Base hierárquica")
    contagem = dict(hier.execute("SELECT esfera, COUNT(*) FROM esferas GROUP BY 1").fetchall())
    for esfera, qtd in {"PAIS": 1, "MACRORREGIAO": 5, "EXTERIOR": 1, "ESTADO": 27,
                        "REGIAO_INTERMEDIARIA": 133, "MUNICIPIO": 5571}.items():
        checar(contagem.get(esfera) == qtd, f"{esfera}: {qtd} linhas", str(contagem.get(esfera)))

    cols_h = [c[0] for c in hier.execute("SELECT * FROM esferas LIMIT 0").description]
    ih = {c: i for i, c in enumerate(cols_h)}
    pais_h = hier.execute("SELECT * FROM esferas WHERE esfera = 'PAIS'").fetchone()
    for nome in ABSOLUTOS:
        soma = hier.execute(
            "SELECT SUM(%s) FROM esferas WHERE esfera IN ('MUNICIPIO','EXTERIOR')" % nome
        ).fetchone()[0] or 0
        checar(soma == pais_h[ih[nome]], f"municípios + exterior = Brasil em {nome}",
               f"{soma} != {pais_h[ih[nome]]}")

    print("\n[3] Histórico 2018/2022")
    oficial_2022 = {(1, "PT"): 57259504, (1, "PL"): 51072345,
                    (2, "PT"): 60345999, (2, "PL"): 58206354}
    for (turno, partido), esperado in oficial_2022.items():
        col = "votos_pt" if partido == "PT" else "votos_polo_b"
        valor = hist.execute("SELECT SUM(%s) FROM historico WHERE ano = 2022 AND turno = ?"
                             % col, (turno,)).fetchone()[0]
        checar(valor == esperado, f"2022 T{turno} {partido} = {esperado:,}", f"{valor:,}")

    unidades = hist.execute("SELECT COUNT(DISTINCT uf || cd_municipio) FROM historico WHERE ano = 2022").fetchone()[0]
    checar(unidades >= 5700, f"histórico cobre 5.700+ unidades: {unidades}")

    print("\n[4] Base completa (histórico + estatística)")
    total = final.execute("SELECT COUNT(*) FROM esferas").fetchone()[0]
    checar(total == 5738, f"5.738 linhas na base final: {total}")

    cols_f = [c[0] for c in final.execute("SELECT * FROM esferas LIMIT 0").description]
    ifa = {c: i for i, c in enumerate(cols_f)}
    pais_f = final.execute("SELECT * FROM esferas WHERE esfera = 'PAIS'").fetchone()
    for nome in HIST_ABS:
        soma = final.execute(
            "SELECT SUM(%s) FROM esferas WHERE esfera IN ('MUNICIPIO','EXTERIOR')" % nome
        ).fetchone()[0] or 0
        checar(soma == pais_f[ifa[nome]], f"histórico reconcilia em {nome}",
               f"{soma} != {pais_f[ifa[nome]]}")

    sem_pai = final.execute(
        "SELECT COUNT(*) FROM esferas WHERE esfera <> 'PAIS' AND (pai IS NULL OR pai = '')"
    ).fetchone()[0]
    checar(sem_pai == 0, "toda linha (menos o Brasil) tem pai", str(sem_pai))

    print("\n[5] Motor estatístico")
    com_z = final.execute(
        "SELECT COUNT(*) FROM esferas WHERE esfera = 'MUNICIPIO' AND z_delta_ri IS NOT NULL"
    ).fetchone()[0]
    checar(com_z == 5570, f"5.570 municípios com z regional: {com_z}")
    checar(final.execute(
        "SELECT COUNT(*) FROM esferas WHERE esfera = 'MUNICIPIO' AND classificacao_z IS NULL"
    ).fetchone()[0] == 0, "todo município classificado (fallback Brasil no DF)")

    # dentro de cada região intermediária, a média dos z deve ser ~0 e o desvio ~1
    desvio_max = final.execute("""
        SELECT MAX(ABS(m)) FROM (
            SELECT cod_regiao_intermediaria AS ri, AVG(z_delta_ri) AS m
            FROM esferas WHERE esfera = 'MUNICIPIO' AND z_delta_ri IS NOT NULL
            GROUP BY ri HAVING COUNT(*) >= 5)
    """).fetchone()[0]
    checar(desvio_max is not None and desvio_max < 1e-6,
           "média dos z é zero em cada região", f"max |média| = {desvio_max}")

    pais_perfil = final.execute("SELECT * FROM esferas WHERE esfera = 'PAIS'").fetchone()
    perfis = sum(pais_perfil[ifa[c]] for c in ("n_consistente_a", "n_consistente_b",
                                               "n_inclinado_a", "n_inclinado_b",
                                               "n_pendulo", "n_sem_historico"))
    checar(perfis == 5571, "contagem de perfis soma 5.571 municípios", str(perfis))

    print("\n[6] Payload do site")
    bruto = JS_SITE.read_text(encoding="utf-8")
    payload = json.loads(bruto[bruto.index("=") + 1:].strip().rstrip(";"))
    checar(len(payload["rows"]) == 5738, f"5.738 linhas no lobby: {len(payload['rows'])}")
    checar(len(payload["cols"]) == len(payload["rows"][0]),
           "todas as linhas têm o mesmo número de colunas")
    checar("indice" in payload["cols"] and "pai" in payload["cols"],
           "payload traz índice e pai para a navegação")

    for con in (votos, hier, hist, final):
        con.close()

    print()
    if falhas:
        print(f"{len(falhas)} CHECAGEM(NS) FALHARAM:")
        for f in falhas:
            print(f"  - {f}")
        return 1
    print("TODAS AS CHECAGENS PASSARAM")
    return 0


if __name__ == "__main__":
    sys.exit(main())
