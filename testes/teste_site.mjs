// Teste do site/ com DOM mínimo em Node — sem dependências.
// Roda a partir da raiz do repositório: node testes/teste_site.mjs
import fs from 'node:fs';

class No {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.parent = null;
    this.dataset = {};
    this.attrs = {};
    this.className = '';
    this.style = {};
    this.title = '';
    this.value = '';
    this.disabled = false;
    this.hidden = false;
    this.tabIndex = 0;
    this.scrollLeft = 0;
    this.scrollWidth = 0;
    this.scrollTop = 0;
    this._text = '';
    this._html = '';
    this._l = {};
    this.classList = {
      add: (c) => { if (!this.className.split(' ').includes(c)) this.className = (this.className + ' ' + c).trim(); },
      remove: (c) => { this.className = this.className.split(' ').filter((x) => x !== c).join(' '); },
      contains: (c) => this.className.split(' ').includes(c),
    };
  }
  appendChild(n) { n.parent = this; this.children.push(n); return n; }
  remove() {
    const p = this.parent; if (!p) return;
    p.children.splice(p.children.indexOf(this), 1); this.parent = null;
  }
  set innerHTML(v) { this._html = String(v); if (v === '') this.children = []; }
  get innerHTML() { return this._html; }
  set textContent(v) { this._text = String(v); if (this._text === '') this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(''); }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  addEventListener(tipo, fn) { (this._l[tipo] = this._l[tipo] || []).push(fn); }
  disparar(tipo, extra) {
    const ev = Object.assign({ target: this, preventDefault() {} }, extra || {});
    for (const fn of (this._l[tipo] || [])) fn(ev);
  }
  closest(sel) {
    const attr = sel.replace(/[[\]]/g, '');
    let no = this;
    while (no) {
      if (attr.startsWith('data-')) {
        const chave = attr.slice(5).replace(/-(\w)/g, (_, c) => c.toUpperCase());
        if (no.dataset[chave] !== undefined) return no;
      }
      if (no.attrs[attr] !== undefined) return no;
      no = no.parent;
    }
    return null;
  }
  getBoundingClientRect() { return { top: this === ids.trilho ? 260 - globalThis.window.scrollY : 0, left: 0 }; }
}

const ids = {};
const body = new No('body');
globalThis.document = {
  getElementById: (id) => (ids[id] = ids[id] || new No('div')),
  createElement: (tag) => new No(tag),
  createDocumentFragment: () => new No('#frag'),
  addEventListener: () => {},
  body,
};
globalThis.window = { innerHeight: 800, scrollY: 0, addEventListener: () => {}, scrollTo: () => {} };
globalThis.requestAnimationFrame = (fn) => setTimeout(fn, 0);

const dadosJs = fs.readFileSync('site/dados.js', 'utf8');
new Function('window', dadosJs)(globalThis.window);
globalThis.DADOS = globalThis.window.DADOS;

new Function(fs.readFileSync('site/app.js', 'utf8'))();

const trilho = ids.trilho;
const cards = () => trilho.children;
const nomes = () => cards().map((c) => (c.innerHTML.match(/class="card-nome">([^<]*)</) || [, '?'])[1]);
let falhas = 0;
const ok = (cond, msg) => { console.log((cond ? 'OK   ' : 'FALHA') + ' ' + msg); if (!cond) falhas++; };
const espera = (ms) => new Promise((r) => setTimeout(r, ms));

// 1. estado inicial
ok(ids.hero.innerHTML.includes('BRASIL'), 'hero abre no BRASIL');
ok(cards().length === 6, 'lista do Brasil tem 6 filhos (5 macro + exterior): ' + cards().length);
ok(nomes()[0] === 'Sudeste', 'macrorregiões ordenadas por votos: ' + nomes()[0]);
ok(trilho.style.height === (6 * 128) + 'px', 'altura do trilho = 6 x 128px');

// 2. Brasil -> Sudeste
cards()[0].disparar('click');
ok(ids.hero.innerHTML.includes('Sudeste'), 'clicar em Sudeste navega');
ok(nomes().join(',') === 'São Paulo,Minas Gerais,Rio de Janeiro,Espírito Santo',
  'estados em ordem de votos: ' + nomes().join(','));
ok(ids.voltar.disabled === false, 'botão voltar habilitado');

// 3. Sudeste -> São Paulo (11 regiões intermediárias)
cards()[0].disparar('click');
ok(ids.hero.innerHTML.includes('São Paulo'), 'chegou em São Paulo');
ok(trilho.style.height === (11 * 128) + 'px', 'SP mostra 11 regiões intermediárias (altura do trilho)');
ok(ids.migalhas.innerHTML.split('data-ir').length - 1 === 3, 'migalhas com 3 níveis');

// 4. atalho "ver todos os municípios"
const botao = new No('button');
botao.dataset.municipios = '1';
ids.hero.disparar('click', { target: botao });
ok(trilho.style.height === (645 * 128) + 'px', 'atalho lista os 645 municípios de SP');
ok(cards().length <= 12, 'virtualizado: só ' + cards().length + ' cards no DOM de 645');

// 5. parecer de um município
const campinas = cards().find((c) => c.innerHTML.includes('>Campinas<'));
ok(!!campinas, 'Campinas presente na lista');
campinas.disparar('click');
ok(ids.sheet.hidden === false, 'bottom sheet abre no município');
ok(ids['sheet-corpo'].innerHTML.includes('Classificação histórica'), 'parecer traz classificação histórica');
ok(ids['sheet-corpo'].innerHTML.includes('z ='), 'parecer traz z-score');
ok(ids['sheet-corpo'].innerHTML.includes('ΔW = ΔV'), 'parecer traz a identidade da decomposição');
ok(ids['sheet-corpo'].innerHTML.includes('Histórico presidencial'), 'parecer traz a tabela 2018/2022/2026');
ids.fechar.disparar('click');
await espera(320);
ok(ids.sheet.hidden === true, 'sheet fecha');

// 6. busca
ids.busca.value = 'londrina';
ids.busca.disparar('input');
await espera(300);
ok(cards().length === 3, 'busca "londrina": município + região + Nova Londrina: ' + cards().length);
ok(ids.contagem.textContent.includes('resultado'), 'contagem mostra resultados: ' + ids.contagem.textContent);

ids.busca.value = '';
ids.busca.disparar('input');
await espera(300);
ok(trilho.style.height === (645 * 128) + 'px', 'limpar a busca restaura a lista de municípios');

// 7. voltar
ids.voltar.disparar('click');
ok(ids.hero.innerHTML.includes('São Paulo') && !ids.hero.innerHTML.includes('BRASIL'), 'voltar retorna a SP');
ids.limpar.disparar('click');
ok(ids.hero.innerHTML.includes('BRASIL') && cards().length === 6, 'atalho volta ao Brasil');

console.log(falhas === 0 ? '\nTODOS OS TESTES PASSARAM' : `\n${falhas} FALHA(S)`);
process.exit(falhas === 0 ? 0 : 1);
