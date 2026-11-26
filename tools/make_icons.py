"""產生網站圖示：朱紅印章底、白色「嘉」字。

輸出到根目錄：favicon-32.png（分頁圖示）、icon-192.png、apple-touch-icon.png（加到 iPhone 主畫面）。

需求：pip install playwright && python -m playwright install chromium，
以及系統已安裝 Noto Serif TC（Windows 11 內建 NotoSerifTC-VF.ttf；SIL OFL 授權）。
用法：python tools/make_icons.py
"""
import asyncio
import sys
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
RED = '#c4161c'  # 與網頁的 --red 相同

# 檔名, 邊長, 圓角（比例）, 有無內框, 字大小（比例）
ICONS = [
    ('favicon-32.png', 32, .2, False, .8),
    ('icon-192.png', 192, .2, True, .66),
    ('apple-touch-icon.png', 180, 0, True, .62),  # iOS 會自己裁圓角，所以填滿
]


def page(size, radius, frame, glyph):
    inset, bw = size * .1, max(2, round(size * .022))
    box = (f'<div style="position:absolute;inset:{inset}px;border:{bw}px solid #fff;'
           f'border-radius:{size * .05}px;opacity:.92"></div>') if frame else ''
    return f'''<!DOCTYPE html><html><body style="margin:0;background:transparent">
<div style="width:{size}px;height:{size}px;border-radius:{size * radius}px;background:{RED};position:relative;
display:flex;align-items:center;justify-content:center;overflow:hidden">{box}
<span style="font:900 {size * glyph}px/1 'Noto Serif TC';color:#fff;position:relative;top:{size * .01}px">嘉</span>
</div></body></html>'''


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        for name, size, radius, frame, glyph in ICONS:
            await pg.set_viewport_size({'width': size, 'height': size})
            await pg.set_content(page(size, radius, frame, glyph))
            await pg.evaluate('document.fonts.ready')
            fam = await pg.evaluate("getComputedStyle(document.querySelector('span')).fontFamily")
            await pg.screenshot(path=str(ROOT / name), omit_background=True)
            print(name, size, fam)
        if '--preview' in sys.argv:
            out = Path(sys.argv[sys.argv.index('--preview') + 1])
            cells = ''.join(f'<figure><img src="{(ROOT / n).as_uri()}" style="width:{max(s, 128)}px;image-rendering:pixelated">'
                            f'<img src="{(ROOT / n).as_uri()}" style="width:16px"><img src="{(ROOT / n).as_uri()}" style="width:32px">'
                            f'<figcaption>{n}</figcaption></figure>' for n, s, *_ in ICONS)
            await pg.set_viewport_size({'width': 760, 'height': 300})
            await pg.goto((ROOT / 'index.html').as_uri())
            await pg.set_content(f'<body style="display:flex;gap:24px;font:14px sans-serif;background:#fff">{cells}'
                                 f'<div style="background:#202124;padding:12px">{cells}</div></body>')
            await pg.wait_for_timeout(300)
            await pg.screenshot(path=str(out))
            print('preview', out)
        await b.close()


if __name__ == '__main__':
    asyncio.run(main())
