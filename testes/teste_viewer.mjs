// Teste descartável do viewer: DOM mínimo em Node, sem dependências.
import fs from 'node:fs';

class No {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.parent = null;
    this.dataset = {};
    this.className = '';
    this.style = {};
    this.title = '';
    this._text = '';
    this._l = {};
    this.value = '';
  }
  appendChild(n) {
    if (n.isFrag) { for (const c of [...n.children]) { c.parent = this; this.children.push(c); } n.children = []; return n; }
    n.parent = this; this.children.push(n); return n;
  }
  after(n) {
    const p = this.parent; if (!p) return;
    if (n.isFrag) { const i = p.children.indexOf(this); for (const c of [...n.children]) { c.parent = p; p.children.splice(++i, 0, c); } n.children = []; return; }
    p.children.splice(p.children.indexOf(this) + 1, 0, n); n.parent = p;
  }
  remove() {
    const p = this.parent; if (!p) return;
    p.children.splice(p.children.indexOf(this), 1); this.parent = null;
  }
  get nextElementSibling() {
    const p = this.parent; if (!p) return null;
    return p.children[p.children.indexOf(this) + 1] || null;
  }
  set textContent(v) { this._text = String(v); if (this._text === '') this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(''); }
  addEventListener(tipo, fn) { (this._l[tipo] = this._l[tipo] || []).push(fn); }
  disparar(tipo) { for (const fn of (this._l[tipo] || [])) fn({}); }
  querySelector(sel) {
    const cls = sel.replace('.', '');
    const busca = (n) => {
      for (const c of n.children) {
        if (String(c.className).split(' ').includes(cls)) return c;
        const achou = busca(c); if (achou) return achou;
      }
      return null;
    };
    return busca(this);
  }
}

const ids = {};
globalThis.document = {
  getElementById: (id) => (ids[id] = ids[id] || new No('div')),
  createElement: (tag) => new No(tag),
  createDocumentFragment: () => { const f = new No('#frag'); f.isFrag = true; return f; },
};
globalThis.window = {};

const dadosJs = fs.readFileSync('visualizacao/dados.js', 'utf8');
new Function('window', dadosJs)(globalThis.window);
globalThis.HIER = globalThis.window.HIER;

const appJs = fs.readFileSync('visualizacao/app.js', 'utf8');
new Function(appJs)();

const corpo = ids.corpo;
const linhas = () => corpo.children.filter((c) => c.tag === 'tr').length;
let falhas = 0;
const ok = (cond, msg) => { console.log((cond ? 'OK   ' : 'FALHA') + ' ' + msg); if (!cond) falhas++; };

ok(globalThis.window.HIER.rows.length === 5738, 'payload tem 5.738 linhas');
ok(linhas() === 7, 'estado inicial: Brasil + 5 macrorregiões + exterior = 7 linhas (tem ' + linhas() + ')');
ok(ids.status.textContent.includes('7 de 5738'), 'status inicial: "' + ids.status.textContent + '"');

// primeira linha é o Brasil, com seta aberta
const brasil = corpo.children[0];
ok(brasil.textContent.includes('BRASIL'), 'primeira linha é o BRASIL');
ok(brasil.querySelector('.careta')?.textContent === '▾', 'careta do Brasil aponta aberto');

// expandir tudo
ids['btn-expandir'].disparar('click');
ok(linhas() === 5738, 'expandir tudo monta as 5.738 linhas (tem ' + linhas() + ')');
ok(ids.status.textContent.includes('5738 de 5738'), 'status após expandir: "' + ids.status.textContent + '"');

// recolher
ids['btn-recolher'].disparar('click');
ok(linhas() === 1, 'recolher deixa só o Brasil (tem ' + linhas() + ')');

// abrir o Brasil de novo clicando na seta
brasil.querySelector('.careta').disparar('click');
ok(linhas() === 7, 'expandir Brasil pela seta volta para 7 (tem ' + linhas() + ')');

// recolher de novo, e abrir uma UF dentro da macro
brasil.querySelector('.careta').disparar('click');
brasil.querySelector('.careta').disparar('click');
const primeiraMacro = corpo.children[1];
ok(primeiraMacro.textContent.includes('Macrorregião'), 'segunda linha é uma macrorregião');
primeiraMacro.querySelector('.careta').disparar('click');
const antes = linhas();
ok(antes > 7 && antes < 40, 'abrir 1 macrorregião monta só as UFs dela (' + antes + ' linhas)');

// busca
ids.busca.value = 'londrina';
ids.busca.disparar('input');
// Londrina aparece como município, como região intermediária e como "Nova Londrina"
ok(linhas() === 3, 'busca por "londrina" acha município + região + Nova Londrina (' + linhas() + ' linhas)');

// busca por nome de UF: 4 municípios "São Paulo..." + o estado
ids.busca.value = 'sao paulo';
ids.busca.disparar('input');
ok(linhas() === 5, 'busca por "sao paulo" acha 4 municípios + o estado (' + linhas() + ' linhas)');

// busca sem resultado
ids.busca.value = 'zzzzz';
ids.busca.disparar('input');
ok(linhas() === 0, 'busca sem resultado não monta linha nenhuma');

// limpar a busca volta a árvore
ids.busca.value = '';
ids.busca.disparar('input');
ok(linhas() === 7, 'limpar a busca restaura Brasil + macrorregiões (' + linhas() + ')');

console.log(falhas === 0 ? '\nTODOS OS TESTES PASSARAM' : `\n${falhas} FALHA(S)`);
process.exit(falhas === 0 ? 0 : 1);
