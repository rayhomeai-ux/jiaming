"""家族投票端對端測試：真正的 Code.gs（記憶體試算表）＋ 網頁 ＋ 兩台模擬裝置。

需求：pip install playwright && python -m playwright install chromium，以及 Node.js。
用法：python tests/e2e_vote.py
環境變數（選用）：
  CHROME=/path/to/chrome      改用指定的瀏覽器
  LUNAR_JS=/path/to/lunar.js  離線時用本機的 lunar-javascript，取代 CDN
"""
import asyncio
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
MOCK_PORT, WEB_PORT = 8766, 8767
CFG = f"window.JIAMING_BACKEND={{url:'http://localhost:{MOCK_PORT}/',poll:1500}};"
URL = f'http://localhost:{WEB_PORT}/index.html#vote'


def start_servers():
    env = dict(os.environ, MOCK_PORT=str(MOCK_PORT))
    mock = subprocess.Popen(['node', str(ROOT / 'tests' / 'mock_gas.js')], env=env, stdout=subprocess.DEVNULL)
    web = subprocess.Popen([sys.executable, '-m', 'http.server', str(WEB_PORT)], cwd=ROOT,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    return mock, web


async def main():
    lunar = Path(os.environ['LUNAR_JS']).read_text(encoding='utf-8') if os.environ.get('LUNAR_JS') else None
    errs, fails = [], []

    def expect(cond, label):
        print(('ok  ' if cond else 'FAIL') + ' ' + label)
        if not cond:
            fails.append(label)

    async with async_playwright() as p:
        kw = {'executable_path': os.environ['CHROME']} if os.environ.get('CHROME') else {}
        b = await p.chromium.launch(args=['--no-sandbox'], **kw)

        async def device(cfg=CFG, mobile=False):
            c = await b.new_context(**(p.devices['iPhone 13'] if mobile else {'viewport': {'width': 1280, 'height': 900}}))
            pg = await c.new_page()
            if lunar:
                await pg.route('**/lunar-javascript@1.7.8/lunar.js', lambda r: r.fulfill(body=lunar, content_type='application/javascript'))
            await pg.route('https://fonts.googleapis.com/**', lambda r: r.fulfill(body='', content_type='text/css'))
            await pg.route('**/config.js', lambda r: r.fulfill(body=cfg, content_type='application/javascript'))
            pg.on('pageerror', lambda e: errs.append(str(e)))
            return c, pg

        c, pg = await device("window.JIAMING_BACKEND={url:''};")
        await pg.goto(URL); await pg.wait_for_timeout(2000)
        expect('還沒設定' in await pg.inner_text('#v-state'), '未設定網址時顯示提示')
        await c.close()

        _, A = await device()
        await A.goto(URL); await A.wait_for_timeout(1500)
        await A.fill('#v-code', '0000'); await A.click('#v-code-go'); await A.wait_for_timeout(2000)
        expect('不正確' in await A.inner_text('#v-state'), '錯誤通關碼被拒')
        await A.fill('#v-code', '9999'); await A.click('#v-code-go'); await A.wait_for_timeout(2500)
        expect('擁有者' in await A.inner_text('#v-state'), '管理碼以擁有者身分進入')
        await A.fill('#v-giv', '寧芸'); await A.click('#v-add'); await A.wait_for_timeout(500)
        expect('稱呼' in await A.inner_text('#toast'), '沒填稱呼不能提名')
        await A.fill('#v-nick', '爸爸'); await A.press('#v-nick', 'Tab'); await A.wait_for_timeout(800)
        await A.click('#v-add'); await A.wait_for_timeout(800)
        await A.fill('#v-giv', '綺芸'); await A.click('#v-add'); await A.wait_for_timeout(800)
        await A.click('button[data-act=vote][data-val="1"] >> nth=0'); await A.wait_for_timeout(800)

        _, B = await device(mobile=True)
        await B.goto(URL); await B.wait_for_timeout(1500)
        await B.fill('#v-code', '1234'); await B.click('#v-code-go'); await B.wait_for_timeout(2500)
        expect('共 2 個名字' in await B.inner_text('#v-state'), '家人看得到 2 個提名')
        await B.fill('#v-nick', '阿嬤'); await B.press('#v-nick', 'Tab'); await B.wait_for_timeout(800)
        await B.click('button[data-act=vote][data-val="-1"] >> nth=1'); await B.wait_for_timeout(600)
        await B.fill('.cmt >> nth=0', '好聽'); await B.press('.cmt >> nth=0', 'Enter'); await B.wait_for_timeout(600)
        await B.fill('#v-giv', '語書'); await B.click('#v-add'); await B.wait_for_timeout(800)
        rm = await B.eval_on_selector_all('[data-act=rm]', 'e=>e.map(x=>x.textContent)')
        expect(rm == ['撤回提名'], '家人只能撤回自己的提名')

        await A.wait_for_timeout(2500)
        cards = await A.eval_on_selector_all('#v-cards .card .nm', 'e=>e.map(x=>x.textContent)')
        expect(sorted(cards) == sorted(['張寧芸', '張綺芸', '張語書']), '擁有者自動看到家人的提名')
        rmb = A.locator('.card:has-text("張語書") [data-act=rm]')
        await rmb.click(); await rmb.click(); await A.wait_for_timeout(1200)
        cards = await A.eval_on_selector_all('#v-cards .card .nm', 'e=>e.map(x=>x.textContent)')
        expect('張語書' not in cards, '擁有者可移除別人的提名')

        dump = json.loads(urllib.request.urlopen(f'http://localhost:{MOCK_PORT}/dump').read())
        summary = dump.get('結果', [])
        expect(len(summary) == 3 and summary[1][0] in ('張寧芸', '張綺芸'), '「結果」工作表自動整理')
        expect(not errs, '沒有網頁錯誤 ' + '; '.join(errs))
        await b.close()

    print('\n' + ('全部通過' if not fails else f'{len(fails)} 項失敗'))
    return 1 if fails else 0


if __name__ == '__main__':
    mock, web = start_servers()
    try:
        code = asyncio.run(main())
    finally:
        mock.terminate(); web.terminate()
    sys.exit(code)
