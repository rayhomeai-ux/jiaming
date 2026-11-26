# Build data files for the naming site.
import sys, json, gzip, re, glob, os, unicodedata
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from chars import IDX, K, GIRL
import opencc
from pypinyin import pinyin, lazy_pinyin, Style
s2t = opencc.OpenCC('s2t'); t2s = opencc.OpenCC('t2s')
OUT = os.environ.get('OUT', str(ROOT))  # 輸出 chars/pairs/poems/words.json 的位置

def big5_level(c):
    try: b = c.encode('big5')
    except Exception: return 0
    if len(b) != 2: return 0
    v = int.from_bytes(b, 'big')
    if 0xA440 <= v <= 0xC67E: return 1
    if 0xC940 <= v <= 0xF9D5: return 2
    return 0

TONE = {'ā':('a',1),'á':('a',2),'ǎ':('a',3),'à':('a',4),'ē':('e',1),'é':('e',2),'ě':('e',3),'è':('e',4),
        'ī':('i',1),'í':('i',2),'ǐ':('i',3),'ì':('i',4),'ō':('o',1),'ó':('o',2),'ǒ':('o',3),'ò':('o',4),
        'ū':('u',1),'ú':('u',2),'ǔ':('u',3),'ù':('u',4),'ǖ':('v',1),'ǘ':('v',2),'ǚ':('v',3),'ǜ':('v',4),'ü':('v',0),
        'ń':('n',2),'ň':('n',3),'ǹ':('n',4),'ḿ':('m',2)}
def num(py):
    t = 5; out = ''
    for ch in py:
        if ch in TONE:
            b, tt = TONE[ch]; out += b
            if tt: t = tt
        else: out += ch
    return out + str(t)

NORM = {'氵':'水','忄':'心','扌':'手','艹':'艸','犭':'犬','礻':'示','衤':'衣','王':'玉','阝':'阜','灬':'火','钅':'金','纟':'糸','讠':'言','饣':'食','罒':'网','⺼':'肉'}
# 字形部件（生肖判斷用，人工整理，非完整）
HIDDEN = {'寧':'心','甯':'心','芯':'心','蕊':'心','德':'心','聽':'心','穗':'心','總':'心','想':'心',
          '好':'子','享':'子','厚':'子','李':'子','遊':'子','游':'子','郭':'子','承':'子','孝':'子','教':'子',
          '苗':'田','富':'田','福':'田','蕾':'田','雷':'田','畫':'田','嫿':'田','留':'田','番':'田','鈿':'田','蕃':'田','疇':'田','甜':'',
          '漢':'','冰':'','雯':'雨'}
TW_PY = {'媛':'yuàn'}  # 台灣讀音覆蓋

rows = []
for c, v in K.items():
    lv = big5_level(c)
    if not lv or v.get('kx') is None: continue
    f = IDX.get(c)
    k1 = v.get('kx'); k2 = f.get('kangxi_stroke') if f else None
    k = k2 if k2 else k1
    alt = k1 if (k2 and k1 and k1 != k2) else 0
    src = 2 if (k2 and k1 == k2) else 1
    r = (f.get('radical') if f and f.get('radical') else v.get('rad')) or ''
    r = NORM.get(r, r)
    w1 = (f.get('wu_xing') if f else None) or ''
    w2 = v.get('wx') or ''
    w = w1 or w2; walt = w2 if (w1 and w2 and w1 != w2) else ''
    py = TW_PY.get(c) or v.get('py') or ((f.get('pinyin') or [''])[0] if f else '')
    py = py.split(',')[0].strip()
    rows.append([c, k, alt, src, r, w, walt, py, num(py) if py else '', HIDDEN.get(c, ''), lv])
# add fate-only Big5 chars (e.g. traditional forms missing from shunshi)
have = {r[0] for r in rows}
for x in IDX.values():
    c = x['char']
    if c in have or not big5_level(c) or not x.get('kangxi_stroke'): continue
    py = (x.get('pinyin') or [''])[0]
    r = NORM.get(x.get('radical') or '', x.get('radical') or '')
    rows.append([c, x['kangxi_stroke'], 0, 1, r, x.get('wu_xing') or '', '', py, num(py) if py else '', HIDDEN.get(c, ''), big5_level(c)])
rows.sort(key=lambda r: (r[10], r[0].encode('big5')))
with open(f'{OUT}/chars.json', 'w', encoding='utf-8') as fo:
    fo.write('[\n' + ',\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n]\n')
print('chars', len(rows), os.path.getsize(f'{OUT}/chars.json'))
CH = {r[0]: r for r in rows}

# ---- pool for generator ----
pool_f = [c for c in json.load(open(ROOT / 'src' / 'data' / 'pool.json', encoding='utf-8')) if c in CH]
BOY = set('承恩宥廷品睿碩宇翔哲浩軒柏彥安晨皓杰傑宸澤叡昊祐佑庭鈞宏豪家俊志偉信誠凱文武鴻博霖霆霈峻崇嘉楷樂謙弘澔洋禹亦均允宣昱晏竣崴彬斌頡毅銘銓錚煜燁璟瀚宜立丞秉侑侃冠勛勳堯定岳峰帆恆振晉朗東杭楓正永江沐洛淳清濬灝炫煒熙琮琦瑋瑞璋甫祥禾程穎穆竑紹維羿翊翰聖胤致舟航良葳蔚衡言詮諺賢辰鋒鎧麒齊予書語景舒毓元暘曜駿騏驊譽')
pool_m = sorted(BOY & set(CH), key=lambda c: (CH[c][1], c))
POOLM_OUT = ROOT / 'src' / 'data' if Path(OUT).resolve() == ROOT else Path(OUT)
open(POOLM_OUT / 'pool_m.txt', 'w', encoding='utf-8').write(''.join(pool_m))
pool = sorted(set(pool_f) | set(pool_m), key=lambda c: (CH[c][1], c))
print('pool_f', len(pool_f), 'pool_m', len(pool_m), 'union', len(pool))

# ---- poems: lines containing >=2 pool chars ----
PS = set(pool)
lines = []; pairs = {}
BOOKORDER = {'诗经':0,'楚辞':1,'乐府诗集':2,'古诗三百首':3,'唐诗三百首':3,'宋词':4,'辞赋':5}
for fpath in sorted(glob.glob(str(Path(os.environ.get('RAW', HERE.parent / 'raw')) / 'gushi_namer' / 'dist' / 'json' / '*.json'))):
    if 'test' in fpath: continue
    for p in json.load(open(fpath, encoding='utf-8')):
        txt = re.sub(r'<[^>]+>', '\n', p.get('content') or '')
        for ln in re.split(r'[\n。！？；]', txt):
            ln = ln.strip().strip('　 ')
            if not ln or len(ln) > 40: continue
            tl = s2t.convert(ln)
            hit = sorted({ch for ch in tl if ch in PS})
            if len(hit) < 2: continue
            rec = [tl, s2t.convert(p.get('author') or '佚名'), s2t.convert(p.get('title') or ''), s2t.convert(p.get('book') or '')]
            idx = None
            for i, a in enumerate(hit):
                for b in hit[i+1:]:
                    key = a + b
                    rank = (BOOKORDER.get(p.get('book'), 6), len(tl))
                    if key not in pairs or rank < pairs[key][1]:
                        if idx is None:
                            lines.append(rec); idx = len(lines) - 1
                        pairs[key] = (idx, rank)
used = sorted({v[0] for v in pairs.values()})
remap = {o: n for n, o in enumerate(used)}
with open(f'{OUT}/poems.json', 'w', encoding='utf-8') as fo:
    fo.write('[\n' + ',\n'.join(json.dumps(lines[o], ensure_ascii=False) for o in used) + '\n]\n')
with open(f'{OUT}/pairs.json', 'w', encoding='utf-8') as fo:
    fo.write('[\n' + ',\n'.join(json.dumps([k, remap[v[0]]], ensure_ascii=False) for k, v in sorted(pairs.items())) + '\n]\n')
print('poem lines', len(used), os.path.getsize(f'{OUT}/poems.json'), 'pairs', len(pairs), os.path.getsize(f'{OUT}/pairs.json'))

# ---- common words for homophone flags ----
import jieba
jd = os.path.join(os.path.dirname(jieba.__file__), 'dict.txt')
words = {}
for ln in open(jd, encoding='utf-8'):
    w, f, *_ = ln.split(); f = int(f)
    if not re.fullmatch(r'[一-鿿]+', w): continue
    if (len(w) == 2 and f >= 20) or (len(w) == 3 and f >= 60):
        key = ' '.join(lazy_pinyin(w, style=Style.TONE3, neutral_tone_with_five=True)).replace('ü', 'v')
        tw = s2t.convert(w)
        words.setdefault(key, [])
        words[key].append((tw, f))
SURN = '陳林黃張李王吳劉蔡楊許鄭謝洪郭邱曾廖賴徐周葉蘇莊呂江何蕭羅高潘簡朱鍾游彭詹胡施沈余盧梁趙顏柯翁魏孫戴范方宋鄧杜傅侯曹薛丁卓阮馬董溫唐藍石蔣古紀姚連馮歐程湯田康姜白汪鄒尤巫鐘黎涂龔嚴韓袁金童陸夏柳邵錢伍倪于譚駱熊任甘秦顧毛章史官萬俞雷粘饒司諸葛上'
SYL = {re.sub(r'\d', '', CH[c][8]) for c in list(pool) + [x for x in SURN if x in CH] if CH[c][8]}
def ok(key):
    return all(re.sub(r'\d', '', sy) in SYL for sy in key.split())
recs = []
for key, lst in words.items():
    if not ok(key): continue
    lst = sorted(set(lst), key=lambda x: (-x[1], x[0]))[:4]
    recs.append([key, ' '.join(t for t, _ in lst)])
with open(f'{OUT}/words.json', 'w', encoding='utf-8') as fo:
    fo.write('[\n' + ',\n'.join(json.dumps(r, ensure_ascii=False) for r in recs) + '\n]\n')
print('word keys', len(recs), os.path.getsize(f'{OUT}/words.json'))
