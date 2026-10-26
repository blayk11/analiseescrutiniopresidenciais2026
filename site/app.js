'use strict';
/* Escrutínio 2026 — drill-down hierárquico com lista virtualizada. */
(function () {
  const { cols, rows } = window.DADOS;
  const D = rows.map((r) => {
    const o = {};
    cols.forEach((c, i) => { o[c] = r[i]; });
    return o;
  });

  const ALTURA = 128;                 // altura de cada card (igual ao CSS)
  const NIVEIS = {
    PAIS: 'Brasil',
    MACRORREGIAO: 'Macrorregião',
    ESTADO: 'Estado',
    REGIAO_INTERMEDIARIA: 'Região intermediária',
    MUNICIPIO: 'Município',
    EXTERIOR: 'Exterior',
  };

  const nf = new Intl.NumberFormat('pt-BR');
  const nf1 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const nf2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const num = (v) => (v === '' || v === null || v === undefined) ? '—' : nf.format(v);
  const pct = (v) => (v === '' || v === null || v === undefined) ? '—' : nf1.format(v) + '%';
  const pp = (v) => (v === '' || v === null || v === undefined) ? '—'
    : (v > 0 ? '+' : '') + nf1.format(v) + ' p.p.';
  const normal = (s) => String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const esc = (s) => String(s === null || s === undefined ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

  // ---------------------------------------------------------------- árvore
  const filhos = D.map(() => []);
  D.forEach((d) => { if (d.pai !== null && d.pai !== undefined && d.pai !== '') filhos[d.pai].push(d.indice); });
  filhos.forEach((lista) => lista.sort((a, b) => {
    if (D[a].esfera === 'EXTERIOR') return 1;
    if (D[b].esfera === 'EXTERIOR') return -1;
    return (D[b].validos_2t || 0) - (D[a].validos_2t || 0);
  }));

  const RAIZ = D.find((d) => d.esfera === 'PAIS').indice;
  const caminho = (i) => {
    const trilha = [];
    let p = i;
    while (p !== null && p !== undefined && p !== '') { trilha.unshift(p); p = D[p].pai; }
    return trilha;
  };

  // ---------------------------------------------------------------- DOM
  const el = {
    voltar: document.getElementById('voltar'),
    limpar: document.getElementById('limpar'),
    migalhas: document.getElementById('migalhas'),
    busca: document.getElementById('busca'),
    contagem: document.getElementById('contagem'),
    hero: document.getElementById('hero'),
    trilho: document.getElementById('trilho'),
    fundo: document.getElementById('fundo'),
    sheet: document.getElementById('sheet'),
    sheetTitulo: document.getElementById('sheet-titulo'),
    sheetNivel: document.getElementById('sheet-nivel'),
    sheetCorpo: document.getElementById('sheet-corpo'),
    fechar: document.getElementById('fechar'),
    infoBtn: document.getElementById('info-btn'),
  };

  // atalho: em um estado, ver todos os municípios sem passar pelas regiões
  const municipiosPorUf = {};
  D.forEach((d) => {
    if (d.esfera === 'MUNICIPIO') (municipiosPorUf[d.uf] = municipiosPorUf[d.uf] || []).push(d.indice);
  });
  Object.values(municipiosPorUf).forEach((lista) =>
    lista.sort((a, b) => (D[b].validos_2t || 0) - (D[a].validos_2t || 0)));

  let atual = RAIZ;
  let pilha = [RAIZ];
  let itens = [];
  let buscando = '';
  let modoMunicipios = false;
  const montados = new Map();
  let rafPendente = false;

  // ---------------------------------------------------------------- formatação de card
  function segmentos(d) {
    const total = d.comparecimento_2t || 0;
    if (!total) return '';
    const partes = [
      ['s-lula', d.lula_2t],
      ['s-flavio', d.flavio_2t],
      ['s-brancos', d.brancos_2t],
      ['s-nulos', d.nulos_2t],
    ];
    return partes.map(([cls, v]) =>
      `<i class="${cls}" style="width:${(Math.max(0, (v || 0)) / total * 100).toFixed(2)}%"></i>`).join('');
  }

  function cardHTML(d) {
    const virada = d.houve_virada === 'SIM';
    const local = d.esfera === 'MUNICIPIO'
      ? `${d.uf} · ${d.regiao_intermediaria || ''}`
      : d.esfera === 'REGIAO_INTERMEDIARIA'
        ? `${d.uf} · ${d.macrorregiao}`
        : d.esfera === 'ESTADO'
          ? d.macrorregiao
          : d.esfera === 'EXTERIOR' ? 'Fora do Brasil' : 'Brasil';

    const tagHist = d.perfil_historico
      ? `<span class="badge neutro" style="font-size:9.5px;padding:1px 6px">${esc(d.perfil_historico)}</span>`
      : '';
    const swing2226 = (d.swing_22_26 !== null && d.swing_22_26 !== undefined)
      ? `<span class="hist-swing" title="Swing 2022→2026 (PT/Lula)" style="color:var(--fraco);font-size:11px">sw 22→26: <b>${pp(d.swing_22_26)}</b></span>`
      : '';

    return `
      <div class="card-topo">
        <div>
          <div class="card-nome">${esc(d.nome_localidade)}</div>
          <div class="card-meta">${esc(local)}${d.eleitores_aptos_2t ? ' · ' + num(d.eleitores_aptos_2t) + ' eleitores' : ''}</div>
        </div>
        <div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap;justify-content:flex-end">
          ${tagHist}
          <span class="badge ${virada ? 'virada' : 'sem-virada'}">${virada ? 'VIRADA' : 'SEM VIRADA'}</span>
        </div>
      </div>
      <div class="barra-votos" role="img" aria-label="Lula ${pct(d.pct_lula_2t)}, Flávio ${pct(d.pct_flavio_2t)}">
        ${segmentos(d)}
      </div>
      <div class="card-nums">
        <span class="lula">Lula ${pct(d.pct_lula_2t)}</span>
        <span class="flavio">Flávio ${pct(d.pct_flavio_2t)}</span>
        ${swing2226}
        <span class="abst">abst. ${pct(d.pct_abstencao_2t)}</span>
        <span class="chev">›</span>
      </div>`;
  }

  function criarCard(i, pos) {
    const d = D[i];
    const card = document.createElement('article');
    card.className = 'card';
    card.style.top = (pos * ALTURA + 4) + 'px';
    card.dataset.indice = i;
    card.innerHTML = cardHTML(d);
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.addEventListener('click', () => abrir(i));
    card.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); abrir(i); } });
    return card;
  }

  // ---------------------------------------------------------------- lista virtual
  function definirLista(lista) {
    itens = lista;
    el.trilho.style.height = (lista.length * ALTURA) + 'px';
    el.trilho.textContent = '';
    montados.clear();
    el.contagem.textContent = lista.length ? (buscando ? lista.length + ' resultado(s)' : lista.length + ' itens') : '';
    atualizarJanela();
  }

  function atualizarJanela() {
    if (!itens.length) return;
    const topo = el.trilho.getBoundingClientRect().top;
    const alturaJanela = window.innerHeight;
    const inicio = Math.max(0, Math.floor((-topo) / ALTURA) - 4);
    const fim = Math.min(itens.length, Math.ceil((alturaJanela - topo) / ALTURA) + 4);

    for (const [i, node] of montados) {
      if (i < inicio || i > fim) { node.remove(); montados.delete(i); }
    }
    for (let k = inicio; k < fim; k++) {
      if (montados.has(k)) continue;
      const node = criarCard(itens[k], k);
      el.trilho.appendChild(node);
      montados.set(k, node);
    }
  }

  function agendarJanela() {
    if (rafPendente) return;
    rafPendente = true;
    requestAnimationFrame(() => { rafPendente = false; atualizarJanela(); });
  }

  window.addEventListener('scroll', agendarJanela, { passive: true });
  window.addEventListener('resize', agendarJanela);

  // ---------------------------------------------------------------- hero
  function heroHTML(d) {
    const virada = d.houve_virada === 'SIM';
    const filhosN = filhos[d.indice].length;
    const nivel = NIVEIS[d.esfera] || d.esfera;
    const sub = d.esfera === 'MUNICIPIO'
      ? `${d.uf} · ${d.regiao_intermediaria || ''} · ${d.cod_ibge || ''}`
      : d.esfera === 'REGIAO_INTERMEDIARIA'
        ? `${d.uf} · ${d.macrorregiao}`
        : d.esfera === 'ESTADO'
          ? d.macrorregiao
          : d.esfera === 'EXTERIOR' ? 'Voto no exterior' : 'Consolidado nacional';

    const kpis = d.esfera === 'MUNICIPIO'
      ? [
          ['Eleitores', num(d.eleitores_aptos_2t)],
          ['Comparecimento', pct(d.pct_comparecimento_2t)],
          ['Abstenção', pct(d.pct_abstencao_2t)],
          ['Brancos / nulos', pct((d.pct_brancos_2t || 0) + (d.pct_nulos_2t || 0))],
          ['Lula 2ºT', pct(d.pct_lula_2t)],
          ['Flávio 2ºT', pct(d.pct_flavio_2t)],
        ]
      : [
          ['Eleitores', num(d.eleitores_aptos_2t)],
          ['Comparecimento', pct(d.pct_comparecimento_2t)],
          ['Viradas', num(d.n_viradas)],
          ['Subdivisões', num(filhosN)],
          ['Lula 2ºT', pct(d.pct_lula_2t)],
          ['Flávio 2ºT', pct(d.pct_flavio_2t)],
        ];

    return `
      <h2>${esc(d.nome_localidade)}</h2>
      <div class="sub">${esc(nivel)} · ${esc(sub)}</div>
      <span class="badge ${virada ? 'virada' : 'sem-virada'}">${virada ? 'VIROU NO 2º TURNO' : 'NÃO VIROU'}</span>
      <span class="badge neutro">margem ${num(d.saldo_virada)}</span>
      <div class="barra-votos" style="margin-top:10px">${segmentos(d)}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;margin-top:8px">
        ${d.perfil_historico
          ? `<span class="badge ok" style="font-size:11px">Histórico: <b>${esc(d.perfil_historico)}</b></span>
             <span class="badge neutro" style="font-size:11px">Swing 18→22: <b>${pp(d.swing_18_22)}</b></span>
             <span class="badge neutro" style="font-size:11px">Swing 22→26: <b>${pp(d.swing_22_26)}</b></span>`
          : (d.pct_pt_2018 !== undefined && d.pct_pt_2018 !== null
            ? `<span class="badge neutro" style="font-size:11px">2018: PT ${pct(d.pct_pt_2018)} × Polo B ${pct(d.pct_polo_b_2018)}</span>
               <span class="badge neutro" style="font-size:11px">2022: PT ${pct(d.pct_pt_2022)} × Polo B ${pct(d.pct_polo_b_2022)}</span>
               <span class="badge neutro" style="font-size:11px">Swing 22→26: <b>${pp(d.swing_22_26)}</b></span>`
            : '')}
      </div>
      <div class="hero-grid">
        ${kpis.map(([k, v]) => `<div><b>${v}</b><span>${k}</span></div>`).join('')}
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
        <button class="migalha" type="button" data-parecer="1" style="font-weight:600">📊 Ver parecer estatístico & histórico 2018/2022</button>
        ${d.esfera === 'ESTADO'
          ? `<button class="migalha" type="button" data-municipios="1">${modoMunicipios
              ? 'Ver regiões geográficas'
              : `Ver todos os ${num((municipiosPorUf[d.uf] || []).length)} municípios`}</button>`
          : ''}
      </div>`;
  }

  function renderHero() {
    el.hero.innerHTML = heroHTML(D[atual]);
  }

  el.hero.addEventListener('click', (ev) => {
    if (!ev.target || !ev.target.closest) return;
    if (ev.target.closest('[data-parecer]')) { abrirSheet(atual); return; }
    if (ev.target.closest('[data-municipios]')) { modoMunicipios = !modoMunicipios; render(); }
  });

  // ---------------------------------------------------------------- navegação
  function render() {
    const trilha = caminho(atual);
    el.migalhas.innerHTML = trilha.map((i, pos) => `
      <button class="migalha" type="button" data-ir="${i}"
        aria-current="${pos === trilha.length - 1}">${esc(D[i].nome_localidade)}</button>`).join('');
    el.migalhas.scrollLeft = el.migalhas.scrollWidth;

    el.voltar.disabled = trilha.length <= 1 && !buscando;

    renderHero();

    const lista = buscando
      ? resultados
      : (modoMunicipios ? (municipiosPorUf[D[atual].uf] || []) : filhos[atual]);
    definirLista(lista);
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  function abrir(i) {
    if (filhos[i].length) {
      atual = i;
      pilha.push(i);
      buscando = '';
      modoMunicipios = false;
      el.busca.value = '';
      resultados = [];
      render();
    } else {
      abrirSheet(i);
    }
  }

  function irPara(i) {
    atual = i;
    pilha = caminho(i);
    modoMunicipios = false;
    buscando = '';
    el.busca.value = '';
    resultados = [];
    render();
  }

  el.voltar.addEventListener('click', () => {
    if (buscando) {
      buscando = '';
      el.busca.value = '';
      resultados = [];
      render();
      return;
    }
    if (modoMunicipios) { modoMunicipios = false; render(); return; }
    if (pilha.length > 1) { pilha.pop(); atual = pilha[pilha.length - 1]; render(); }
  });
  el.limpar.addEventListener('click', () => { pilha = [RAIZ]; irPara(RAIZ); });
  el.migalhas.addEventListener('click', (ev) => {
    const alvo = ev.target.closest('[data-ir]');
    if (!alvo) return;
    irPara(Number(alvo.dataset.ir));
  });

  // ---------------------------------------------------------------- busca
  let resultados = [];
  let timerBusca = null;
  el.busca.addEventListener('input', () => {
    clearTimeout(timerBusca);
    timerBusca = setTimeout(() => {
      const q = normal(el.busca.value.trim());
      if (q.length < 2) {
        buscando = '';
        resultados = [];
        render();
        return;
      }
      buscando = q;
      resultados = [];
      for (const d of D) {
        if (d.esfera === 'EXTERIOR') continue;
        const alvo = normal(d.nome_localidade);
        if (alvo.includes(q) || (d.esfera === 'ESTADO' && normal(d.uf) === q)) {
          resultados.push(d.indice);
          if (resultados.length >= 400) break;
        }
      }
      resultados.sort((a, b) => (D[b].validos_2t || 0) - (D[a].validos_2t || 0));
      render();
    }, 120);
  });

  // ---------------------------------------------------------------- sheet
  function badgeClasse(cls) {
    if (cls === 'Outlier estatístico') return 'out';
    if (cls === 'Variação notável') return 'warn';
    if (cls === 'Padrão esperado') return 'ok';
    return 'neutro';
  }

  function secaoDecomposicao(d) {
    const partes = [
      ['Crescimento do colégio válido', d.decomp_validos],
      ['Migração de terceiros', d.decomp_terceiros],
      ['Conversão direta (perda do adversário)', d.decomp_adversario],
    ];
    const vals = partes.map(([, v]) => Number(v) || 0);
    if (!vals.some((v) => v !== 0)) return '';
    const max = Math.max(...vals.map((v) => Math.abs(v)), 1);
    const barras = partes.map(([rotulo, v], i) => {
      const valor = vals[i];
      const largura = Math.abs(valor) / max * 50;
      const esquerda = valor >= 0 ? 50 : 50 - largura;
      const cor = valor >= 0 ? 'var(--ok)' : 'var(--out)';
      return `
        <div class="decomp-item">
          <div class="decomp-rotulo"><span>${rotulo}</span><b>${valor > 0 ? '+' : ''}${num(valor)}</b></div>
          <div class="decomp-trilho">
            <span class="decomp-centro"></span>
            <span class="decomp-barra" style="left:${esquerda}%;width:${largura}%;background:${cor};opacity:.75"></span>
          </div>
        </div>`;
    }).join('');
    return `
      <div class="bloco">
        <h3>De onde veio o ganho do vencedor</h3>
        <div class="decomp">${barras}</div>
        <p class="paragrafo">
          Fator dominante: <b>${esc(d.motor_dominante || '—')}</b>
          ${d.motor_share !== null && d.motor_share !== undefined
            ? `(${nf1.format(d.motor_share)}% do ganho em valor absoluto)` : ''}.
          Identidade contábil: <b>ΔW = ΔV − P − ΔL</b>, sem estimativa de modelo.
        </p>
      </div>`;
  }

  function secaoHistorico(d) {
    // Calcular percentuais do Polo B (PSL 2018 / PL 2022) via margem e PT
    const poloB_2018 = (d.pct_pt_2018 !== undefined && d.pct_pt_2018 !== null && d.margem_2018 !== undefined && d.margem_2018 !== null)
      ? (d.vencedor_2018 === 'B' ? d.pct_pt_2018 + d.margem_2018 : Math.max(0, d.pct_pt_2018 - d.margem_2018))
      : null;
    const poloB_2022 = (d.pct_pt_2022 !== undefined && d.pct_pt_2022 !== null && d.margem_2022 !== undefined && d.margem_2022 !== null)
      ? (d.vencedor_2022 === 'B' ? d.pct_pt_2022 + d.margem_2022 : Math.max(0, d.pct_pt_2022 - d.margem_2022))
      : null;

    const linhas = [
      ['2018 (1ºT)', d.pct_pt_2018, poloB_2018, d.margem_2018, d.vencedor_2018],
      ['2022 (1ºT)', d.pct_pt_2022, poloB_2022, d.margem_2022, d.vencedor_2022],
      ['2026 (1ºT)', d.pct_lula_1t, d.pct_flavio_1t, d.margem_2026, d.vencedor_2026],
      ['2026 (2ºT)', d.pct_lula_2t, d.pct_flavio_2t, Math.abs((d.pct_lula_2t || 0) - (d.pct_flavio_2t || 0)), d.pct_lula_2t >= d.pct_flavio_2t ? 'A' : 'B'],
    ];
    const corpo = linhas.map(([ano, a, b, m, v]) => `
      <tr>
        <td>${ano}</td>
        <td class="a">${pct(a)}</td>
        <td class="b">${pct(b)}</td>
        <td>${m === null || m === undefined ? '—' : nf1.format(m) + ' p.p.'}</td>
        <td>${v === 'A' ? 'Polo A' : v === 'B' ? 'Polo B' : '—'}</td>
      </tr>`).join('');
    const semHist = d.perfil_historico === 'Sem histórico completo'
      ? '<p class="paragrafo">Município criado depois de 2022 ou sem dados comparáveis — perfil histórico não calculado.</p>'
      : '';
    return `
      <div class="bloco">
        <h3>Histórico presidencial (1º turno)</h3>
        <table class="hist">
          <thead><tr><th>Eleição</th><th>Polo A (PT)</th><th>Polo B (Bolsonaro)</th><th>Margem</th><th>Vencedor</th></tr></thead>
          <tbody>${corpo}</tbody>
        </table>
        ${semHist}
        <p class="paragrafo">
          Perfil: <b>${esc(d.perfil_historico || '—')}</b>.
          Swing 2018→2022: <b>${pp(d.swing_18_22)}</b> ·
          Swing 2022→2026: <b>${pp(d.swing_22_26)}</b>.
        </p>
      </div>`;
  }

  function secaoEstatistica(d) {
    const cls = d.classificacao_z;
    const temZ = d.z_delta_ri !== null && d.z_delta_ri !== undefined
      ? { z: d.z_delta_ri, base: 'região intermediária', media: d.media_delta_ri, sd: d.sd_delta_ri, n: d.n_ri }
      : (d.z_delta_br !== null && d.z_delta_br !== undefined
        ? { z: d.z_delta_br, base: 'Brasil', media: null, sd: null, n: null }
        : null);

    if (!temZ) {
      return `
        <div class="bloco">
          <h3>Comportamento regional</h3>
          <p class="paragrafo">Sem base estatística suficiente para calcular z-score nesta localidade.</p>
        </div>`;
    }

    const zTxt = (temZ.z > 0 ? '+' : '') + nf2.format(temZ.z);
    const contexto = temZ.sd
      ? `média da base ${nf1.format(temZ.media)} p.p., σ ${nf2.format(temZ.sd)} p.p., n = ${num(temZ.n)}`
      : 'desvio calculado sobre todos os municípios';

    return `
      <div class="bloco">
        <h3>Comportamento regional</h3>
        <div class="linha-par">
          <span class="badge ${badgeClasse(cls)}">${esc(cls || '—')}</span>
          <span class="badge neutro">|z| = ${nf2.format(Math.abs(temZ.z))}</span>
          <span class="badge neutro">base: ${temZ.base}</span>
        </div>
        <p class="paragrafo">
          A variação de Lula do 1º para o 2º turno foi de <b>${pp(d.delta_pp)}</b>.
          Contra a ${temZ.base} (${contexto}), isso dá <b>z = ${zTxt}</b>.
          Limiares: |z| ≤ 1,5 padrão esperado · ≤ 2,5 variação notável · > 2,5 outlier.
        </p>
      </div>`;
  }

  function secaoAgregado(d) {
    const total = (d.n_consistente_a || 0) + (d.n_consistente_b || 0) + (d.n_inclinado_a || 0) +
      (d.n_inclinado_b || 0) + (d.n_pendulo || 0) + (d.n_sem_historico || 0);
    if (!total) return '';
    return `
      <div class="bloco">
        <h3>Perfil dos municípios desta esfera</h3>
        <div class="kpis">
          <div class="kpi"><b>${num(d.n_consistente_a)}</b><span>Consistente Polo A</span></div>
          <div class="kpi"><b>${num(d.n_consistente_b)}</b><span>Consistente Polo B</span></div>
          <div class="kpi"><b>${num(d.n_pendulo)}</b><span>Pêndulo</span></div>
          <div class="kpi"><b>${num(d.n_outliers)}</b><span>Outliers estatísticos</span></div>
        </div>
        <p class="paragrafo">
          ${num(d.n_consistente_a + d.n_consistente_b)} municípios consistentes,
          ${num(d.n_inclinado_a + d.n_inclinado_b)} inclinados,
          ${num(d.n_pendulo)} pêndulos e ${num(d.n_sem_historico)} sem histórico completo.
          z médio: <b>${d.z_medio === null || d.z_medio === undefined ? '—' : nf2.format(d.z_medio)}</b>.
        </p>
      </div>`;
  }

  function parecerHTML(d) {
    const ehMunicipio = d.esfera === 'MUNICIPIO';
    const cls = d.classificacao_z;
    const resumo = ehMunicipio
      ? `Classificação histórica: <b>${esc(d.perfil_historico || '—')}</b> ·
         Swing 2018→2022: <b>${pp(d.swing_18_22)}</b> ·
         Comportamento regional: <b>${esc(cls || '—')}</b>
         ${d.z_delta_ri !== null && d.z_delta_ri !== undefined
           ? `(|z| = ${nf2.format(Math.abs(d.z_delta_ri))})` : ''}`
      : `${NIVEIS[d.esfera]} com ${num(filhos[d.indice].length)} subdivisões.`;

    const kpis = ehMunicipio
      ? `<div class="kpis">
           <div class="kpi"><b>${pp(d.delta_pp)}</b><span>Lula 1º→2º</span></div>
           <div class="kpi"><b>${pp(d.swing_22_26)}</b><span>Swing 2022→26</span></div>
           <div class="kpi"><b>${pp(d.delta_abst_pp)}</b><span>Δ abstenção</span></div>
           <div class="kpi"><b>${pp(d.swing_18_22)}</b><span>Swing 2018→22</span></div>
         </div>`
      : '';

    return `
      <div class="bloco">
        <p class="paragrafo" style="margin-top:0">${resumo}</p>
        ${kpis}
      </div>
      ${ehMunicipio ? secaoEstatistica(d) : secaoAgregado(d)}
      ${secaoDecomposicao(d)}
      ${secaoHistorico(d)}
      <div class="bloco">
        <div class="nota">
          <b>Como ler.</b> Tudo aqui é agregado: o delta de votos de um município não é
          transferência de voto entre eleitores (falácia ecológica). O delta mistura migração
          de voto, variação de comparecimento e de brancos/nulos. z-score compara o município
          com o desvio padrão da própria região intermediária — não é teste de fraude nem
          juízo político. Fonte: TSE.
        </div>
      </div>`;
  }

  
  function guiaHTML() {
    return `
      <div class="bloco">
        <h3>Guia Rápido: Como entender este aplicativo</h3>
        <p class="paragrafo">
          Este painel reúne e audita 100% dos dados oficiais da apuração para Presidente em 2026 (TSE)
          comparados aos ciclos de 2018 e 2022. Você pode navegar do Brasil até qualquer município.
        </p>
      </div>

      <div class="bloco">
        <h3>1. Navegação em Níveis (Drill-down)</h3>
        <p class="paragrafo">
          • <b>Hierarquia:</b> Começa no <b>Brasil</b> → clique em uma <b>Macrorregião</b> (ex: Sudeste) → escolha o <b>Estado</b> → veja as <b>Regiões Intermediárias</b> ou use o atalho <i>"Ver todos os municípios"</i>.<br>
          • <b>Migalhas (topo):</b> Toque em qualquer botão na linha superior para voltar diretamente àquele nível.<br>
          • <b>Busca:</b> Digite o nome de qualquer cidade, sigla de estado ou região para ir direto a ela.
        </p>
      </div>

      <div class="bloco">
        <h3>2. Por que o vencedor ganhou ~74% dos novos votos no 2º turno?</h3>
        <p class="paragrafo">
          À primeira vista, pode parecer contraintuitivo que quase 3 em cada 4 votos novos no 2º turno tenham ido para Lula. A matemática e o histórico eleitoral brasileiro explicam isso por 3 razões:<br>
          • <b>Teto do adversário:</b> Flávio Bolsonaro já atingiu 56,1 milhões de votos no 1º turno (sua base mais fiel e mobilizada). No 2º turno, cresceu +3,7 mi.<br>
          • <b>Rejeição ao bolsonarismo no eleitorado de terceiros:</b> Os candidatos de centro e terceira via (Cury, Renan, Caiado) somaram 9,3 milhões de votos. Grande parte desse público tinha alta rejeição ao Polo B e migrou para Lula no 2º turno.<br>
          • <b>Aumento de votantes válidos (+4,7 milhões):</b> Milhões de pessoas que votaram em branco, nulo ou faltaram no 1º turno compareceram no 2º turno, especialmente nas capitais e periferias do Sudeste e Sul, gerando a virada matemática.<br>
          <i>Precedente:</i> Em 2006, Lula ganhou 11,6 milhões de votos novos no 2º turno, enquanto Alckmin perdeu 2,4 milhões (Lula absorveu mais de 100% do saldo de crescimento).
        </p>
      </div>

      <div class="bloco">
        <h3>3. O que significam os termos e números</h3>
        <p class="paragrafo">
          • <b>Barra colorida nos cards:</b> Vermelho = Lula | Azul = Flávio Bolsonaro | Cinza claro = Votos Brancos | Cinza escuro = Votos Nulos.<br>
          • <b>VIRADA / NÃO VIROU:</b> Indica se o candidato que venceu no 1º turno perdeu no 2º turno naquela localidade.<br>
          • <b>p.p. (Pontos Percentuais):</b> É a diferença direta entre duas porcentagens. Exemplo: subir de 45% para 50% é um ganho de +5 p.p.<br>
          • <b>Swing (Balanço entre eleições):</b> Mudança percentual no voto de um polo político de uma eleição para a outra (ex: de 2022 para 2026).<br>
          • <b>Decomposição contábil (ΔW = ΔV − P − ΔL):</b> Mostra com precisão matemática de onde veio o ganho do vencedor: quanto veio do crescimento total de votantes válidos, quanto veio de eleitores de terceiros candidatos e quanto veio de perda direta de votos do adversário.
        </p>
      </div>

      <div class="bloco">
        <h3>4. Perfil Histórico (2018, 2022 e 2026) e Estatística</h3>
        <p class="paragrafo">
          • <b>Polo A (PT) / Polo B (PL/PSL):</b> Compara o comportamento histórico nos últimos 3 ciclos presidenciais (2018, 2022 e 2026).<br>
          • <b>Consistente:</b> Cidade onde o mesmo polo venceu todas as 3 eleições com folga (>10 p.p.).<br>
          • <b>Pêndulo:</b> Cidades que alternaram o polo vencedor entre os anos.<br>
          • <b>z-score (Desvio relativo à região):</b> Mede se a variação da cidade fugiu do padrão das cidades vizinhas da mesma região geográfica. <i>Não é teste de fraude nem acusação</i>, apenas um termômetro estatístico (|z| ≤ 1,5 é o padrão esperado; > 2,5 é um ponto fora da curva).
        </p>
      </div>

      <div class="bloco">
        <div class="nota">
          <b>Transparência total:</b> Todos os números são calculados diretamente das bases oficiais do TSE e IBGE por rotinas públicas e auditáveis. Nenhum valor é editado à mão.
        </div>
      </div>
    `;
  }

  function abrirGuia() {
    el.sheetTitulo.textContent = 'Como entender as informações';
    el.sheetNivel.textContent = 'Guia & Instruções de Uso';
    el.sheetCorpo.innerHTML = guiaHTML();
    el.sheetCorpo.scrollTop = 0;
    el.fundo.hidden = false;
    el.sheet.hidden = false;
    requestAnimationFrame(() => el.sheet.classList.add('aberto'));
    document.body.style.overflow = 'hidden';
  }

  function abrirSheet(i) {
    const d = D[i];
    el.sheetTitulo.textContent = d.nome_localidade;
    el.sheetNivel.textContent = (NIVEIS[d.esfera] || d.esfera) + (d.uf ? ' · ' + d.uf : '');
    el.sheetCorpo.innerHTML = parecerHTML(d);
    el.sheetCorpo.scrollTop = 0;
    el.fundo.hidden = false;
    el.sheet.hidden = false;
    requestAnimationFrame(() => el.sheet.classList.add('aberto'));
    document.body.style.overflow = 'hidden';
  }

  function fecharSheet() {
    el.sheet.classList.remove('aberto');
    el.fundo.hidden = true;
    document.body.style.overflow = '';
    setTimeout(() => { el.sheet.hidden = true; }, 260);
  }

  el.fechar.addEventListener('click', fecharSheet);
  if (el.infoBtn) el.infoBtn.addEventListener('click', abrirGuia);
  el.fundo.addEventListener('click', fecharSheet);
  document.addEventListener('keydown', (ev) => { if (ev.key === 'Escape') fecharSheet(); });

  // ---------------------------------------------------------------- início
  if (!D.length) {
    el.hero.innerHTML = '<p class="paragrafo">Falha ao carregar os dados (dados.js).</p>';
    return;
  }
  render();
})();
