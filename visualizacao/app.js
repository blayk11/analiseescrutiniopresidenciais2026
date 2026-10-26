'use strict';
/* Drill-down da base hierárquica: só monta no DOM o que está aberto. */
(function () {
  const { cols, rows } = window.HIER;

  const D = rows.map((r) => {
    const o = {};
    cols.forEach((c, i) => { o[c] = r[i]; });
    return o;
  });

  const NOME_NIVEL = {
    PAIS: 'Brasil',
    MACRORREGIAO: 'Macrorregião',
    ESTADO: 'Estado',
    REGIAO_INTERMEDIARIA: 'Reg. intermediária',
    MUNICIPIO: 'Município',
    EXTERIOR: 'Exterior',
  };
  const RECUO = {
    PAIS: 0, MACRORREGIAO: 0, EXTERIOR: 0, ESTADO: 1, REGIAO_INTERMEDIARIA: 2, MUNICIPIO: 3,
  };

  const nf = new Intl.NumberFormat('pt-BR');
  const nf2 = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtN = (v) => (v === '' || v === null || v === undefined) ? '—' : nf.format(v);
  const fmtP = (v) => (v === '' || v === null || v === undefined) ? '—' : nf2.format(v) + '%';
  const normal = (s) => String(s).normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

  // ---------------------------------------------------------------- árvore
  const pai = new Array(D.length).fill(null);
  const filhos = Array.from({ length: D.length }, () => []);
  const mapa = new Map();
  D.forEach((d, i) => { if (d.esfera === 'PAIS') mapa.set('PAIS', i); });

  D.forEach((d, i) => {
    let p = null;
    if (d.esfera === 'MACRORREGIAO' || d.esfera === 'EXTERIOR') p = mapa.get('PAIS');
    else if (d.esfera === 'ESTADO') p = mapa.get('M:' + d.macrorregiao);
    else if (d.esfera === 'REGIAO_INTERMEDIARIA') p = mapa.get('U:' + d.uf);
    else if (d.esfera === 'MUNICIPIO') p = mapa.get('R:' + d.cod_regiao_intermediaria);
    pai[i] = (p === undefined) ? null : p;
    if (pai[i] !== null) filhos[pai[i]].push(i);

    if (d.esfera === 'MACRORREGIAO') mapa.set('M:' + d.macrorregiao, i);
    if (d.esfera === 'ESTADO') mapa.set('U:' + d.uf, i);
    if (d.esfera === 'REGIAO_INTERMEDIARIA') mapa.set('R:' + d.cod_regiao_intermediaria, i);
  });

  filhos.forEach((lista) => lista.sort((a, b) =>
    (D[b].validos_2t || 0) - (D[a].validos_2t || 0) ||
    D[a].nome_localidade.localeCompare(D[b].nome_localidade, 'pt-BR')));

  const PAIS = D.findIndex((d) => d.esfera === 'PAIS');

  function ehDescendente(id, ancestral) {
    let p = pai[id];
    while (p !== null && p !== undefined) {
      if (p === ancestral) return true;
      p = pai[p];
    }
    return false;
  }

  // ---------------------------------------------------------------- DOM
  const corpo = document.getElementById('corpo');
  const statusEl = document.getElementById('status');
  const busca = document.getElementById('busca');
  const trs = new Map();
  const aberto = new Set();

  function status(extra) {
    statusEl.textContent = extra !== undefined
      ? extra + ' resultado(s) — busca ativa'
      : trs.size + ' de ' + D.length + ' linhas visíveis';
  }

  function celula(texto, classe, titulo) {
    const td = document.createElement('td');
    if (classe) td.className = classe;
    if (titulo) td.title = titulo;
    td.textContent = texto;
    return td;
  }

  function criarTr(i, plano) {
    const d = D[i];
    const tr = document.createElement('tr');
    tr.dataset.id = i;
    tr.className = 'nivel-' + d.esfera.toLowerCase().replace(/_/g, '-');

    const tdNome = document.createElement('td');
    tdNome.className = 'col-nome';

    if (!plano && filhos[i].length) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'careta';
      b.textContent = aberto.has(i) ? '▾' : '▸';
      b.addEventListener('click', () => alternar(i));
      tdNome.appendChild(b);
    } else if (!plano) {
      const vazio = document.createElement('span');
      vazio.className = 'careta-vazia';
      tdNome.appendChild(vazio);
    }

    const nome = document.createElement('span');
    nome.style.paddingLeft = ((RECUO[d.esfera] || 0) * 12) + 'px';
    nome.textContent = d.nome_localidade;
    tdNome.appendChild(nome);
    tr.appendChild(tdNome);

    tr.appendChild(celula(NOME_NIVEL[d.esfera] || d.esfera, 'nivel-tag'));
    tr.appendChild(celula(fmtN(d.eleitores_aptos_2t), 'num', 'eleitores aptos no 2º turno'));
    tr.appendChild(celula(fmtP(d.pct_comparecimento_2t), 'num', 'comparecimento / aptos'));
    tr.appendChild(celula(fmtP(d.pct_abstencao_2t), 'num', 'abstenção / aptos'));
    tr.appendChild(celula(fmtP(d.pct_brancos_2t), 'num', 'brancos / comparecimento'));
    tr.appendChild(celula(fmtP(d.pct_nulos_2t), 'num', 'nulos / comparecimento'));

    tr.appendChild(celula(fmtN(d.lula_1t), 'num lula'));
    tr.appendChild(celula(fmtP(d.pct_lula_1t), 'num lula', '% dos válidos no 1º turno'));
    tr.appendChild(celula(fmtN(d.flavio_1t), 'num flavio'));
    tr.appendChild(celula(fmtP(d.pct_flavio_1t), 'num flavio', '% dos válidos no 1º turno'));
    tr.appendChild(celula(fmtN(d.lula_2t), 'num lula'));
    tr.appendChild(celula(fmtP(d.pct_lula_2t), 'num lula', '% dos válidos no 2º turno'));
    tr.appendChild(celula(fmtN(d.flavio_2t), 'num flavio'));
    tr.appendChild(celula(fmtP(d.pct_flavio_2t), 'num flavio', '% dos válidos no 2º turno'));

    const noEstado = d.esfera === 'MUNICIPIO' || d.esfera === 'REGIAO_INTERMEDIARIA';
    tr.appendChild(celula(
      fmtP(noEstado ? d.pct_no_estado : d.pct_no_brasil),
      'num',
      noEstado ? '% dos válidos do estado' : '% dos válidos do Brasil'
    ));

    const curto = (v) => v === 'LULA' ? 'Lula' : (v === 'FLÁVIO BOLSONARO' ? 'Flávio' : 'Empate');
    tr.appendChild(celula(curto(d.vencedor_1t), 'venc v-' + (d.vencedor_1t === 'LULA' ? 'lula' : (d.vencedor_1t === 'FLÁVIO BOLSONARO' ? 'flavio' : 'empate'))));
    tr.appendChild(celula(curto(d.vencedor_2t), 'venc v-' + (d.vencedor_2t === 'LULA' ? 'lula' : (d.vencedor_2t === 'FLÁVIO BOLSONARO' ? 'flavio' : 'empate'))));

    if (d.houve_virada === 'SIM') {
      const td = document.createElement('td');
      const span = document.createElement('span');
      span.className = 'badge sim';
      span.textContent = 'SIM';
      td.title = 'margem no 2º turno: ' + fmtN(d.saldo_virada) + ' votos';
      td.appendChild(span);
      tr.appendChild(td);
    } else {
      tr.appendChild(celula('—', 'virada-nao'));
    }

    return tr;
  }

  function alternar(i) {
    const el = trs.get(i);
    if (!el) return;

    if (aberto.has(i)) {
      aberto.delete(i);
      let n = el.nextElementSibling;
      while (n && ehDescendente(Number(n.dataset.id), i)) {
        const prox = n.nextElementSibling;
        const id = Number(n.dataset.id);
        trs.delete(id);
        aberto.delete(id);
        n.remove();
        n = prox;
      }
    } else {
      aberto.add(i);
      let ponto = el;
      while (ponto.nextElementSibling && ehDescendente(Number(ponto.nextElementSibling.dataset.id), i)) {
        ponto = ponto.nextElementSibling;
      }
      for (const c of filhos[i]) {
        const tr = criarTr(c);
        ponto.after(tr);
        ponto = tr;
        trs.set(c, tr);
      }
    }
    const seta = el.querySelector('.careta');
    if (seta) seta.textContent = aberto.has(i) ? '▾' : '▸';
    status();
  }

  function recolher() {
    corpo.textContent = '';
    trs.clear();
    aberto.clear();
    const tr = criarTr(PAIS);
    corpo.appendChild(tr);
    trs.set(PAIS, tr);
    status();
  }

  function expandirTudo() {
    corpo.textContent = '';
    trs.clear();
    aberto.clear();
    const frag = document.createDocumentFragment();
    (function rec(i) {
      aberto.add(i);
      const tr = criarTr(i);
      frag.appendChild(tr);
      trs.set(i, tr);
      for (const c of filhos[i]) rec(c);
    })(PAIS);
    corpo.appendChild(frag);
    status();
  }

  // ---------------------------------------------------------------- busca
  busca.addEventListener('input', () => {
    const q = normal(busca.value.trim());
    if (q.length < 2) { recolher(); alternar(PAIS); return; }

    const achados = [];
    for (let i = 0; i < D.length && achados.length < 600; i++) {
      const d = D[i];
      if (d.esfera === 'MUNICIPIO' || d.esfera === 'REGIAO_INTERMEDIARIA') {
        if (normal(d.nome_localidade).includes(q)) achados.push(i);
      } else if (d.esfera === 'ESTADO' || d.esfera === 'MACRORREGIAO' || d.esfera === 'EXTERIOR') {
        if (normal(d.nome_localidade).includes(q)) achados.push(i);
      }
    }
    achados.sort((a, b) => (D[b].validos_2t || 0) - (D[a].validos_2t || 0));

    corpo.textContent = '';
    trs.clear();
    aberto.clear();
    const frag = document.createDocumentFragment();
    for (const i of achados) {
      const tr = criarTr(i, true);
      frag.appendChild(tr);
      trs.set(i, tr);
    }
    corpo.appendChild(frag);
    status(achados.length);
  });

  document.getElementById('btn-expandir').addEventListener('click', expandirTudo);
  document.getElementById('btn-recolher').addEventListener('click', () => {
    busca.value = '';
    recolher();
  });

  recolher();
  alternar(PAIS);
})();
