# 嘉名 交接文件

最後更新：2026-11-26（從 claude.ai 對話轉到 Claude Code）

## 1. 這是什麼

Ray 為女兒（張姓、雙名）取名時一起做出來的工具，後來改成任何姓氏都能用，並加上家族投票。名字取自《離騷》「肇錫余以嘉名」。

- 網站：<https://rayhomeai-ux.github.io/jiaming/>（GitHub Pages，`main` 分支根目錄）
- 儲存庫：<https://github.com/rayhomeai-ux/jiaming>（公開）
- 本機：`D:\project\AI\jiaming`（淺層 clone，深度 1）
- 投票後端：綁在 Ray 的 Google 試算表上的 Apps Script，網址在 `config.js`
- 舊版：claude.ai 上的 Claude 網頁「嘉名・寶寶取名工具」，用 Claude 內建的共用資料投票。已不再更新，資料也沒有和 GitHub 版同步
- 另有一份 Claude 文件「張家女兒取名建議」，記錄取名過程的分析，只在 claude.ai 看得到

## 2. 目前狀態

- 網站上線，五個分頁都能用：名字健檢、候選產生、八字粗算、已討論名單、家族投票。
- 投票後端已部署最新版 `Code.gs`（含 `@OnlyCurrentDoc` 和防暴力猜碼），Ray 已跑過 `checkSetup`。
- 家族投票目前有 8 個提名，還沒有人投票：
  - 爸爸提名：張榕紗、張菱紗
  - 媽媽提名：張予馨、張曦文、張榕書、張瑄容、張維紓、張綵書
  - 媽媽的 6 個是用管理碼代填的，記在另一個裝置代號、稱呼為「媽媽」的紀錄下。她用自己手機進來時會是另一筆紀錄，所以不能自己撤回這 6 個；要撤回得用管理碼按「移除」。
- 下一步是 Ray 把網址和家族通關碼傳給家人（說明訊息已寫好，在對話裡）。
- GitHub 設定：Issues、Wiki、Projects、Pull requests 已關閉；`main` 有規則「保護 main」（禁止刪除、禁止強制推送）；機密掃描與推送保護開啟。

## 3. 架構

### 3.1 網頁（`src/page.html` → `index.html`）

單一 HTML 檔，所有計算都在瀏覽器裡。執行時再 `fetch` 根目錄的 `chars.json`、`pairs.json`、`poems.json`、`words.json`，八字用 CDN 的 `lunar-javascript@1.7.8`。

`src/page.html` 大致分段（行號會變動，僅供定位）：

| 區段 | 內容 |
| --- | --- |
| `<style>` | 全部 CSS |
| `<section id="v-check">` 等 5 個 | 各分頁 HTML，路由用網址 `#check`、`#generate`、`#bazi`、`#list`、`#vote` |
| `// CORE-START` … `// CORE-END` | 純計算：字資料查詢 `ch()`、五格 `grids()`、`gridRate()`、三才 `scClass()`、`zod()`、`analyze()`、`score()`、菜市場 `commonCheck()`、年代感 `eraCheck()` |
| `const S=…` | 判斷標準設定，存在 localStorage `nm-set` |
| `const LIST=[…]` | 「已討論名單」（張家的候選名字與註記） |
| `renderCheck` / `runGen` / `drawGen` / `renderBazi` / `renderList` | 各分頁畫面 |
| `// ---------- 家族投票 ----------` | 投票模組：`V` 狀態、`save()` 寫入佇列、`nominate`、`castVote`、`renderVote`、`initVote`，以及複製與 LINE 分享 |
| 檔尾 `Promise.all([...fetch])` | 載入資料後才開始畫面 |

佔位符（由 `tools/build.py` 填入）：`__SANCAI__`、`__POOL__`、`__POOLM__`、`__TOP__`、`__TOPM__`、`__ZOD__`、`__COMMON__`、`__GH_HEAD__`（GitHub 版放 `config.js` 與 `sheets-backend.js` 的 `<script>`）。

設定 `S`：`gender`（f/m）、`zodiac`、`sur`、`jinv`（女性忌數 1/0）、`wxrel`（字五行生剋 1/0）、`wai`（外格也要吉 1/0）、`sancai`（`mid` 吉以上／`any` 不凶即可）、`zod`（`part` 部首＋部件／`radical` 只看部首／`off`）、`xi`（喜用五行陣列）、`fam`（家人名字，使用者輸入的原始字串）。

localStorage：`nm-set`（設定）、`nm-fav`（收藏，`姓|名` 格式）、`jm-device`（投票裝置代號）、`jm-code`（通關碼）。

### 3.2 家族投票

投票模組原本寫給 Claude 網頁的 `db`／`user` 介面。GitHub 版由 `sheets-backend.js` 提供同樣的最小介面（`claude.use('db')`、`collection().onSnapshot`、`doc().set`、`user.me()/can()/profiles()`），所以同一份程式兩邊都能跑。`const GH=!!window.JIAMING_BACKEND` 用來切換提示文字，並要求先填稱呼。

資料模型（每個裝置一份）：

- `ballot/<id>`：`{names: {<nid>: {s: 姓, g: 名, t: 提名時間}}}`
- `votes/<id>`：`{v: {<nid>: 1|0|-1}, c: {<nid>: 留言}, nick: 稱呼}`
- `nid` = 每字 Unicode 十六進位以 `-` 相連，姓與名以 `_` 分隔，例如 `5f35_5be7-82b8`
- 裝置代號 `d_` + 16 位十六進位，隨機產生、存在 localStorage

後端協定（`POST`，body 為 JSON 字串、不加自訂標頭以避開 CORS 預檢）：

| op | 參數 | 回應 |
| --- | --- | --- |
| `list` | `code`, `me` | `{ok, admin, rows: [{id, ballot, votes}]}` |
| `set` | `code`, `me`, `col`（ballot/votes）, `id`, `body` | `{ok}`；非管理者只能寫自己的 `id` |

錯誤碼：`bad_code`、`locked`（10 分鐘內錯 30 次）、`not_owner`、`too_large`（單格 40,000 字元）、`bad_id`、`bad_col`、`bad_op`、`bad_json`。管理碼進入時 `admin: true`，畫面上的「移除」才會出現。網頁每 20 秒輪詢一次（只在投票分頁可見時）。

試算表：`data` 工作表每裝置一列（id、ballot JSON、votes JSON、更新時間）；`結果` 工作表每次寫入後自動重算排名、誰投什麼、留言。通關碼存在 Apps Script 的指令碼屬性 `FAMILY_CODE`、`ADMIN_CODE`。編輯器可執行 `checkSetup`（檢查設定、不印出通關碼）與 `resetLock`（解除鎖定）。

## 4. 姓名學規則（目前採用的版本）

- **筆劃**：康熙筆劃。兩份字庫（babyname/fate、shunshi-kangxi-core）比對，不一致的字記在 `alt`，候選產生預設排除。
- **五格**：天格＝單姓＋1（複姓＝兩字相加）；人格＝姓末字＋名首字；地格＝名兩字相加（單名＋1）；外格＝單姓雙名為名末字＋1、單姓單名固定 2、複姓雙名為姓首字＋名末字、複姓單名為姓首字＋1；總格＝全部相加。超過 81 減 80。
- **81 數吉凶**：`DAJI`、`BANJI` 常數；女性忌數 `JINV` = 21, 23, 26, 28, 29, 33, 39，只在女孩且「女性忌數：要看」時套用，且不套用在外格。
- **三才**：天人地三格的數理五行（個位數 1、2 木，3、4 火，5、6 土，7、8 金，9、0 水）查 `sancai_tw.json`（124 組，缺「金金火」，視為參考）。
- **字五行**：相鄰字生剋，剋為警告。**陰陽**：奇數陽、偶數陰。
- **生肖字根**：`zod.json` 為十二生肖的宜／不宜部首（整理自網路通行表），部首變體已正規化；「部首＋部件」模式另用 `HIDDEN` 部件表（例如寧含心、好含子）。
- **八字粗算**：天干 1、藏干本氣 1／中氣 0.5／餘氣 0.3、月令 ×2；同黨（比劫＋印）≥50% 為身強，喜食傷、財、官殺；否則喜印、比劫。結果只當參考。
- **菜市場名**（內政部《全國姓名統計分析》112 年版）：名字完全在全國前 100 大、各世代前 10 大或單名前 100 大裡 → 警告；讀音含聲調相同 → 警告；只有聲調不同 → 參考；異性名單命中降為參考。
- **年代感**：名字在民國 59 年以前出生的前 10 大 → 警告；含 `OLD_CH` 長輩常用字 → 警告；民國 60–89 年代的常見名字或含 `MID_CH` → 參考。`OLD_CH`／`MID_CH` 是依統計資料人工挑選，有主觀成分。
- **撞名**：比對同姓同名前 100 名與 `FAMOUS` 名人清單。
- **家人名字（避諱）**：上方規則列填入父母、祖父母等長輩的名字才會檢查（`famParse`、`familyCheck`）。三字以上視為全名、去掉姓（`FUXING` 複姓去兩字，四字冠夫姓保留後兩字），一、兩字視為名。名字和家人完全相同或同字 → 不符；讀音含聲調相同 → 注意；只差聲調 → 參考。候選產生會排除同字與同音（計入「另排除」）。依據：民間普遍避長輩名諱；《姓名條例》第 9 條把「與三親等以內直系尊親屬名字完全相同」列為改名事由。
- **排序分數 `score()`**：三才大吉 +2／吉 +1；生肖每字 −5～+2；字五行相生 +1、相剋 −2；每個喜用字 +2；聲調 ±1；同音詞警告 −2；有詩詞出處 +2；撞名 −3；菜市場、年代感警告各 −3、參考各 −1；筆劃或陰陽警告 −1；外格警告 −2；家人名字不符 −5、注意 −3、參考 −1；常用好字（`top*.txt`）每字 +2；Big5 次常用字每字 −1；已討論過 +1。

## 5. 資料檔

| 檔案 | 格式 |
| --- | --- |
| `chars.json` | 每列 `[字, 康熙筆劃, 另一字庫筆劃(不一致才有), 來源數, 部首, 五行, 另一字庫五行, 拼音, 數字調拼音, 隱藏部件, Big5 等級]`，13,048 字 |
| `pairs.json` | `[兩字(依碼位排序), 詩句索引]` |
| `poems.json` | 詩句陣列（含兩個以上池內字的句子） |
| `words.json` | `[數字調拼音, "同音詞 以空白分隔"]`，用來抓諧音 |
| `src/data/pool.txt`／`pool_m.txt` | 女孩／男孩候選字池 |
| `src/data/top.txt`／`top_m.txt` | 常用好字（加分） |
| `src/data/moi112_lists.json` | `top`（全國前 100）、`single`（單名前 100）、`same`（同姓同名前 100）、`coh`（各世代前 10，`[民國起始年, [[名字, 人數]...]]`），皆分 `m`／`f` |
| `src/data/zod.json`、`sancai_tw.json` | 生肖字根表、三才吉凶表 |

`moi112_lists.json` 是從內政部 112 年版 PDF（表五十、五十一、五十二、五十六）擷取的。重建根目錄 JSON 見 `dev/data-pipeline/README.md`。

## 6. 建置、測試、部署

```bash
python tools/build.py          # 產生 index.html；--artifact 另產生 dist/artifact.html（給 Claude 網頁）
node tests/core.test.js        # 11 項核心測試
python tests/e2e_vote.py       # 10 項投票流程測試（mock 後端執行真正的 Code.gs）
```

- 網站：推送到 `main`，GitHub Pages 約一分鐘內自動更新。
- 投票後端：改 `Code.gs` 後，Ray 要手動貼到 Apps Script，並用「管理部署作業 → 編輯 → 新版本」部署，網址不變。
- `index.html` 目前與 `tools/build.py` 的輸出逐位元相同；改網頁請改 `src/page.html`。
- 網站圖示（朱紅印章底、白色「嘉」，Noto Serif TC 900）由 `python tools/make_icons.py` 產生根目錄的 `favicon-32.png`、`icon-192.png`、`apple-touch-icon.png`；需要 playwright 與系統安裝的 Noto Serif TC。

## 7. 隱私與安全

- 儲存庫和網站都公開。寶寶的出生日期、時辰、八字結果都不放進儲存庫。
- `tools/build.py` 會檢查產物裡不得出現「預產期」，以及本機 `.private-terms.txt`（已列入 `.gitignore`）裡列的字串，例如預產期日期。這個檔案只存在 Ray 的電腦上；具體日期不要寫進任何會提交的檔案。
- 通關碼只存在 Apps Script 指令碼屬性；試算表不要共用。
- 本機 `D:\project\AI\jiaming\token.txt` 是 Ray 的私人檔案，已列入 `.gitignore`，不要讀取或提交。
- 通關碼外流時，到指令碼屬性改掉即可，立即生效。
- 「家人名字」只存在瀏覽器的 `nm-set`，不送到後端，也不放進複製／LINE 分享文字（`listText` 不含檢查結果）。真實的家人名字不要寫進程式、測試或文件；測試只用虛構名字。

## 8. 決策紀錄

- **為何用 GitHub Pages＋Google 試算表**：家人不用註冊任何帳號；Claude 網頁版的投票需要每位家人都有 Claude 帳號並被邀請為可編輯。
- **投票方式**：每名「喜歡／可以／不喜歡」＋一句留言；票分＝喜歡 2、可以 1、不喜歡 −2。
- **身分**：裝置代號＋自填稱呼，不做登入；通關碼只擋外人，同一人換裝置能重投，家人間可接受。
- **LINE 分享**：LINE 的分享網址只在手機 App 有效；電腦版改成「複製後貼到 LINE」。
- **必含字**：不在字庫裡也會自動加入候選池（曾因「根」不在男孩字庫而產生 0 個結果）。
- **預設排除**：候選產生預設排除菜市場名（含同音）與長輩常用名、用字，可取消勾選。

## 9. 已知限制與待辦

- 菜市場資料只到全國前 100、各世代前 10，排名較後的常見名抓不到。
- 同音比對只用每字最常見的讀音，破音字可能漏抓。
- `OLD_CH`／`MID_CH` 與生肖字根表都是單一流派的整理。
- 生肖字根改用網路通行表後，「馬」的結果和 Claude 文件「張家女兒取名建議」裡的生肖欄不同（玉變中性、口變不宜）。曾提議更新文件，Ray 尚未回覆。
- 舊的 Claude 網頁版仍有自己的投票資料（Ray 當初提名的 8 個收藏），與 GitHub 版無關。
- `words.json` 與 `pool_m.txt` 是舊版（非決定性）管線產生的；用新版管線重建時，同分項目的順序可能改變，內容相同。
- 可能的下一步（未承諾）：投票截止或隱藏票數直到自己投完、匯出結果、把「已討論名單」改由試算表管理。
