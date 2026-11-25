/**
 * @OnlyCurrentDoc
 * ↑ 讓這支程式只能存取它所綁定的這一份試算表，碰不到你雲端硬碟裡的其他檔案。
 */

/**
 * 嘉名：家族投票後端（Google Apps Script，綁定在一份 Google 試算表上）
 *
 * 設定方式請看儲存庫的 README.md「設定家族投票」。
 * 需要在「專案設定 → 指令碼屬性」新增兩個屬性：
 *   FAMILY_CODE  家人用的通關碼（建議 8 碼以上、英數混合）
 *   ADMIN_CODE   你自己用的管理碼（可移除任何人提名的名字）
 *
 * 資料表：
 *   data  每台裝置一列：id、ballot（提名，JSON）、votes（投票與留言，JSON）、更新時間
 *   結果   每次有人投票後自動重算，方便直接在試算表裡看
 *
 * 防暴力猜碼：10 分鐘內通關碼錯誤累計 30 次，就暫停受理所有請求，
 * 直到連續 10 分鐘沒有新的錯誤嘗試為止。
 */

var DATA_SHEET = 'data';
var SUMMARY_SHEET = '結果';
var MAX_BODY = 40000;      // 單一儲存格上限 50,000 字元，留一點餘裕
var FAIL_LIMIT = 30;       // 鎖定前允許的錯誤次數
var FAIL_WINDOW = 600;     // 秒；也是鎖定時間

function doGet() {
  return out_({ ok: true, service: 'jiaming' });
}

function doPost(e) {
  var req;
  try { req = JSON.parse(e.postData.contents); } catch (err) { return out_({ ok: false, error: 'bad_json' }); }

  var cache = CacheService.getScriptCache();
  var fails = Number(cache.get('fails') || 0);
  if (fails >= FAIL_LIMIT) return out_({ ok: false, error: 'locked' });

  var props = PropertiesService.getScriptProperties();
  var family = props.getProperty('FAMILY_CODE');
  var admin = props.getProperty('ADMIN_CODE');
  var code = String(req.code || '');
  var isAdmin = !!admin && code === admin;
  var allowed = isAdmin || (!!family && code === family);
  if (!allowed) {
    cache.put('fails', String(fails + 1), FAIL_WINDOW);
    Utilities.sleep(1000); // 拖慢連續猜測
    return out_({ ok: false, error: 'bad_code' });
  }

  if (req.op === 'list') return out_({ ok: true, admin: isAdmin, rows: readRows_() });

  if (req.op === 'set') {
    if (req.col !== 'ballot' && req.col !== 'votes') return out_({ ok: false, error: 'bad_col' });
    if (!/^d_[0-9a-f]{16}$/.test(String(req.id || ''))) return out_({ ok: false, error: 'bad_id' });
    if (req.id !== req.me && !isAdmin) return out_({ ok: false, error: 'not_owner' });
    var body = JSON.stringify(req.body || {});
    if (body.length > MAX_BODY) return out_({ ok: false, error: 'too_large' });

    var lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      upsert_(req.id, req.col, body);
      refreshSummary_();
    } finally {
      lock.releaseLock();
    }
    return out_({ ok: true });
  }
  return out_({ ok: false, error: 'bad_op' });
}

/**
 * 部署後在編輯器裡選這個函式按「執行」一次：
 * 會觸發授權，並在「執行記錄」顯示設定是否完整（不會印出通關碼）。
 */
function checkSetup() {
  var props = PropertiesService.getScriptProperties();
  var family = props.getProperty('FAMILY_CODE') || '';
  var admin = props.getProperty('ADMIN_CODE') || '';
  var notes = [];
  notes.push('FAMILY_CODE：' + (family ? family.length + ' 碼' : '未設定'));
  notes.push('ADMIN_CODE：' + (admin ? admin.length + ' 碼' : '未設定'));
  if (family && family.length < 8) notes.push('建議 FAMILY_CODE 改成 8 碼以上');
  if (admin && admin.length < 8) notes.push('建議 ADMIN_CODE 改成 8 碼以上');
  if (family && admin && family === admin) notes.push('兩個通關碼不應相同');
  notes.push('目前錯誤次數：' + (CacheService.getScriptCache().get('fails') || 0) + '／' + FAIL_LIMIT);
  dataSheet_();
  notes.push('資料表：' + SpreadsheetApp.getActiveSpreadsheet().getName() + ' 可正常讀寫');
  Logger.log(notes.join('\n'));
}

/** 鎖定時想立刻解除，可在編輯器執行這個函式。 */
function resetLock() {
  CacheService.getScriptCache().remove('fails');
  Logger.log('已解除鎖定');
}

function sheet_(name, header) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(name);
  if (!sh) { sh = ss.insertSheet(name); sh.appendRow(header); sh.setFrozenRows(1); }
  return sh;
}

function dataSheet_() { return sheet_(DATA_SHEET, ['id', 'ballot', 'votes', 'updated']); }

function readRows_() {
  var values = dataSheet_().getDataRange().getValues();
  var rows = [];
  for (var i = 1; i < values.length; i++) {
    var r = values[i];
    if (!r[0]) continue;
    rows.push({ id: String(r[0]), ballot: parse_(r[1]), votes: parse_(r[2]) });
  }
  return rows;
}

function parse_(s) { try { return s ? JSON.parse(s) : null; } catch (e) { return null; } }

function upsert_(id, col, body) {
  var sh = dataSheet_();
  var last = sh.getLastRow();
  var ids = last > 1 ? sh.getRange(2, 1, last - 1, 1).getValues().map(function (r) { return String(r[0]); }) : [];
  var i = ids.indexOf(id);
  var c = col === 'ballot' ? 2 : 3;
  if (i < 0) {
    sh.appendRow([id, col === 'ballot' ? body : '', col === 'votes' ? body : '', new Date()]);
  } else {
    sh.getRange(i + 2, c).setValue(body);
    sh.getRange(i + 2, 4).setValue(new Date());
  }
}

/** 把投票整理成「結果」工作表：名字、喜歡／可以／不喜歡、票分、誰投了什麼、留言。 */
function refreshSummary_() {
  var rows = readRows_();
  var names = {}, order = [];
  rows.forEach(function (r) {
    var ns = r.ballot && r.ballot.names;
    if (!ns) return;
    Object.keys(ns).forEach(function (nid) {
      var x = ns[nid];
      if (!x || !x.s || !x.g) return;
      if (!names[nid]) { names[nid] = x.s + x.g; order.push(nid); }
    });
  });
  var nick = {};
  rows.forEach(function (r) { nick[r.id] = (r.votes && r.votes.nick) || '某位家人'; });
  var out = [['名字', '喜歡', '可以', '不喜歡', '票分', '喜歡的人', '不喜歡的人', '留言']];
  order.forEach(function (nid) {
    var like = [], ok = [], no = [], cm = [];
    rows.forEach(function (r) {
      var v = r.votes && r.votes.v && r.votes.v[nid];
      if (v === 1) like.push(nick[r.id]); else if (v === 0) ok.push(nick[r.id]); else if (v === -1) no.push(nick[r.id]);
      var c = r.votes && r.votes.c && r.votes.c[nid];
      if (c) cm.push(nick[r.id] + '：' + c);
    });
    out.push([names[nid], like.length, ok.length, no.length, 2 * like.length + ok.length - 2 * no.length, like.join('、'), no.join('、'), cm.join('\n')]);
  });
  var head = out.shift();
  out.sort(function (a, b) { return b[4] - a[4] || b[1] - a[1]; });
  out.unshift(head);
  var sh = sheet_(SUMMARY_SHEET, head);
  sh.clearContents();
  sh.getRange(1, 1, out.length, head.length).setValues(out);
  sh.setFrozenRows(1);
}

function out_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
