# Análise de escrutínio — Presidente 2026 (1º → 2º turno)

Extração e análise **determinística** da votação para Presidente nas Eleições 2026, município
por município, a partir dos JSON públicos de `resultados.tse.jus.br`, mais uma **base
hierárquica** (Brasil → macrorregião → UF → região intermediária → município) pronta para
roll-up e drill-down. Nenhum número é digitado à mão: tudo sai dos scripts sobre os dados
oficiais do TSE.

Segundo turno: **LULA (PT, 13) × FLÁVIO BOLSONARO (PL, 22)**, apuração encerrada em 25/10/2026.

## Achados principais

Relatório completo das três perguntas de pesquisa: **[ANALISE.md](ANALISE.md)**.

| | |
|---|---|
| Placar nacional (com exterior) | Lula 53.879.538 → **64.256.232** (+10.376.694); Flávio 56.104.503 → **59.826.041** (+3.721.538) |
| Divisão do crescimento | **73,7%** dos votos novos nos dois candidatos foram para Lula |
| Viradas municipais | **212** de 5.571 (3,8%): 211 Flávio→Lula e **1** Lula→Flávio (Uirapuru/GO) |
| Maior virada | Rio de Janeiro/RJ — 4,95 mi de eleitores, era de Flávio no 1º turno por 137.837 votos |
| Região que virou | **Norte**: Flávio ganhava por 458.835 no 1º turno e perdeu por **1.079 votos** no 2º |
| Origem do ganho de Lula | 54,5% do saldo veio de municípios onde ele **perdeu** o 1º turno |
| Absorção dos terceiros | r = **−0,18** entre peso dos terceiros no 1º turno e captura por Lula |

O ponto metodológico central: o crescimento combinado dos dois candidatos (14,0 mi) é
**1,51× maior** que o pool de votos dados a terceiros no 1º turno (9,3 mi). Logo, o delta não
se explica por migração de voto de terceiros — boa parte vem de mudança de comparecimento e de
brancos/nulos.

## Base hierárquica (roll-up / drill-down)

`agregar_esferas.py` gera **uma tabela só**, com as mesmas colunas em todos os níveis. Cada
linha traz os absolutos somados das filhas e os percentuais recalculados sobre o denominador
correto daquele nível (nunca média de percentuais).

| Nível | Esfera | Linhas |
|---|---|---|
| 0 | `PAIS` | 1 |
| 1 | `MACRORREGIAO` (Norte, Nordeste, Sudeste, Sul, Centro-Oeste) | 5 |
| 2 | `ESTADO` | 27 |
| 3 | `REGIAO_INTERMEDIARIA` (IBGE) | 133 |
| 4 | `MUNICIPIO` | 5.571 |
| — | `EXTERIOR` (todos os postos no exterior em uma linha) | 1 |
| | **total** | **5.738** |

O `EXTERIOR` fica fora da malha do IBGE (não tem UF nem região), mas entra na soma do Brasil —
assim o nível `PAIS` bate exatamente com o total oficial do TSE.

Saídas:

- `saidas/base_hierarquica.csv` — 5.738 linhas × 47 colunas (UTF-8 com BOM)
- `dados/base_hierarquica.db` — tabela `esferas`, com índices por esfera e UF
- `visualizacao/dados.js` — mesmo conteúdo em JSON, para o viewer

### Ver no navegador

Abra **`visualizacao/index.html`** direto no navegador (funciona por `file://`, sem servidor).
Abre no Brasil; clique na seta para descer até o município. Tem busca por município, UF ou
região, e botões de expandir/recolher tudo. A tabela monta no DOM **só o que está aberto** —
expandir tudo são 5.738 linhas, e mesmo assim rola liso.

### Colunas da base

| Grupo | Colunas |
|---|---|
| Localização | `esfera`, `cod_ibge`, `nome_localidade`, `uf`, `macrorregiao`, `regiao_intermediaria`, `cod_regiao_intermediaria` |
| Engajamento | `eleitores_aptos_1t/2t`, `comparecimento_1t/2t`, `pct_comparecimento_1t/2t`, `pct_abstencao_1t/2t` |
| Inválidos | `brancos_1t/2t`, `nulos_1t/2t` e os `pct_*` sobre o comparecimento |
| Nominais | `lula_1t/2t`, `flavio_1t/2t` e os `pct_*` sobre os válidos |
| Terceiros | `outros_1t`, `cury_1t`, `renan_1t`, `caiado_1t` e os `pct_*` |
| Peso | `pct_no_estado` (município e região intermediária), `pct_no_brasil` |
| Virada | `vencedor_1t`, `vencedor_2t`, `houve_virada` (SIM/NÃO), `saldo_virada` (margem do 2º turno em votos) |

Exemplo de consulta:

```sql
-- % de Lula por macrorregião e o peso de cada uma
SELECT nome_localidade, pct_lula_2t AS pct_lula, pct_no_brasil AS peso,
       houve_virada, saldo_virada
FROM esferas WHERE esfera = 'MACRORREGIAO' ORDER BY validos_2t DESC;
```

## Como reproduzir

Só precisa de Python 3.10+ e da stdlib. Sem pandas, sem pip install.

```bash
python extrair_presidente.py    # baixa 11.514 JSON do TSE (~8 min, fica em cache/)
python agregar_esferas.py       # monta a base hierárquica (malha do IBGE)
python analise.py               # gera ANALISE.md e saidas/*.csv
python verificar.py             # checagem de integridade (sai 1 se algo divergir)
```

Variações úteis:

```bash
python extrair_presidente.py --ufs ac,sp   # só alguns estados
python extrair_presidente.py --turnos 2    # só o 2º turno
python extrair_presidente.py --force       # rebaixa ignorando o cache
node testes/teste_viewer.mjs               # testa o drill-down (DOM mínimo, sem dependências)
```

## Estrutura

```
extrair_presidente.py    JSON do TSE -> CSV + SQLite por município e turno
agregar_esferas.py       roll-up município -> região intermediária -> UF -> macrorregião -> Brasil
analise.py               três perguntas de pesquisa -> ANALISE.md
verificar.py             reconciliação e integridade -> código de saída
ANALISE.md               relatório gerado (não editar à mão: é sobrescrito)
saidas/
  base_hierarquica.csv                 5.738 linhas, todos os níveis
  consolidado_municipios_t1_t2.csv     5.571 municípios, T1 x T2
  cidades_com_virada.csv               212 municípios que viraram
  uf_delta.csv                         deltas por UF
visualizacao/
  index.html, app.js, style.css        drill-down (abre por file://)
  dados.js                             payload gerado por agregar_esferas.py
testes/teste_viewer.mjs                teste do drill-down
cache/                                 JSON bruto do TSE + malha do IBGE (gitignored)
dados/                                 CSV/SQLite gerados (gitignored)
```

## Dicionário de dados (votação por município)

`dados/votos_presidente_2026.csv` (80.598 linhas, UTF-8 com BOM) e a tabela `votos` no SQLite:

| Coluna | Conteúdo |
|---|---|
| `turno` | 1 ou 2 |
| `uf` | sigla da UF; `zz` = voto no exterior |
| `cd_municipio` | código TSE de 5 dígitos (**não** é o código IBGE) |
| `cd_ibge`, `municipio` | código IBGE e nome |
| `cargo`, `cd_cargo` | "Presidente", 1 |
| `nr_candidato`, `sq_candidato`, `nome_candidato`, `nome_urna` | identificação do candidato |
| `partido`, `coligacao` | sigla do partido; coligação (vazio se concorreu isolado) |
| `votos` | votos nominais no município |
| `pct_municipio` | % dentro do município (não do estado nem do país) |
| `status`, `eleito` | `Eleito` / `2º turno` / `Não eleito`; flag S/N derivada de `status` |
| `secoes_total`, `secoes_apuradas`, `pct_secoes` | progresso da apuração |
| `eleitorado`, `eleitorado_apurado` | eleitorado apto e apurado |
| `votos_total`, `votos_validos`, `votos_brancos`, `votos_nulos` | comparecimento e composição |
| `apuracao_encerrada`, `gerado_em` | `and` do TSE e data/hora de geração |

## Armadilhas que o código já trata

1. **`eleito` vem de `status`, não do campo `e`.** No JSON do TSE, `e = "s"` significa "não
   eliminado" — quem vai a 2º turno também vem com `"s"`. Usar `e` marcaria dois candidatos
   como eleitos no 1º turno.
2. **`pct_municipio` chega como string com vírgula** (`"66,57"`). `float()` direto devolve
   `NaN` sem erro; o extrator converte certo.
3. **`uf = 'zz'` é voto no exterior** (186 postos). `ANALISE.md` compara municípios e por isso
   exclui o exterior; a base hierárquica inclui o exterior como linha própria, para o Brasil
   fechar com o TSE.
4. **Não existe arquivo "Brasil por município"** para Presidente — o total nacional é a soma
   dos municípios. Os arquivos de UF são agregados.
5. **Região intermediária não vem do TSE.** O merge é pelo `cod_ibge` (7 dígitos) com a malha
   do IBGE; município novo que não exista lá aparece no aviso do script e fica fora da base.

## Validação

`python verificar.py` cobre:

- 5.757 unidades no TSE (5.571 municípios + 186 exterior), sem duplicata e sem voto nulo de dado.
- Contagem por esfera (1 / 5 / 27 / 133 / 5.571 / 1).
- **Reconciliação**: município + exterior = Brasil em todas as 15 colunas absolutas; UF = região
  intermediária = macrorregião, e (+exterior) = Brasil, nos dois turnos.
- `pct_no_estado` somando 100% em cada UF; `pct_no_brasil` das UFs + exterior = 100%.
- Todo município com macrorregião e região intermediária preenchidas.
- 212 municípios com virada.

Além disso, a soma dos municípios foi conferida contra os **arquivos oficiais do TSE para
Brasil + 27 UFs + exterior, nos dois turnos (54 conferências): diferença zero** em todos os
candidatos. E `node testes/teste_viewer.mjs` testa o drill-down (7 linhas iniciais, 5.738 ao
expandir tudo, busca e recolher).

## Limitações

Tudo é agregado por município: o delta de votos **não** é transferência de voto entre turnos
(falácia ecológica). O delta mistura migração de voto, variação de comparecimento e de
brancos/nulos. Detalhes na seção 5 de [ANALISE.md](ANALISE.md).

## Fonte

```
https://resultados.tse.jus.br/oficial/comum/config/ele-c.json                     # catálogo de eleições
https://resultados.tse.jus.br/oficial/ele2026/6257/config/mun-e006257-cm.json     # municípios
https://resultados.tse.jus.br/oficial/ele2026/{6257|6258}/dados/{uf}/{uf}{cd}-c0001-e00{6257|6258}-u.json
https://servicodados.ibge.gov.br/api/v1/localidades/estados/{id}/municipios       # malha do IBGE
```

Códigos de eleição: **6257** = Presidente 1º turno, **6258** = Presidente 2º turno.

Esses endpoints do TSE não são documentados nem versionados. Para dados com contrato, o caminho
é o Portal de Dados Abertos: <https://dadosabertos.tse.jus.br/dataset/resultados-2026>.

Licença dos dados: CC-BY (Portal de Dados Abertos do TSE). Este repositório é análise
independente, sem vínculo com o TSE.
