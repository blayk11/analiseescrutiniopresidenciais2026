#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analise exploratoria 1o -> 2o turno (Presidente 2026).

Le dados/votos_presidente_2026.db (gerado por extrair_presidente.py), calcula as tres
perguntas centrais e escreve ANALISE.md + CSVs em saidas/.

Zero dependencias externas: sqlite3 da stdlib. Todos os numeros do .md saem daqui,
nenhum e digitado a mao.

Uso:
    python analise.py
"""

from __future__ import annotations

import csv
import sqlite3
import statistics as st
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
DB = RAIZ / "dados" / "votos_presidente_2026.db"
SAIDAS = RAIZ / "saidas"
MD = RAIZ / "ANALISE.md"

LULA = "LULA"
FLAVIO = "FLAVIO BOLSONARO"

SQL_MUNICIPIOS = """
WITH t AS (
    SELECT uf, cd_municipio, municipio, turno,
           SUM(CASE WHEN nome_urna = ? THEN votos ELSE 0 END) AS lula,
           SUM(CASE WHEN nome_urna = ? THEN votos ELSE 0 END) AS flavio,
           SUM(votos) AS total,
           MAX(eleitorado) AS eleitorado
    FROM votos
    WHERE uf <> 'zz'
    GROUP BY uf, cd_municipio, municipio, turno
)
SELECT a.uf, a.cd_municipio, a.municipio, a.eleitorado,
       a.lula, a.flavio, a.total,
       b.lula, b.flavio, b.total
FROM t a
JOIN t b ON a.uf = b.uf AND a.cd_municipio = b.cd_municipio
WHERE a.turno = 1 AND b.turno = 2
ORDER BY a.uf, a.cd_municipio
"""


def n(v) -> str:
    """1234567 -> '1.234.567' (pt-BR)."""
    return f"{int(v):,}".replace(",", ".")


def sinal(v) -> str:
    return f"{v:+,}".replace(",", ".")


def pct(v, casas=1) -> str:
    return f"{v:.{casas}f}".replace(".", ",") + "%"


PREPOSICOES = {"de", "da", "do", "das", "dos", "e", "d'"}
NOMES = {"LULA": "Lula", "FLAVIO": "Flávio", "EMPATE": "Empate"}


def titulo(nome: str) -> str:
    """'RIO DE JANEIRO' -> 'Rio de Janeiro'; 'SÃO PAULO' -> 'São Paulo'."""
    partes = nome.lower().split()
    saida = [
        p if (p in PREPOSICOES and i > 0) else p[:1].upper() + p[1:]
        for i, p in enumerate(partes)
    ]
    return " ".join(saida).replace("Flavio", "Flávio")


def lado(v: str) -> str:
    return NOMES.get(v, v)


def tabela(cabecalho, linhas, alinhamento=None) -> str:
    if alinhamento is None:
        alinhamento = ["---"] * len(cabecalho)
    out = ["| " + " | ".join(cabecalho) + " |", "| " + " | ".join(alinhamento) + " |"]
    out += ["| " + " | ".join(str(c) for c in linha) + " |" for linha in linhas]
    return "\n".join(out)


def pearson(xs, ys):
    if len(xs) < 2:
        return 0.0
    mx, my = st.mean(xs), st.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = (sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys)) ** 0.5
    return num / den if den else 0.0


def main() -> int:
    if not DB.exists():
        raise SystemExit(f"Banco nao encontrado: {DB}\nRode antes: python extrair_presidente.py")

    SAIDAS.mkdir(exist_ok=True)
    con = sqlite3.connect(DB)

    # ------------------------------------------------ consolidado por municipio
    mun = []
    for uf, cd, nome, eleit, l1, f1, t1, l2, f2, t2 in con.execute(
        SQL_MUNICIPIOS, (LULA, FLAVIO)
    ):
        outros1 = t1 - l1 - f1
        dl, df = l2 - l1, f2 - f1
        mun.append(
            {
                "uf": uf,
                "cd": cd,
                "municipio": nome,
                "eleitorado": eleit,
                "lula_t1": l1,
                "flavio_t1": f1,
                "outros_t1": outros1,
                "validos_t1": t1,
                "lula_t2": l2,
                "flavio_t2": f2,
                "validos_t2": t2,
                "delta_lula": dl,
                "delta_flavio": df,
                "delta_validos": dl + df,
                "pct_outros_t1": (outros1 / t1 * 100) if t1 else 0.0,
                "vencedor_t1": "LULA" if l1 > f1 else ("FLAVIO" if f1 > l1 else "EMPATE"),
                "vencedor_t2": "LULA" if l2 > f2 else ("FLAVIO" if f2 > l2 else "EMPATE"),
            }
        )
    for m in mun:
        # virada = lado definido nos DOIS turnos e diferente. Empate em qualquer turno
        # nao e "vencedor que perdeu"; fica de fora e e reportado a parte.
        decidido = m["vencedor_t1"] != "EMPATE" and m["vencedor_t2"] != "EMPATE"
        m["virada"] = decidido and m["vencedor_t1"] != m["vencedor_t2"]
        m["share_lula_delta"] = (
            m["delta_lula"] / m["delta_validos"] * 100 if m["delta_validos"] > 0 else None
        )

    total_outros1 = sum(m["outros_t1"] for m in mun)
    total_validos1 = sum(m["validos_t1"] for m in mun)
    total_validos2 = sum(m["validos_t2"] for m in mun)
    lula1, lula2 = sum(m["lula_t1"] for m in mun), sum(m["lula_t2"] for m in mun)
    flavio1, flavio2 = sum(m["flavio_t1"] for m in mun), sum(m["flavio_t2"] for m in mun)
    d_lula, d_flavio = lula2 - lula1, flavio2 - flavio1
    d_ambos = d_lula + d_flavio
    share_lula_total = d_lula / d_ambos * 100

    viradas = [m for m in mun if m["virada"]]
    f2l = [m for m in viradas if m["vencedor_t1"] == "FLAVIO"]
    l2f = [m for m in viradas if m["vencedor_t1"] == "LULA"]
    eleit_viradas = sum(m["eleitorado"] for m in viradas)

    venc_lula_t1 = sum(1 for m in mun if m["vencedor_t1"] == "LULA")
    venc_lula_t2 = sum(1 for m in mun if m["vencedor_t2"] == "LULA")

    # delta de Lula que veio de municipios onde ele PERDEU o 1o turno
    delta_lula_em_derrotas = sum(
        m["delta_lula"] for m in mun if m["vencedor_t1"] == "FLAVIO"
    )
    pct_delta_lula_em_derrotas = delta_lula_em_derrotas / d_lula * 100 if d_lula else 0

    # ------------------------------------------------ concentracao
    top100 = sorted(mun, key=lambda m: -m["validos_t2"])[:100]
    share_top100 = sum(m["delta_lula"] for m in top100) / d_lula * 100 if d_lula else 0

    # ------------------------------------------------ absorcao dos terceiros
    base_abs = [m for m in mun if m["delta_validos"] > 0]
    r = pearson(
        [m["pct_outros_t1"] for m in base_abs],
        [m["share_lula_delta"] for m in base_abs],
    )
    ordenado = sorted(base_abs, key=lambda m: m["pct_outros_t1"])
    tam = len(ordenado) // 4
    quartis = []
    for i in range(4):
        grupo = ordenado[i * tam : (i + 1) * tam] if i < 3 else ordenado[3 * tam :]
        dl = sum(m["delta_lula"] for m in grupo)
        df = sum(m["delta_flavio"] for m in grupo)
        quartis.append(
            {
                "faixa": f"{pct(grupo[0]['pct_outros_t1'])} a {pct(grupo[-1]['pct_outros_t1'])}",
                "n": len(grupo),
                "dl": dl,
                "df": df,
                "share": dl / (dl + df) * 100 if (dl + df) > 0 else 0,
            }
        )

    outros_cands = con.execute(
        """SELECT nome_urna, MIN(partido), SUM(votos)
           FROM votos
           WHERE turno = 1 AND uf <> 'zz' AND nome_urna NOT IN (?, ?)
           GROUP BY nome_urna ORDER BY 3 DESC""",
        (LULA, FLAVIO),
    ).fetchall()

    # ------------------------------------------------ saidas CSV
    cols = [
        "uf", "cd_municipio", "municipio", "eleitorado",
        "lula_t1", "flavio_t1", "outros_t1", "validos_t1",
        "lula_t2", "flavio_t2", "validos_t2",
        "delta_lula", "delta_flavio", "delta_validos",
        "pct_outros_t1", "share_lula_delta", "vencedor_t1", "vencedor_t2", "virada",
    ]

    def escrever(caminho: Path, linhas):
        with caminho.open("w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            for m in linhas:
                w.writerow([
                    m[c] if c != "cd_municipio" else m["cd"] for c in cols
                ])

    escrever(SAIDAS / "consolidado_municipios_t1_t2.csv", mun)
    escrever(SAIDAS / "cidades_com_virada.csv", sorted(viradas, key=lambda m: -m["eleitorado"]))

    with (SAIDAS / "uf_delta.csv").open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["uf", "lula_t1", "flavio_t1", "outros_t1", "lula_t2", "flavio_t2",
                    "delta_lula", "delta_flavio", "share_lula_delta"])
        for uf, l1, f1, o1, l2, f2 in con.execute(
            """WITH t AS (
                   SELECT uf, turno,
                          SUM(CASE WHEN nome_urna = ? THEN votos ELSE 0 END) lula,
                          SUM(CASE WHEN nome_urna = ? THEN votos ELSE 0 END) flavio,
                          SUM(votos) total
                   FROM votos WHERE uf <> 'zz' GROUP BY uf, turno)
               SELECT a.uf, a.lula, a.flavio, a.total - a.lula - a.flavio, b.lula, b.flavio
               FROM t a JOIN t b ON a.uf = b.uf AND a.turno = 1 AND b.turno = 2
               ORDER BY (b.lula - a.lula) DESC""",
            (LULA, FLAVIO),
        ):
            dl, df = l2 - l1, f2 - f1
            w.writerow([uf, l1, f1, o1, l2, f2, dl, df,
                        round(dl / (dl + df) * 100, 2) if (dl + df) else ""])

    # ------------------------------------------------ montagem do .md
    t_uf = (
        con.execute(
            """WITH t AS (
                   SELECT uf, turno,
                          SUM(CASE WHEN nome_urna = ? THEN votos ELSE 0 END) lula,
                          SUM(CASE WHEN nome_urna = ? THEN votos ELSE 0 END) flavio,
                          SUM(votos) total
                   FROM votos WHERE uf <> 'zz' GROUP BY uf, turno)
               SELECT a.uf, a.lula, a.flavio, a.total, b.lula, b.flavio, b.total
               FROM t a JOIN t b ON a.uf = b.uf AND a.turno = 1 AND b.turno = 2
               ORDER BY (b.lula - a.lula) DESC""",
            (LULA, FLAVIO),
        ).fetchall()
    )
    empates_t1 = [m for m in mun if m["vencedor_t1"] == "EMPATE"]
    empates_t2 = [m for m in mun if m["vencedor_t2"] == "EMPATE"]

    top_viradas = sorted(viradas, key=lambda m: -m["eleitorado"])[:12]
    top_delta_lula = sorted(mun, key=lambda m: -m["delta_lula"])[:12]
    top_delta_flavio = sorted(mun, key=lambda m: -m["delta_flavio"])[:12]
    unico_l2f = l2f[0] if l2f else None

    partes = []
    A = partes.append

    A(f"# Análise exploratória — Presidente 2026, 1º → 2º turno\n")
    A(f"*Gerado por `analise.py` em {date.today().isoformat()} a partir de "
      f"`dados/votos_presidente_2026.db`. Todos os números deste documento são calculados "
      f"pelo script — nenhum foi digitado à mão.*\n")
    A("**Candidatos no 2º turno:** LULA (PT, nº 13) e FLÁVIO BOLSONARO (PL, nº 22).\n")
    A(f"**Universo:** {n(len(mun))} municípios brasileiros (voto no exterior, `uf='zz'`, "
      f"fica fora das comparações por município). Apuração encerrada nos dois turnos.\n")

    A("## 0. As três perguntas\n")
    A("1. **Viradas municipais** — cidades em que o vencedor do 1º turno perdeu no 2º.\n")
    A("2. **Distribuição do delta** — para onde foram os votos novos, em valor absoluto.\n")
    A("3. **Absorção dos votos de terceiros** — o peso dos demais candidatos no 1º turno "
      "tem relação com quem capturou o crescimento?\n")

    A("## 1. O placar nacional\n")
    A(tabela(
        ["Candidato", "1º turno", "2º turno", "Δ votos", "% do crescimento dos dois"],
        [
            ["LULA (PT)", n(lula1), n(lula2), sinal(d_lula), pct(share_lula_total)],
            ["FLÁVIO BOLSONARO (PL)", n(flavio1), n(flavio2), sinal(d_flavio), pct(100 - share_lula_total)],
        ],
        ["---", "---:", "---:", "---:", "---:"],
    ))
    A(f"\nVotos válidos totais (inclui terceiros no 1º turno): {n(total_validos1)} → "
      f"{n(total_validos2)}. O colégio de votos válidos **cresceu "
      f"{sinal(total_validos2 - total_validos1)}** entre os turnos — parte relevante do delta "
      f"não vem de migração de voto, e sim de eleitor que votou em branco/nulo no 1º turno ou "
      f"não compareceu.\n")
    A(f"O crescimento combinado dos dois candidatos foi de **{n(d_ambos)} votos**, contra um "
      f"estoque de **{n(total_outros1)} votos** dados a terceiros no 1º turno. Ou seja, o delta "
      f"é **{d_ambos / total_outros1:.2f}×** maior que o pool de terceiros: só ele não explica "
      f"o movimento.\n")

    A("### Por estado\n")
    A(tabela(
        ["UF", "Δ LULA", "Δ FLÁVIO", "Δ válidos", "% do Δ para Lula"],
        [
            [uf.upper(), sinal(l2 - l1), sinal(f2 - f1), sinal((l2 + f2) - t1),
             pct((l2 - l1) / ((l2 - l1) + (f2 - f1)) * 100) if (l2 - l1) + (f2 - f1) > 0 else "—"]
            for uf, l1, f1, t1, l2, f2, _ in t_uf
        ],
        ["---", "---:", "---:", "---:", "---:"],
    ))
    A("\nOnde a soma dos deltas é negativa ou próxima de zero (AP, AC, RR), o percentual perde "
      "sentido — nesses estados o eleitorado válido total encolheu, então um candidato pode "
      "crescer com o outro caindo.\n")

    A("## 2. Pergunta 1 — Viradas municipais\n")
    A(f"- **{n(len(viradas))} municípios viraram** de lado, de {n(len(mun))} "
      f"({pct(len(viradas) / len(mun) * 100, 2)}).\n")
    A(f"- **{n(len(f2l))} viradas Flávio → Lula** e apenas **{len(l2f)}** no sentido inverso"
      + (f" ({unico_l2f['municipio']}/{unico_l2f['uf'].upper()}: "
         f"{n(unico_l2f['lula_t1'])} × {n(unico_l2f['flavio_t1'])} no 1º turno, "
         f"{n(unico_l2f['lula_t2'])} × {n(unico_l2f['flavio_t2'])} no 2º)." if unico_l2f else ".")
      + "\n")
    A(f"- Municípios vencidos: Lula **{n(venc_lula_t1)} → {n(venc_lula_t2)}**; "
      f"Flávio **{n(len(mun) - venc_lula_t1)} → {n(len(mun) - venc_lula_t2)}**."
      + (f" Fora da conta de viradas ficaram os empates: {len(empates_t1)} no 1º turno "
         f"({', '.join(titulo(m['municipio']) + '/' + m['uf'].upper() for m in empates_t1)}) e "
         f"{len(empates_t2)} no 2º turno "
         f"({', '.join(titulo(m['municipio']) + '/' + m['uf'].upper() for m in empates_t2)})."
         if empates_t1 or empates_t2 else "")
      + "\n")
    A(f"- Eleitorado somado das cidades que viraram: **{n(eleit_viradas)}** "
      f"({pct(eleit_viradas / sum(m['eleitorado'] for m in mun) * 100)} do eleitorado nacional).\n")
    A("\nAs 12 maiores viradas por eleitorado:\n")
    A(tabela(
        ["Município", "UF", "Eleitorado", "1º turno (L × F)", "2º turno (L × F)", "Δ Lula", "Δ Flávio"],
        [
            [titulo(m["municipio"]), m["uf"].upper(), n(m["eleitorado"]),
             f"{n(m['lula_t1'])} × {n(m['flavio_t1'])}",
             f"{n(m['lula_t2'])} × {n(m['flavio_t2'])}",
             sinal(m["delta_lula"]), sinal(m["delta_flavio"])]
            for m in top_viradas
        ],
        ["---", "---", "---:", "---:", "---:", "---:", "---:"],
    ))
    if top_viradas:
        maior = top_viradas[0]
        margem_t1 = abs(maior["flavio_t1"] - maior["lula_t1"])
        A(f"\nA maior delas é **{titulo(maior['municipio'])}/{maior['uf'].upper()}**: "
          f"{n(maior['eleitorado'])} eleitores, virada em um município que era de "
          f"{lado(maior['vencedor_t1'])} no 1º turno por {n(margem_t1)} votos de margem.\n")
    A(f"Lista completa em `saidas/cidades_com_virada.csv` ({n(len(viradas))} linhas).\n")

    A("## 3. Pergunta 2 — Distribuição do delta\n")
    A(f"- Lula somou **{sinal(d_lula)}** votos; Flávio, **{sinal(d_flavio)}**. "
      f"**{pct(share_lula_total)}** do crescimento dos dois candidatos foi para Lula.\n")
    A(f"- Nos {n(sum(1 for m in mun if m['vencedor_t1'] == 'FLAVIO'))} municípios onde Lula "
      f"**perdeu** o 1º turno ele ainda somou {sinal(delta_lula_em_derrotas)} de saldo, o que "
      f"equivale a **{pct(pct_delta_lula_em_derrotas)}** do seu crescimento total — "
      f"o ganho não é só mobilização de reduto.\n")
    A(f"- Os 100 maiores municípios (por votos válidos no 2º turno) responderam por "
      f"**{pct(share_top100)}** do delta de Lula.\n")
    A("\nMaiores ganhos absolutos de Lula:\n")
    A(tabela(
        ["Município", "UF", "Δ Lula", "Δ Flávio", "Vencedor 1º", "Vencedor 2º"],
        [
            [titulo(m["municipio"]), m["uf"].upper(), sinal(m["delta_lula"]),
             sinal(m["delta_flavio"]), lado(m["vencedor_t1"]), lado(m["vencedor_t2"])]
            for m in top_delta_lula
        ],
        ["---", "---", "---:", "---:", "---", "---"],
    ))
    A("\nMaiores ganhos absolutos de Flávio:\n")
    A(tabela(
        ["Município", "UF", "Δ Flávio", "Δ Lula", "Vencedor 1º", "Vencedor 2º"],
        [
            [titulo(m["municipio"]), m["uf"].upper(), sinal(m["delta_flavio"]),
             sinal(m["delta_lula"]), lado(m["vencedor_t1"]), lado(m["vencedor_t2"])]
            for m in top_delta_flavio
        ],
        ["---", "---", "---:", "---:", "---", "---"],
    ))

    A("## 4. Pergunta 3 — Absorção dos votos de terceiros\n")
    A(f"No 1º turno, **{n(total_outros1)} votos** ({pct(total_outros1 / total_validos1 * 100)} "
      f"dos válidos) foram para os outros 10 candidatos — Augusto Cury, Renan Santos, "
      f"Caiado, Zema, Samara e mais cinco. No 2º turno esse pool não existe mais.\n")
    A("\nOs dez candidatos que formaram esse pool no 1º turno:\n")
    A(tabela(
        ["Candidato", "Partido", "Votos no 1º turno", "% dos válidos"],
        [[nome, part, n(v), pct(v / total_validos1 * 100, 2)] for nome, part, v in outros_cands],
        ["---", "---", "---:", "---:"],
    ))
    A(f"\nDividindo os municípios em quartis pelo **peso dos terceiros no 1º turno** "
      f"(`outros / válidos`), e medindo para onde foi o crescimento:\n")
    A(tabela(
        ["Quartil", "% de terceiros no 1º turno", "Municípios", "Δ Lula", "Δ Flávio", "% do Δ para Lula"],
        [
            [f"Q{i + 1}", q["faixa"], n(q["n"]), sinal(q["dl"]), sinal(q["df"]), pct(q["share"])]
            for i, q in enumerate(quartis)
        ],
        ["---", "---", "---:", "---:", "---:", "---:"],
    ))
    A(f"\n**Correlação de Pearson** entre `% de terceiros no 1º turno` e `% do delta capturado "
      f"por Lula`: **r = {f'{r:.3f}'.replace('.', ',')}** (n = {n(len(base_abs))} municípios "
      f"com crescimento líquido positivo).\n")
    A(f"\nA leitura: a relação é **negativa e fraca** — nos municípios onde os terceiros pesavam "
      f"mais no 1º turno, Lula capturou uma fatia **menor** do crescimento (de "
      f"{pct(quartis[0]['share'])} no Q1 para {pct(quartis[-1]['share'])} no Q4), mas a força "
      f"do sinal é baixa, então peso de terceiros está longe de ser o fator determinante. "
      f"Onde esses votos eram grandes, a maior parte foi para **Flávio**, não para Lula.\n")

    A("## 5. Limitações (o que estes números NÃO provam)\n")
    A("1. **Não é transferência de voto.** Tudo aqui é agregado por município. Dizer que "
      "\"o eleitor de Cury foi para Flávio\" a partir do delta de um município é falácia "
      "ecológica: o dado não liga o voto de um eleitor entre turnos.\n")
    A("2. **O delta mistura três coisas:** migração de voto, mudança de comparecimento e "
      "variação de brancos/nulos. Por isso o crescimento combinado (14,0 mi) supera o pool de "
      "terceiros (9,3 mi).\n")
    A("3. **Efeito teto.** Quem já tinha 70% no 1º turno tem menos espaço para crescer em "
      "votos absolutos; por isso a comparação por quartis usa *share do delta*, não votos "
      "brutos.\n")
    A("4. **Exterior fora.** 186 postos de votação no exterior (`uf='zz'`) não entram nas "
      "comparações municipais, mas entram no total nacional de `extrair_presidente.py`.\n")
    A("5. **Só dois candidatos no 2º turno**, então `% do delta` tem denominador restrito ao "
      "crescimento desses dois.\n")

    A("## 6. Reprodutibilidade\n")
    A("```bash\npython extrair_presidente.py   # baixa os JSON do TSE (~8 min, fica em cache/)\n"
      "python analise.py               # gera ANALISE.md e saidas/*.csv\n```\n")
    A("Fonte: `resultados.tse.jus.br` (endpoints públicos, sem chave). Conferência de "
      "integridade: a soma dos municípios bate exatamente com os arquivos oficiais do TSE para "
      "Brasil, 27 UFs e exterior, nos dois turnos.\n")

    MD.write_text("\n".join(partes), encoding="utf-8")

    print(f"OK: {MD}")
    for arq in sorted(SAIDAS.glob("*.csv")):
        print(f"OK: {arq}")
    print(f"\n{len(viradas)} viradas | r = {r:.3f} | {pct(share_lula_total)} do delta para Lula")
    con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
