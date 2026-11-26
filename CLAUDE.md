# 嘉名・寶寶取名工具 — Claude Code 專案說明

純前端的取名網站（GitHub Pages）＋ Google Apps Script 投票後端。介面文字一律用**台灣繁體中文**。
完整背景、決策紀錄與待辦請先讀 `docs/HANDOFF.md`。

## 常用指令

```bash
python tools/build.py              # src/ → index.html（每次改完都要跑）＋ tests/.core_test.js
node tests/core.test.js            # 核心計算回歸測試（先跑 build）
python tests/e2e_vote.py           # 投票端對端測試（需要 Node、playwright + chromium）
python -m http.server 8000         # 本機預覽 http://localhost:8000/
```

## 規則

- **index.html 是產物。** 只改 `src/page.html` 或 `src/data/*`，再執行 `python tools/build.py`。`build.py` 會檢查不得出現「預產期」及本機 `.private-terms.txt` 列的字串，失敗就是有個人資訊要外洩了。具體日期等私密字串不可寫進任何會提交的檔案（包括程式和文件）。
- **儲存庫是公開的。** 不可提交：通關碼（`FAMILY_CODE`／`ADMIN_CODE`）、寶寶出生日期時辰、八字結果、`token.txt` 或任何金鑰。提交者 Email 用 `rayhomeai-ux@users.noreply.github.com`。
- **不要改 `config.js` 的網址**，除非使用者給了新的 Apps Script 部署網址。部署網址換了，網站就連不到投票資料。
- **改 `apps-script/Code.gs` 後**，使用者必須在 Apps Script 編輯器貼上新版，並用「管理部署作業 → 編輯 → 新版本」部署（不是「新增部署作業」）。README 有完整步驟；完成改動後要提醒使用者。
- **共用資料一律當不可信輸入：** 投票資料、稱呼、留言要用 `esc()` 或 `textContent` 輸出。
- **`main` 有規則保護**：禁止強制推送與刪除。直接推送一般提交即可；Pull request 功能已關閉。
- **核心計算**（`// CORE-START` 到 `// CORE-END`）必須維持純函式、不碰 DOM，`tools/build.py` 會把它抽出來給 Node 測試。改到這段就要跑 `node tests/core.test.js`，並視需要補測試。
- 姓名學各派說法不同，改判斷邏輯前先問使用者採用哪一派，不要自行決定。

## 結構速覽

```
src/page.html          網頁模板（CSS、HTML、全部 JS）；__XXX__ 佔位由 build.py 填入
src/data/              字庫池、三才表、生肖字根表、內政部姓名統計（小檔，嵌入網頁）
index.html             建置產物（GitHub Pages 直接提供）
*.json（根目錄）        字庫、詩詞、同音詞（網頁執行時 fetch）
config.js              投票後端網址
sheets-backend.js      把 Google 試算表後端包成 Claude 共用資料的介面
apps-script/Code.gs    投票後端（貼到 Google Apps Script）
tools/build.py         建置
tests/                 core.test.js、e2e_vote.py、mock_gas.js（以記憶體試算表執行真正的 Code.gs）
dev/data-pipeline/     重建根目錄 JSON 的資料管線（需要原始資料，見其 README）
docs/HANDOFF.md        交接文件
```
