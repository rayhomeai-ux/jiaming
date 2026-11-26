// 核心計算的回歸測試：先執行 python tools/build.py 產生 tests/.core_test.js，再執行 node tests/core.test.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.join(__dirname, '..');
const M = require('./.core_test.js');
const rd = f => JSON.parse(fs.readFileSync(path.join(ROOT, f), 'utf8'));
for (const r of rd('chars.json')) M.C.set(r[0], r);
for (const [k, i] of rd('pairs.json')) M.PAIR.set(k, i);
M.setPoem(rd('poems.json'));
for (const [k, w] of rd('words.json')) { M.WT.set(k, w); const p = k.replace(/\d/g, ''); M.WN.set(p, [...(M.WN.get(p) || []), ...w.split(' ')]); }

const GIRL = { gender: 'f', zodiac: '馬', jinv: 1, wxrel: 1, wai: 1, sancai: 'mid', zod: 'part', xi: [] };
const BOY = { ...GIRL, gender: 'm', zodiac: '蛇' };
const check = (a, name) => a.checks.find(c => c.name === name);
let n = 0;
const t = (label, fn) => { fn(); n++; console.log('ok', label); };

t('張寧芸 五格與三才', () => {
  const a = M.analyze('張', '寧芸', GIRL);
  assert.deepEqual([a.g.tian, a.g.ren, a.g.di, a.g.wai, a.g.zong], [12, 25, 24, 11, 35]);
  assert.equal(a.cfg, '木土火');
  assert.equal(check(a, '菜市場名').st, 'pass');
  assert.equal(typeof M.score(a, GIRL), 'number');
});

t('複姓 歐陽語桐 五格', () => {
  const a = M.analyze('歐陽', '語桐', GIRL);
  assert.deepEqual([a.g.tian, a.g.ren, a.g.di, a.g.wai, a.g.zong], [32, 31, 24, 25, 56]);
});

t('菜市場名：完全相同', () => {
  const c = check(M.analyze('張', '芯語', GIRL), '菜市場名');
  assert.equal(c.st, 'warn');
  assert.match(c.det, /芯語/);
});

t('菜市場名：同音', () => {
  const c = check(M.analyze('張', '語桐', GIRL), '菜市場名');
  assert.equal(c.st, 'warn');
  assert.match(c.det, /讀音同「語彤」/);
});

t('菜市場名：單名', () => {
  assert.equal(check(M.analyze('張', '杰', BOY), '菜市場名').st, 'warn');
});

t('年代感：長輩用字', () => {
  const c = check(M.analyze('張', '秀芸', GIRL), '年代感');
  assert.equal(c.st, 'warn');
  assert.match(c.det, /秀/);
});

t('撞名：同姓同名排行', () => {
  const c = check(M.analyze('張', '家豪', BOY), '撞名');
  assert.equal(c.st, 'warn');
  assert.match(c.det, /第 3 多/);
});

t('女性忌數不套用在男生', () => {
  assert.equal(M.gridRate(21, GIRL), '忌女');
  assert.equal(M.gridRate(21, BOY), '吉');
});

console.log(`\n${n} tests passed`);
