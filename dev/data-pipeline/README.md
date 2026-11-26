# 資料管線：重建根目錄的 JSON

平常不需要執行。只有在要換字庫、調整字池或詩詞來源時，才重建 `chars.json`、`pairs.json`、`poems.json`、`words.json`。

## 需要的原始資料（放在 `dev/raw/`，已列入 .gitignore）

| 目錄 | 來源 | 用途 |
| --- | --- | --- |
| `dev/raw/fate/` | `git clone https://github.com/babyname/fate`（MIT） | `resources/character.json`：康熙筆劃、五行、部首、拼音 |
| `dev/raw/shunshi-kangxi-core/` | npm 套件 `shunshi-kangxi-core@0.1.1` 解開後的 `package/`（MIT） | `data/chars.json.gz`：第二份康熙筆劃，用來交叉比對 |
| `dev/raw/gushi_namer/` | `git clone https://github.com/holynova/gushi_namer` | `dist/json/*.json`：詩經、楚辭、唐詩、宋詞句子 |

例如：

```bash
mkdir -p dev/raw && cd dev/raw
git clone --depth 1 https://github.com/babyname/fate
git clone --depth 1 https://github.com/holynova/gushi_namer
npm pack shunshi-kangxi-core@0.1.1 && tar xzf shunshi-kangxi-core-0.1.1.tgz && mv package shunshi-kangxi-core
```

Python 套件：`pip install opencc-python-reimplemented pypinyin jieba`（`words.json` 用的是 jieba 內建詞庫）。

## 執行

```bash
python dev/data-pipeline/build_data.py                 # 直接覆寫根目錄的 JSON 與 src/data/pool_m.txt
OUT=/tmp/out python dev/data-pipeline/build_data.py    # 先輸出到別處比對
RAW=/path/to/raw python dev/data-pipeline/build_data.py
```

輸出統計（2026-11 版）：chars 13,048 字、詩句 2,120 行、字對 3,715 組、同音詞 24,653 組。

注意：

- 管線已改成決定性輸出。目前儲存庫裡的 `words.json` 與 `src/data/pool_m.txt` 是改版前產生的，重建後同分項目的順序可能不同，內容一樣。
- 女孩字池 `src/data/pool.json` 是人工整理的輸入；男孩字池寫在 `build_data.py` 的 `BOY` 常數。
- `HIDDEN`（字形部件，生肖判斷用）、`NORM`（部首正規化）、`TW_PY`（台灣讀音覆蓋）都在 `build_data.py` 裡人工維護。
- `src/data/moi112_lists.json` 不在這條管線裡，是從內政部《全國姓名統計分析》112 年版 PDF 的表五十、五十一、五十二、五十六擷取的。
