# Análise de escrutínio — Presidente 2026 (1º → 2º turno)

Extração e análise **determinística** da votação para Presidente nas Eleições 2026, município
por município, a partir dos JSON públicos de `resultados.tse.jus.br`. Nenhum número deste
repositório é digitado à mão: tudo sai de dois scripts Python sobre os arquivos oficiais do TSE.

Segundo turno: **LULA (PT, 13) × FLÁVIO BOLSONARO (PL, 22)**, apuração encerrada em 25/10/2026.

## Achados principais

Relatório completo, com todas as tabelas: **[ANALISE.md](ANALISE.md)**.

| | |
|---|---|
| Placar nacional (só municípios) | Lula 53.722.151 → **64.056.078** (+10.333.927); Flávio 55.960.603 → **59.654.544** (+3.693.941) |
| Divisão do crescimento | **73,7%** dos votos novos foram para Lula, 26,3% para Flávio |
| Viradas municipais | **212** (3,8% dos 5.571): 211 Flávio→Lula e **1** Lula→Flávio (Uirapuru/GO) |
| Maior virada | Rio de Janeiro/RJ — 4,95 mi de eleitores, era de Flávio no 1º turno por 137.837 votos |
| Origem do ganho de Lula | 54,5% do saldo veio de municípios onde ele **perdeu** o 1º turno |
| Absorção dos terceiros | r = **−0,18** entre peso dos terceiros no 1º turno e captura por Lula — relação negativa e fraca |

O ponto metodológico central: o crescimento combinado dos dois candidatos (14,0 mi) é
**1,51× maior** que o pool de votos dados a terceiros no 1º turno (9,3 mi). Logo, o delta não
se explica por migração de voto de terceiros — boa parte vem de mudança de comparecimento e de
brancos/nulos.

## Como reproduzir

Só precisa de Python 3.10+ e da stdlib. Sem pandas, sem pip install.

```bash
python extrair_presidente.py    # baixa 11.514 JSON do TSE (~8 min, fica em cache/)
python analise.py               # gera ANALISE.md e saidas/*.csv
```

Variações úteis:

```bash
python extrair_presidente.py --ufs ac,sp   # só alguns estados
python extrair_presidente.py --turnos 2    # só o 2º turno
python extrair_presidente.py --force       # rebaixa ignorando o cache
```

## Estrutura

```
extrair_presidente.py   extrator (JSON do TSE -> CSV + SQLite)
analise.py              análise das 3 perguntas -> ANALISE.md + saidas/
ANALISE.md              relatório gerado (não editar à mão: é sobrescrito)
saidas/
  consolidado_municipios_t1_t2.csv   5.571 linhas, 1 por município
  cidades_com_virada.csv             212 linhas (as que viraram de lado)
  uf_delta.csv                       deltas por UF
cache/                  JSON bruto do TSE (gitignored)
dados/                  votos_presidente_2026.csv/.db (gitignored)
```

## Dicionário de dados

`dados/votos_presidente_2026.csv` (15 MB, 80.598 linhas, UTF-8 com BOM) e a tabela `votos` no
SQLite têm as mesmas colunas:

| Coluna | Conteúdo |
|---|---|
| `turno` | 1 ou 2 |
| `uf` | sigla da UF; `zz` = voto no exterior |
| `cd_municipio` | código TSE de 5 dígitos (**não** é o código IBGE) |
| `cd_ibge`, `municipio` | código IBGE e nome |
| `cargo`, `cd_cargo` | "Presidente", 1 |
| `nr_candidato`, `sq_candidato`, `nome_candidato`, `nome_urna` | identificação do candidato |
| `partido`, `coligacao` | sigla do partido; coligação (vazio se o partido concorreu isolado) |
| `votos` | votos nominais no município |
| `pct_municipio` | % dentro do município (não do estado nem do país) |
| `status`, `eleito` | `Eleito` / `2º turno` / `Não eleito`; flag S/N derivada de `status` |
| `secoes_total`, `secoes_apuradas`, `pct_secoes` | progresso da apuração no município |
| `eleitorado`, `eleitorado_apurado` | eleitorado apto e apurado |
| `votos_total`, `votos_validos`, `votos_brancos`, `votos_nulos` | comparecimento e composição |
| `apuracao_encerrada`, `gerado_em` | `and` do TSE e data/hora de geração do arquivo |

## Armadilhas que o código já trata

1. **`eleito` vem de `status`, não do campo `e`.** No JSON do TSE, `e = "s"` significa "não
   eliminado" — quem vai a 2º turno também vem com `"s"`. Usar `e` marcaria dois candidatos
   como eleitos no 1º turno.
2. **`pct_municipio` chega como string com vírgula** (`"66,57"`). `float()` direto devolve
   `NaN` sem erro; o extrator converte certo e guarda o campo `pvapn` como referência.
3. **`uf = 'zz'` é voto no exterior** (186 postos). Fica fora das comparações municipais,
   senão a abstenção de 58% distorce médias.
4. **A soma dos municípios é a única via para o total nacional** — não existe arquivo "Brasil
   por município" para Presidente. Os arquivos de UF são agregados.

## Validação

- Soma dos municípios conferida contra os arquivos oficiais do TSE para **Brasil + 27 UFs +
  exterior, nos dois turnos** (54 conferências): **diferença zero** em todos os candidatos.
- 0 linhas sem votos, 0 seções pendentes, 0 duplicatas de candidato/município/turno.
- `pct_municipio` soma ~100% por município (variação de ±0,02 no 1º turno é arredondamento do
  próprio TSE).

## Limitações

Tudo é agregado por município: o delta de votos **não** é transferência de voto entre turnos
(falácia ecológica). O delta mistura migração de voto, variação de comparecimento e de
brancos/nulos. Detalhes na seção 5 de [ANALISE.md](ANALISE.md).

## Fonte

```
https://resultados.tse.jus.br/oficial/comum/config/ele-c.json                     # catálogo de eleições
https://resultados.tse.jus.br/oficial/ele2026/6257/config/mun-e006257-cm.json     # municípios
https://resultados.tse.jus.br/oficial/ele2026/{6257|6258}/dados/{uf}/{uf}{cd}-c0001-e00{6257|6258}-u.json
```

Códigos de eleição: **6257** = Presidente 1º turno, **6258** = Presidente 2º turno.

Esses endpoints não são documentados nem versionados pelo TSE. Para dados com contrato, o
caminho é o Portal de Dados Abertos: <https://dadosabertos.tse.jus.br/dataset/resultados-2026>.

Licença dos dados: CC-BY (Portal de Dados Abertos do TSE). Este repositório é análise
independente, sem vínculo com o TSE.
