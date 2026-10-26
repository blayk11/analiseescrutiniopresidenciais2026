# Escrutínio presidencial 2026 — dados, estatística e app mobile

Extração, análise e visualização da votação para Presidente em 2026 (1º e 2º turno), com
camada histórica de 2018 e 2022, motor de validação estatística e um app **mobile-first** com
drill-down hierárquico. Todos os números saem de scripts sobre dados oficiais — nada é digitado
à mão.

Segundo turno: **LULA (PT, 13) × FLÁVIO BOLSONARO (PL, 22)**, apuração encerrada em 25/10/2026.

## App

```bash
# abrir direto, sem servidor
start site/index.html        # Windows
# ou servir (necessário só se quiser testar em celular na mesma rede)
python -m http.server 8000 --directory site
```

- Abre no **BRASIL** e desce: macrorregião → estado → região intermediária → município.
- **Migalhas** no topo e botão voltar; busca global por município, UF ou região.
- Em cada estado, atalho **"Ver todos os N municípios"** (sem passar pelas regiões).
- Card com barra empilhada (Lula / Flávio / brancos / nulos), badge de virada e abstenção.
- **"Ver parecer estatístico"** abre um bottom sheet com z-score, swings, decomposição do
  ganho e histórico 2018/2022/2026.
- Lista **virtualizada**: só os cards visíveis existem no DOM (em SP, 9 nós para 645 cidades).

## Achados

| | |
|---|---|
| Placar nacional | Lula 53.879.538 → **64.256.232** (+10.376.694); Flávio 56.104.503 → **59.826.041** (+3.721.538) |
| Divisão do crescimento | **73,7%** dos votos novos nos dois candidatos foram para Lula |
| Viradas municipais | **212** de 5.571 (3,8%): 211 Flávio→Lula e **1** Lula→Flávio (Uirapuru/GO) |
| Região que virou | **Norte**: Flávio ganhava por 458.835 e perdeu por **1.079 votos** |
| Origem do ganho de Lula | 54,5% do saldo veio de municípios onde ele **perdeu** o 1º turno |
| Absorção dos terceiros | r = **−0,18** entre peso dos terceiros no 1º turno e captura por Lula |
| Histórico | 2.170 municípios consistentes Polo A, 1.598 Polo B, 927 pêndulos, 875 inclinados |
| Estatística | 4.866 padrão esperado, 637 variação notável, **68 outliers** (|z| > 2,5) |

Relatório das três perguntas de pesquisa: **[ANALISE.md](ANALISE.md)**.

## Pipeline

Python 3.10+ e stdlib apenas. Sem pandas, sem `pip install`.

```bash
python extrair_presidente.py    # 2026: 11.514 JSON do TSE -> CSV + SQLite (~8 min)
python historico.py             # 2018/2022: ZIP de dados abertos -> SQLite (~30 s)
python agregar_esferas.py       # roll-up município -> RI -> UF -> macrorregião -> Brasil
python estatistica.py           # histórico + swing + z-score -> base final e site/dados.js
python analise.py               # ANALISE.md (três perguntas)
python verificar.py             # integridade de ponta a ponta (sai 1 se algo divergir)
node testes/teste_site.mjs      # 24 asserções do app (DOM mínimo, sem dependências)
```

## Estrutura

```
extrair_presidente.py   JSON do TSE 2026 -> votação nominal por município
historico.py            2018/2022 -> votos PT vs polo B por município
agregar_esferas.py      roll-up hierárquico (5 esferas + exterior)
estatistica.py          histórico, swing, perfil, z-score, decomposição, payload do site
analise.py              ANALISE.md
verificar.py            reconciliação e integridade
ANALISE.md              relatório das três perguntas
site/                   app mobile (index.html, app.js, style.css, dados.js)
saidas/                 base_hierarquica.csv, base_completa.csv, histórico, viradas, UF
testes/teste_site.mjs   teste do app em Node
cache/                  JSON do TSE + ZIPs do IBGE/TSE (gitignored)
dados/                  SQLite/CSV gerados (gitignored)
```

## Base hierárquica

| Nível | Esfera | Linhas |
|---|---|---|
| 0 | `PAIS` | 1 |
| 1 | `MACRORREGIAO` | 5 |
| 2 | `ESTADO` | 27 |
| 3 | `REGIAO_INTERMEDIARIA` (IBGE) | 133 |
| 4 | `MUNICIPIO` | 5.571 |
| — | `EXTERIOR` | 1 |
| | **total** | **5.738** |

Cada linha traz os absolutos somados das filhas e os percentuais **recalculados sobre o
denominador do próprio nível** — nunca média de percentuais. `PAIS` inclui o exterior e bate
exatamente com o total oficial do TSE (124.082.273 válidos no 2º turno).

## Camada histórica

Fonte (Portal de Dados Abertos do TSE, dataset `resultados-2018` e `resultados-2022`):

```
https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona/votacao_partido_munzona_2018.zip
https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona/votacao_partido_munzona_2022.zip
```

Usa o arquivo de **partido** (28 MB / 26 MB) em vez do de candidato (395 MB / 643 MB): o voto
nominal é atribuído ao partido do candidato, e basta para comparar os dois polos.

- **Polo A** = PT (13). **Polo B** = PSL (17) em 2018 e PL (22) em 2022 — o partido de Bolsonaro
  nas duas eleições; nos dois anos o 2º turno foi PT × esse partido.
- O ZIP tem 29 CSVs: 27 UFs (sem Presidente), `_BR.csv` (país inteiro) e `_BRASIL.csv`
  (cópia idêntica do `_BR`). O script lê **só o `_BR.csv`** — somar os dois duplicaria os votos.
- Conferência: os totais de 2022 batem exatamente com o oficial (PT 57.259.504 / PL 51.072.345
  no 1º turno). Em 2018 há **+46 votos** para o PT em relação ao total publicado, resíduo de
  voto em trânsito — 0,0001%, registrado aqui por transparência.
- `CD_MUNICIPIO` vem com 5 dígitos em 2018 e sem zero à esquerda em 2022; o script normaliza.
- O município criado depois de 2022 (**Boa Esperança do Norte/MT**) aparece como
  "Sem histórico completo" — 1 caso, tratado explicitamente.

## Motor estatístico

Tudo determinístico, sem modelo probabilístico e sem juízo político:

| Métrica | Definição |
|---|---|
| `delta_pp` | pct Lula 2ºT − pct Lula 1ºT (pontos percentuais sobre válidos) |
| `swing_18_22` | pct PT 2022 1ºT − pct PT 2018 1ºT |
| `swing_22_26` | pct Lula 2026 1ºT − pct PT 2022 1ºT |
| `z_delta_ri` | (delta − média da **região intermediária**) / desvio padrão amostral da região |
| `z_delta_br` | mesmo cálculo contra todos os municípios (fallback p/ DF e regiões com n < 5) |
| `classificacao_z` | \|z\| ≤ 1,5 **Padrão esperado** · ≤ 2,5 **Variação notável** · > 2,5 **Outlier estatístico** |

**Perfil histórico** (3 ciclos, margem > 10 p.p. como corte):
`Consistente Polo A/B` (venceu os 3 com margem > 10) · `Inclinado Polo A/B` (venceu os 3, mas
com alguma margem ≤ 10) · `Pêndulo` (alternou o polo vencedor) · `Sem histórico completo`.

**Decomposição do ganho do vencedor** — identidade contábil exata, sem hipótese:

```
ΔW = ΔV − P − ΔL
  ΔV = variação dos votos válidos totais
  P  = votos de terceiros no 1º turno (deixam de existir no 2º)
  ΔL = variação do adversário (negativa => transferiu)
```

O fator dominante é o maior termo dessa soma. No Brasil, o motor dominante é o **crescimento do
colégio válido** (+4,7 mi), seguido da migração de terceiros (−9,3 mi) e da perda do adversário.
A decomposição mostra que o pool de terceiros sozinho não explica o delta: ele é 1,51× menor.

## Fontes (todas rastreáveis no código)

| Uso | URL |
|---|---|
| Catálogo de eleições 2026 | `resultados.tse.jus.br/oficial/comum/config/ele-c.json` |
| Municípios de 2026 | `resultados.tse.jus.br/oficial/ele2026/6257/config/mun-e006257-cm.json` |
| Votação nominal 2026 | `resultados.tse.jus.br/oficial/ele2026/{6257|6258}/dados/{uf}/{uf}{cd}-c0001-e00{6257|6258}-u.json` |
| Votação por partido 2018/2022 | `cdn.tse.jus.br/estatistica/sead/odsele/votacao_partido_munzona/votacao_partido_munzona_{ano}.zip` |
| Malha de regiões | `servicodados.ibge.gov.br/api/v1/localidades/estados/{id}/municipios` |

Códigos de eleição: **6257** = Presidente 1º turno, **6258** = 2º turno.

## Validação

`python verificar.py` (tudo roda hoje sem falha):

- 5.757 unidades no TSE, sem duplicata e sem voto nulo de dado.
- Contagem por esfera (1 / 5 / 27 / 133 / 5.571 / 1) e toda linha com pai.
- **Reconciliação**: município + exterior = Brasil em 15 colunas de 2026 e 12 de histórico.
- 2022 oficial × extraído, turno a turno, PT e PL.
- 5.570 municípios com z regional; média dos z = 0 em cada região intermediária.
- Contagem de perfis somando 5.571 e payload do site com 5.738 linhas.

Além disso, a soma dos municípios foi conferida contra os **arquivos oficiais do TSE para
Brasil + 27 UFs + exterior, nos dois turnos (54 conferências): diferença zero**.

## Limitações

1. **Tudo é agregado.** O delta de votos de um município não é transferência de voto entre
   eleitores (falácia ecológica); mistura migração, comparecimento e brancos/nulos.
2. **z-score não é teste de fraude.** É só distância em desvios padrão da própria região.
3. **Histórico usa 1º turno** para comparar 2018/2022/2026, porque é o único turno comum aos
   três ciclos com o mesmo conjunto de candidatos.
4. **2018 difere em 46 votos** do total publicado (voto em trânsito).
5. **Sem 2014.** O recorte cobre 2018 + 2022 + 2026; 2014 mudaria a definição de polo
   (PSDB no 2º turno) e ficou fora para não misturar séries.

## Deploy

O app é estático: publique a pasta `site/` (GitHub Pages, Netlify, Vercel). `site/dados.js` tem
~2,9 MB (já versionado) e carrega por `<script>` — não precisa de servidor de API.

Licença dos dados: CC-BY (Portal de Dados Abertos do TSE). Análise independente, sem vínculo
com o TSE.
