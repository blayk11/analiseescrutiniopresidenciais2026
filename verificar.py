#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verificação de integridade do dataset e da base hierárquica.

Checa reconciliação (filho soma exatamente o pai), contagens por esfera,
percentuais e a igualdade com os totais nacionais do TSE. Sai com código 1
se qualquer checagem falhar.

Uso:
    python verificar.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DB_VOTOS = RAIZ / "dados" / "votos_presidente_2026.db"
DB_HIER = RAIZ / "dados" / "base_hierarquica.db"

ABSOLUTOS = [
    "eleitores_aptos_1t", "comparecimento_1t", "brancos_1t", "nulos_1t", "validos_1t",
    "lula_1t", "flavio_1t", "outros_1t",
    "eleitores_aptos_2t", "comparecimento_2t", "brancos_2t", "nulos_2t", "validos_2t",
    "lula_2t", "flavio_2t",
]

falhas: list[str] = []


def checar(condicao: bool, descricao: str, detalhe: str = "") -> None:
    print(("  OK    " if condicao else "  FALHA ") + descricao + (f"  [{detalhe}]" if detalhe and not condicao else ""))
    if not condicao:
        falhas.append(descricao + (f" — {detalhe}" if detalhe else ""))


def main() -> int:
    for arq in (DB_VOTOS, DB_HIER):
        if not arq.exists():
            raise SystemExit(f"Faltando {arq}\nRode: python extrair_presidente.py && python agregar_esferas.py")

    votos = sqlite3.connect(DB_VOTOS)
    hier = sqlite3.connect(DB_HIER)

    print("\n[1] Dataset de votos")
    mun_tse = votos.execute("SELECT COUNT(DISTINCT uf || cd_municipio) FROM votos").fetchone()[0]
    checar(mun_tse == 5757, f"5.757 unidades no TSE (5.571 municípios + 186 exterior): {mun_tse}")
    dup = votos.execute("""SELECT COUNT(*) FROM (SELECT turno, uf, cd_municipio, nr_candidato, COUNT(*) c
                           FROM votos GROUP BY 1,2,3,4 HAVING c > 1)""").fetchone()[0]
    checar(dup == 0, "sem duplicata de candidato/município/turno", f"{dup} duplicatas")
    sem_voto = votos.execute("SELECT COUNT(*) FROM votos WHERE votos IS NULL").fetchone()[0]
    checar(sem_voto == 0, "sem linha com votos nulos", f"{sem_voto} linhas")

    print("\n[2] Base hierárquica: contagens")
    contagem = dict(hier.execute("SELECT esfera, COUNT(*) FROM esferas GROUP BY 1").fetchall())
    esperado = {"PAIS": 1, "MACRORREGIAO": 5, "EXTERIOR": 1, "ESTADO": 27,
                "REGIAO_INTERMEDIARIA": 133, "MUNICIPIO": 5571}
    for esfera, qtd in esperado.items():
        checar(contagem.get(esfera) == qtd, f"{esfera}: {qtd} linhas", str(contagem.get(esfera)))

    print("\n[3] Reconciliação filho -> pai")
    pais = hier.execute("SELECT * FROM esferas WHERE esfera = 'PAIS'").fetchone()
    colunas = [c[0] for c in hier.execute("SELECT * FROM esferas LIMIT 0").description]
    idx = {c: i for i, c in enumerate(colunas)}

    # município -> região intermediária
    for nome in ABSOLUTOS:
        soma = hier.execute(
            f"SELECT SUM({nome}) FROM esferas WHERE esfera IN ('MUNICIPIO','EXTERIOR')"
        ).fetchone()[0] or 0
        checar(soma == pais[idx[nome]], f"municípios + exterior = Brasil em {nome}", f"{soma} != {pais[idx[nome]]}")

    # UF -> macrorregião e macrorregião -> Brasil
    for nome in ("validos_2t", "lula_2t", "flavio_2t", "eleitores_aptos_2t"):
        soma_macro = hier.execute(f"SELECT SUM({nome}) FROM esferas WHERE esfera = 'MACRORREGIAO'").fetchone()[0]
        soma_uf = hier.execute(f"SELECT SUM({nome}) FROM esferas WHERE esfera = 'ESTADO'").fetchone()[0]
        soma_ri = hier.execute(f"SELECT SUM({nome}) FROM esferas WHERE esfera = 'REGIAO_INTERMEDIARIA'").fetchone()[0]
        soma_ext = hier.execute(f"SELECT SUM({nome}) FROM esferas WHERE esfera = 'EXTERIOR'").fetchone()[0]
        # as três esferas domésticas têm de ser idênticas entre si, e a diferença até o
        # Brasil tem de ser exatamente o exterior (que é uma linha fora da malha do IBGE)
        checar(soma_uf == soma_ri == soma_macro and soma_uf + soma_ext == pais[idx[nome]],
               f"UF = RI = macrorregião e (+ exterior) = Brasil em {nome}",
               f"{soma_uf}/{soma_ri}/{soma_macro} + {soma_ext} != {pais[idx[nome]]}")

    print("\n[4] Percentuais e pesos")
    pior = hier.execute("""SELECT MAX(ABS(s - 100)) FROM
                           (SELECT uf, SUM(pct_no_estado) s FROM esferas
                            WHERE esfera = 'MUNICIPIO' GROUP BY uf)""").fetchone()[0]
    checar(pior is not None and pior < 0.01, "pct_no_estado soma 100% em cada UF", f"desvio {pior}")

    pct_uf = hier.execute("SELECT SUM(pct_no_brasil) FROM esferas WHERE esfera = 'ESTADO'").fetchone()[0]
    ext = hier.execute("SELECT SUM(pct_no_brasil) FROM esferas WHERE esfera = 'EXTERIOR'").fetchone()[0]
    checar(abs(pct_uf + ext - 100) < 0.5, "pct_no_brasil das UFs + exterior = 100%", f"{pct_uf + ext:.4f}")

    ruim = hier.execute("""SELECT COUNT(*) FROM esferas
                           WHERE esfera = 'MUNICIPIO' AND (pct_no_estado IS NULL
                             OR regiao_intermediaria IS NULL OR regiao_intermediaria = ''
                             OR macrorregiao IS NULL OR macrorregiao = '')""").fetchone()[0]
    checar(ruim == 0, "todo município tem macrorregião e região intermediária", f"{ruim} sem")

    print("\n[5] Coerência entre as duas bases")
    br_votos = votos.execute("""SELECT SUM(votos) FROM votos
                                WHERE turno = 2""").fetchone()[0]
    checar(br_votos == pais[idx["validos_2t"]], "válidos 2ºT do dataset = Brasil da base",
           f"{br_votos} != {pais[idx['validos_2t']]}")

    print("\n[6] Viradas")
    v_mun = hier.execute("SELECT COUNT(*) FROM esferas WHERE esfera = 'MUNICIPIO' AND houve_virada = 'SIM'").fetchone()[0]
    checar(v_mun == 212, "212 municípios com virada", str(v_mun))

    votos.close()
    hier.close()

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
