/*
 * 嘉名：家族投票的 Google 試算表後端轉接層。
 * 只在 GitHub Pages 版使用：config.js 設好 JIAMING_BACKEND.url 時啟用。
 * 它提供和 Claude 共用資料相同的最小介面（db.collection().onSnapshot、db.doc().set
 * 與 user.me()/can()/profiles()），所以投票頁面的程式不需要分成兩套。
 */
(function () {
  'use strict';
  var CFG = window.JIAMING_BACKEND || {};
  if (window.claude) return;
  if (!CFG.url) { CFG.why = '投票功能還沒設定：請依 README 部署 Google Apps Script，並把網址填進 config.js。'; return; }

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) {} }

  // 每台裝置一個隨機代號，用來區分「誰投的」；名字由使用者自己填的稱呼顯示。
  var dev = lsGet('jm-device');
  if (!dev || !/^d_[0-9a-f]{16}$/.test(dev)) {
    var a = new Uint8Array(8); crypto.getRandomValues(a);
    dev = 'd_' + Array.from(a, function (b) { return b.toString(16).padStart(2, '0'); }).join('');
    lsSet('jm-device', dev);
  }
  var code = lsGet('jm-code') || '';
  var S = { rows: new Map(), admin: false, subs: [], timer: null };

  async function call(p) {
    p.code = code; p.me = dev;
    // 不加自訂標頭：以 text/plain 送出，避免瀏覽器先送 CORS 預檢請求。
    var r = await fetch(CFG.url, { method: 'POST', body: JSON.stringify(p) });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return r.json();
  }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function snap(col) {
    var docs = [];
    S.rows.forEach(function (row, id) {
      var d = row[col];
      if (d && typeof d === 'object') docs.push({ id: id, exists: true, data: function () { return clone(d); }, metadata: { fromCache: false, hasPendingWrites: false } });
    });
    return { docs: docs, size: docs.length, empty: !docs.length, metadata: { fromCache: false, hasPendingWrites: false }, docChanges: function () { return []; } };
  }
  function deliver() { S.subs.forEach(function (s) { try { s.next(snap(s.col)); } catch (e) { console.error(e); } }); }
  function load(rows) {
    S.rows = new Map();
    (rows || []).forEach(function (r) { if (r && typeof r.id === 'string') S.rows.set(r.id, { ballot: r.ballot, votes: r.votes }); });
  }
  async function pull() {
    try { var j = await call({ op: 'list' }); if (j.ok) { load(j.rows); S.admin = !!j.admin; deliver(); } } catch (e) { /* 下次輪詢再試 */ }
  }
  function onVoteTab() { return document.visibilityState === 'visible' && location.hash === '#vote'; }

  var db = {
    collection: function (col) {
      return {
        onSnapshot: function (next, err) {
          var s = { col: col, next: next, err: err }; S.subs.push(s);
          setTimeout(function () { next(snap(col)); }, 0);
          return function () { S.subs = S.subs.filter(function (x) { return x !== s; }); };
        }
      };
    },
    doc: function (path) {
      var seg = path.split('/');
      return {
        set: async function (body) {
          var j;
          try { j = await call({ op: 'set', col: seg[0], id: seg[1], body: body }); }
          catch (e) { throw { code: 'unavailable', message: String(e && e.message || e) }; }
          if (!j.ok) throw { code: (j.error === 'bad_code' || j.error === 'not_owner' || j.error === 'too_large' || j.error === 'bad_id') ? 'invalid_argument' : 'unavailable', message: j.error };
          var row = S.rows.get(seg[1]) || {}; row[seg[0]] = clone(body); S.rows.set(seg[1], row); deliver();
        }
      };
    }
  };
  var user = {
    me: async function () { return { id: dev, name: '', avatarUrl: '', color: '#888', email: null, isOwner: S.admin, canEdit: S.admin }; },
    id: async function () { return dev; },
    can: async function () { return true; },
    isOwner: async function () { return S.admin; },
    canEdit: async function () { return S.admin; },
    profiles: async function (ids) {
      var o = {}; [].concat(ids).forEach(function (i) { o[i] = { id: i, name: '', avatarUrl: '', color: '#888', email: null, isMe: i === dev, guest: false, roles: null }; });
      return o;
    }
  };

  var ready = (async function () {
    if (!code) { CFG.why = '請先在上方輸入家族通關碼。'; return false; }
    try {
      var j = await call({ op: 'list' });
      if (!j.ok) {
        CFG.why = j.error === 'bad_code' ? '家族通關碼不正確，請重新輸入。' : j.error === 'locked' ? '通關碼錯誤次數太多，已暫時鎖定，請 10 分鐘後再重新整理。' : '投票後端回應錯誤（' + j.error + '）。';
        if (j.error === 'bad_code') { lsSet('jm-code', null); code = ''; }
        return false;
      }
      load(j.rows); S.admin = !!j.admin;
      S.timer = setInterval(function () { if (onVoteTab()) pull(); }, CFG.poll || 20000);
      document.addEventListener('visibilitychange', function () { if (onVoteTab()) pull(); });
      window.addEventListener('hashchange', function () { if (location.hash === '#vote') pull(); });
      return true;
    } catch (e) { CFG.why = '連不上投票後端，請檢查網路後重新整理。'; return false; }
  })();

  window.claude = { use: async function (n) { var ok = await ready; if (!ok) return null; return n === 'db' ? db : n === 'user' ? user : null; } };

  // 投票頁上方的通關碼欄位
  function panel(ok) {
    var host = document.querySelector('#v-vote .panel'); if (!host) return;
    var box = document.createElement('div'); box.className = 'row'; box.style.marginBottom = '10px';
    if (ok) {
      box.innerHTML = '<span class="note">已用家族通關碼進入' + (S.admin ? '（管理者）' : '') + '。投票結果約每 20 秒自動更新。</span><button class="btn ghost sm" type="button" id="v-code-out">登出</button>';
    } else {
      box.innerHTML = '<label>家族通關碼<input type="password" id="v-code" autocomplete="off" style="width:10em"></label><button class="btn" type="button" id="v-code-go">進入投票</button>';
    }
    host.insertBefore(box, host.firstChild);
    var go = box.querySelector('#v-code-go'), inp = box.querySelector('#v-code'), out = box.querySelector('#v-code-out');
    if (go) {
      var submit = function () { var v = inp.value.trim(); if (!v) { inp.focus(); return; } lsSet('jm-code', v); location.reload(); };
      go.addEventListener('click', submit);
      inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); submit(); } });
    }
    if (out) out.addEventListener('click', function () { lsSet('jm-code', null); location.reload(); });
  }
  ready.then(function (ok) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { panel(ok); });
    else panel(ok);
  });
})();
