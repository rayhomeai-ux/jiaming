"""Build index.html from src/page.html and src/data/.

Usage:
    python tools/build.py              # 產生 index.html（GitHub Pages 版）與 tests/.core_test.js
    python tools/build.py --artifact   # 另外輸出 dist/artifact.html（不載入 config.js，給 Claude 網頁用）

index.html 是產物：要改網頁請改 src/page.html，再執行這支程式。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'src'
DATA = SRC / 'data'


def read(name):
    return (DATA / name).read_text(encoding='utf-8')


def assemble():
    s = (SRC / 'page.html').read_text(encoding='utf-8')
    parts = [
        ('__SANCAI__', read('sancai_tw.json')),
        ('__POOLM__', read('pool_m.txt')),
        ('__POOL__', read('pool.txt')),
        ('__TOPM__', read('top_m.txt')),
        ('__TOP__', read('top.txt')),
        ('__ZOD__', read('zod.json')),
        ('__COMMON__', json.dumps(json.loads(read('moi112_lists.json')), ensure_ascii=False, separators=(',', ':'))),
    ]
    for key, value in parts:
        assert key in s, f'placeholder {key} missing in src/page.html'
        s = s.replace(key, value)
    return s


def check_private(s):
    """公開儲存庫：不得出現預產期或出生資料。

    具體的日期等字串不能寫在這裡（這個檔案也是公開的），
    請一行一個放在根目錄的 .private-terms.txt（已列入 .gitignore，只存在本機）。
    """
    terms = ['預產期']
    private = ROOT / '.private-terms.txt'
    if private.exists():
        terms += [t.strip() for t in private.read_text(encoding='utf-8').splitlines() if t.strip() and not t.startswith('#')]
    else:
        print('提醒：找不到 .private-terms.txt，只檢查通用字詞')
    for i, term in enumerate(terms):
        assert term not in s, f'private detail found (term #{i} in check list)'


def main():
    base = assemble()
    check_private(base)

    site = base.replace('__GH_HEAD__', '<script src="config.js"></script>\n<script src="sheets-backend.js"></script>')
    (ROOT / 'index.html').write_text(site, encoding='utf-8')

    core = site.split('// CORE-START')[1].split('// CORE-END')[0]
    exports = ('C,PAIR,WT,WN,LISTED,setPoem:p=>{POEM=p},analyze,grids,score,rate,wxn,SC,POOL_F,POOL_M,'
               'gridRate,scClass,ch,ZOD,NM,cidx,commonCheck,eraCheck')
    (ROOT / 'tests' / '.core_test.js').write_text(core + '\nmodule.exports={' + exports + '};\n', encoding='utf-8')

    if '--artifact' in sys.argv:
        (ROOT / 'dist').mkdir(exist_ok=True)
        (ROOT / 'dist' / 'artifact.html').write_text(base.replace('__GH_HEAD__', ''), encoding='utf-8')
        print('dist/artifact.html written')

    print(f'index.html written ({len(site):,} chars)')


if __name__ == '__main__':
    main()
