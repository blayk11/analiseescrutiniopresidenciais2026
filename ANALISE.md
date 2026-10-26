# Análise exploratória — Presidente 2026, 1º → 2º turno

*Gerado por `analise.py` em 2026-10-26 a partir de `dados/votos_presidente_2026.db`. Todos os números deste documento são calculados pelo script — nenhum foi digitado à mão.*

**Candidatos no 2º turno:** LULA (PT, nº 13) e FLÁVIO BOLSONARO (PL, nº 22).

**Universo:** 5.571 municípios brasileiros (voto no exterior, `uf='zz'`, fica fora das comparações por município). Apuração encerrada nos dois turnos.

## 0. As três perguntas

1. **Viradas municipais** — cidades em que o vencedor do 1º turno perdeu no 2º.

2. **Distribuição do delta** — para onde foram os votos novos, em valor absoluto.

3. **Absorção dos votos de terceiros** — o peso dos demais candidatos no 1º turno tem relação com quem capturou o crescimento?

## 1. O placar nacional

| Candidato | 1º turno | 2º turno | Δ votos | % do crescimento dos dois |
| --- | ---: | ---: | ---: | ---: |
| LULA (PT) | 53.722.151 | 64.056.078 | +10.333.927 | 73,7% |
| FLÁVIO BOLSONARO (PL) | 55.960.603 | 59.654.544 | +3.693.941 | 26,3% |

Votos válidos totais (inclui terceiros no 1º turno): 118.969.906 → 123.710.622. O colégio de votos válidos **cresceu +4.740.716** entre os turnos — parte relevante do delta não vem de migração de voto, e sim de eleitor que votou em branco/nulo no 1º turno ou não compareceu.

O crescimento combinado dos dois candidatos foi de **14.027.868 votos**, contra um estoque de **9.287.152 votos** dados a terceiros no 1º turno. Ou seja, o delta é **1.51×** maior que o pool de terceiros: só ele não explica o movimento.

### Por estado

| UF | Δ LULA | Δ FLÁVIO | Δ válidos | % do Δ para Lula |
| --- | ---: | ---: | ---: | ---: |
| SP | +2.613.861 | +1.217.155 | +1.375.504 | 68,2% |
| MG | +1.162.163 | +464.238 | +616.650 | 71,5% |
| RJ | +872.372 | +202.189 | +364.726 | 81,2% |
| BA | +820.487 | +166.176 | +533.728 | 83,2% |
| PE | +563.542 | +94.511 | +349.050 | 85,6% |
| RS | +529.793 | +300.595 | +275.884 | 63,8% |
| PR | +511.907 | +346.099 | +272.705 | 59,7% |
| CE | +480.861 | +62.628 | +237.788 | 88,5% |
| GO | +396.675 | +293.446 | +103.066 | 57,5% |
| SC | +291.146 | +220.051 | +137.488 | 57,0% |
| PA | +263.212 | +35.983 | +27.217 | 88,0% |
| PB | +252.932 | +33.833 | +145.522 | 88,2% |
| MA | +241.930 | -9.069 | +27.763 | 103,9% |
| RN | +175.633 | +16.916 | +79.107 | 91,2% |
| AL | +157.162 | +8.422 | +77.905 | 94,9% |
| ES | +151.937 | +61.310 | +45.391 | 71,2% |
| DF | +149.597 | +69.926 | +31.958 | 68,1% |
| SE | +133.022 | +15.515 | +58.199 | 89,6% |
| PI | +130.279 | +8.831 | +33.454 | 93,7% |
| MT | +112.486 | +52.518 | +51.978 | 68,2% |
| MS | +112.118 | +54.541 | +66.587 | 67,3% |
| AM | +98.787 | -1.519 | -49.735 | 101,6% |
| RO | +43.779 | +21.394 | +769 | 67,2% |
| TO | +38.953 | -1.405 | -19.569 | 103,7% |
| AP | +10.465 | -13.604 | -43.216 | — |
| AC | +9.743 | -15.092 | -36.838 | — |
| RR | +9.085 | -11.647 | -22.365 | — |

Onde a soma dos deltas é negativa ou próxima de zero (AP, AC, RR), o percentual perde sentido — nesses estados o eleitorado válido total encolheu, então um candidato pode crescer com o outro caindo.

## 2. Pergunta 1 — Viradas municipais

- **212 municípios viraram** de lado, de 5.571 (3,81%).

- **211 viradas Flávio → Lula** e apenas **1** no sentido inverso (UIRAPURU/GO: 930 × 854 no 1º turno, 1.069 × 1.087 no 2º).

- Municípios vencidos: Lula **2.663 → 2.875**; Flávio **2.908 → 2.696**. Fora da conta de viradas ficaram os empates: 2 no 1º turno (Trabiju/SP, Crixás do Tocantins/TO) e 1 no 2º turno (Marquinho/PR).

- Eleitorado somado das cidades que viraram: **10.901.618** (6,9% do eleitorado nacional).


As 12 maiores viradas por eleitorado:

| Município | UF | Eleitorado | 1º turno (L × F) | 2º turno (L × F) | Δ Lula | Δ Flávio |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Rio de Janeiro | RJ | 4.952.612 | 1.524.517 × 1.662.354 | 1.898.391 × 1.785.198 | +373.874 | +122.844 |
| Osasco | SP | 583.991 | 182.778 × 191.726 | 234.320 × 213.187 | +51.542 | +21.461 |
| Ananindeua | PA | 358.249 | 127.573 × 130.954 | 152.008 × 136.916 | +24.435 | +5.962 |
| Macapá | AP | 321.597 | 114.179 × 124.378 | 125.479 × 120.593 | +11.300 | -3.785 |
| São Vicente | SP | 256.025 | 73.549 × 87.214 | 95.326 × 93.907 | +21.777 | +6.693 |
| Ribeirão das Neves | MG | 218.584 | 71.008 × 75.218 | 89.343 × 81.574 | +18.335 | +6.356 |
| Cotia | SP | 194.159 | 59.084 × 65.331 | 76.363 × 72.794 | +17.279 | +7.463 |
| Araraquara | SP | 170.310 | 56.181 × 57.432 | 68.699 × 63.218 | +12.518 | +5.786 |
| Santa Luzia | MG | 164.668 | 51.624 × 59.701 | 66.465 × 64.730 | +14.841 | +5.029 |
| Alvorada | RS | 135.997 | 42.505 × 46.134 | 54.052 × 50.071 | +11.547 | +3.937 |
| Ibirité | MG | 122.338 | 39.349 × 43.183 | 50.512 × 46.937 | +11.163 | +3.754 |
| Sapucaia do Sul | RS | 102.445 | 31.819 × 34.384 | 40.061 × 37.422 | +8.242 | +3.038 |

A maior delas é **Rio de Janeiro/RJ**: 4.952.612 eleitores, virada em um município que era de Flávio no 1º turno por 137.837 votos de margem.

Lista completa em `saidas/cidades_com_virada.csv` (212 linhas).

## 3. Pergunta 2 — Distribuição do delta

- Lula somou **+10.333.927** votos; Flávio, **+3.693.941**. **73,7%** do crescimento dos dois candidatos foi para Lula.

- Nos 2.906 municípios onde Lula **perdeu** o 1º turno ele ainda somou +5.631.486 de saldo, o que equivale a **54,5%** do seu crescimento total — o ganho não é só mobilização de reduto.

- Os 100 maiores municípios (por votos válidos no 2º turno) responderam por **45,0%** do delta de Lula.


Maiores ganhos absolutos de Lula:

| Município | UF | Δ Lula | Δ Flávio | Vencedor 1º | Vencedor 2º |
| --- | --- | ---: | ---: | --- | --- |
| São Paulo | SP | +812.005 | +337.176 | Lula | Lula |
| Rio de Janeiro | RJ | +373.874 | +122.844 | Flávio | Lula |
| Salvador | BA | +209.714 | +30.564 | Lula | Lula |
| Brasília | DF | +149.597 | +69.926 | Flávio | Flávio |
| Belo Horizonte | MG | +149.091 | +74.351 | Flávio | Flávio |
| Fortaleza | CE | +135.280 | +33.383 | Lula | Lula |
| Curitiba | PR | +92.993 | +73.523 | Flávio | Flávio |
| Recife | PE | +89.821 | +23.074 | Lula | Lula |
| Manaus | AM | +81.391 | +16.028 | Flávio | Flávio |
| Porto Alegre | RS | +78.767 | +35.551 | Lula | Lula |
| Guarulhos | SP | +77.863 | +29.784 | Flávio | Flávio |
| Goiânia | GO | +77.538 | +71.673 | Flávio | Flávio |

Maiores ganhos absolutos de Flávio:

| Município | UF | Δ Flávio | Δ Lula | Vencedor 1º | Vencedor 2º |
| --- | --- | ---: | ---: | --- | --- |
| São Paulo | SP | +337.176 | +812.005 | Lula | Lula |
| Rio de Janeiro | RJ | +122.844 | +373.874 | Flávio | Lula |
| Belo Horizonte | MG | +74.351 | +149.091 | Flávio | Flávio |
| Curitiba | PR | +73.523 | +92.993 | Flávio | Flávio |
| Goiânia | GO | +71.673 | +77.538 | Flávio | Flávio |
| Brasília | DF | +69.926 | +149.597 | Flávio | Flávio |
| Porto Alegre | RS | +35.551 | +78.767 | Lula | Lula |
| Fortaleza | CE | +33.383 | +135.280 | Lula | Lula |
| Salvador | BA | +30.564 | +209.714 | Lula | Lula |
| Campinas | SP | +30.489 | +61.942 | Flávio | Flávio |
| Guarulhos | SP | +29.784 | +77.863 | Flávio | Flávio |
| São Bernardo do Campo | SP | +24.299 | +53.731 | Lula | Lula |
## 4. Pergunta 3 — Absorção dos votos de terceiros

No 1º turno, **9.287.152 votos** (7,8% dos válidos) foram para os outros 10 candidatos — Augusto Cury, Renan Santos, Caiado, Zema, Samara e mais cinco. No 2º turno esse pool não existe mais.


Os dez candidatos que formaram esse pool no 1º turno:

| Candidato | Partido | Votos no 1º turno | % dos válidos |
| --- | --- | ---: | ---: |
| ESCRITOR AUGUSTO CURY | AVANTE | 3.438.835 | 2,89% |
| RENAN SANTOS | MISSÃO | 2.667.307 | 2,24% |
| RONALDO CAIADO | PSD | 2.600.440 | 2,19% |
| ZEMA | NOVO | 323.159 | 0,27% |
| SAMARA | UP | 121.858 | 0,10% |
| HERTZ DIAS | PSTU | 42.730 | 0,04% |
| CLARIANA BARAO | DC | 39.218 | 0,03% |
| EDMILSON COSTA | PCB | 22.272 | 0,02% |
| VETERINÁRIO WILSON GRASSI | DEMOCRATA | 16.508 | 0,01% |
| RUI COSTA PIMENTA | PCO | 14.825 | 0,01% |

Dividindo os municípios em quartis pelo **peso dos terceiros no 1º turno** (`outros / válidos`), e medindo para onde foi o crescimento:

| Quartil | % de terceiros no 1º turno | Municípios | Δ Lula | Δ Flávio | % do Δ para Lula |
| --- | --- | ---: | ---: | ---: | ---: |
| Q1 | 1,6% a 4,4% | 1.348 | +897.617 | +62.867 | 93,5% |
| Q2 | 4,4% a 5,7% | 1.348 | +1.114.204 | +223.904 | 83,3% |
| Q3 | 5,7% a 7,5% | 1.348 | +2.217.070 | +640.610 | 77,6% |
| Q4 | 7,5% a 33,2% | 1.351 | +6.110.322 | +2.828.839 | 68,4% |

**Correlação de Pearson** entre `% de terceiros no 1º turno` e `% do delta capturado por Lula`: **r = -0,183** (n = 5.395 municípios com crescimento líquido positivo).


A leitura: a relação é **negativa e fraca** — nos municípios onde os terceiros pesavam mais no 1º turno, Lula capturou uma fatia **menor** do crescimento (de 93,5% no Q1 para 68,4% no Q4), mas a força do sinal é baixa, então peso de terceiros está longe de ser o fator determinante. Onde esses votos eram grandes, a maior parte foi para **Flávio**, não para Lula.

## 5. Limitações (o que estes números NÃO provam)

1. **Não é transferência de voto.** Tudo aqui é agregado por município. Dizer que "o eleitor de Cury foi para Flávio" a partir do delta de um município é falácia ecológica: o dado não liga o voto de um eleitor entre turnos.

2. **O delta mistura três coisas:** migração de voto, mudança de comparecimento e variação de brancos/nulos. Por isso o crescimento combinado (14,0 mi) supera o pool de terceiros (9,3 mi).

3. **Efeito teto.** Quem já tinha 70% no 1º turno tem menos espaço para crescer em votos absolutos; por isso a comparação por quartis usa *share do delta*, não votos brutos.

4. **Exterior fora.** 186 postos de votação no exterior (`uf='zz'`) não entram nas comparações municipais, mas entram no total nacional de `extrair_presidente.py`.

5. **Só dois candidatos no 2º turno**, então `% do delta` tem denominador restrito ao crescimento desses dois.

## 6. Reprodutibilidade

```bash
python extrair_presidente.py   # baixa os JSON do TSE (~8 min, fica em cache/)
python analise.py               # gera ANALISE.md e saidas/*.csv
```

Fonte: `resultados.tse.jus.br` (endpoints públicos, sem chave). Conferência de integridade: a soma dos municípios bate exatamente com os arquivos oficiais do TSE para Brasil, 27 UFs e exterior, nos dois turnos.
