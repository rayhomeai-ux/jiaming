import json, os
from pathlib import Path
RAW = Path(os.environ.get('RAW', Path(__file__).resolve().parents[1] / 'raw'))
D = json.load(open(RAW / 'fate' / 'resources' / 'character.json', encoding='utf-8'))
IDX = {}
for x in D:
    IDX.setdefault(x['char'], x)   # first record
GIRL = set('''安宜宥寧容宸家宣嘉蓉芸芯芷芮苡若苓茵荷莉菁菲萱萍葳蓁蕙薇蕾藍蘭茜芊芃芙蔓蓓葶菱茹莞蘋蘊芝芳英萃茗蔚蓮
禾秀秋穎穗秦稚程穆稼米粲粹精木林杉柔柚桐榕楓楠樺槿棠梓樂楷榆杏采彬森楨柏
紫綺純素紗綸縈絮綾緹綠維絹紋縵綵繪繡紜絲彤彩彥裕裳帆希
玥珊珍玲珈琪琳瑜瑄瑀瑋瑤璇璟瓊琦珮瑾環璐琬瑩瑞瑢璦璿琇鈺銀鈴錦
恩思怡悅慧惠慈愛語詩詠諭謙詡誼雅雯霏霓露雪晴晨昕曦晏時晞昀昱映暄曉
婷妍妤婕嫣媛姿娟婉嬿婧嫻文予云允方心丹欣歆庭真貞品馨書夏宛羽翎翊靜青菁聿立舒筠箏簡笙妮亭華
凝潔涵沛清沁溪渝蘅蘿薰馥韶儀伶佳伊依倩可如意卉喬采葦芹苑茉芩荻菀葭蓀蒨藝藹蘩
珺琤瑗瑒琰瓔璞璘熙鑫寶寰寀宓宬宴宙宇宏寬睿穠穹究竺笛箐簫籃籟織綏絃緣縝綿繹纖紈約紳紓
和佑祐禎祺禧福祥祈嫚媞婭娉嫿瀅灩澄澐沐洛涓淇淳湘湄漪瀞潼汐
文雯斐斌晰旻昊晉景暖暘曜朗朋望月有服
如嫺嬋娜娥嫦婕媚'''.replace('\n',''))
def info(c):
    x = IDX.get(c)
    if not x: return None
    return dict(c=c, k=x.get('kangxi_stroke'), wx=x.get('wu_xing'), rad=x.get('radical'), py=x.get('pinyin'))
# 生肖馬 字根
XI = set('艸禾米麥豆宀冖木糸衣巾彡玉金羊')
JI = set('子水冫雨田車心肉牛丑')
def zodiac(c):
    r = IDX[c].get('radical')
    if r in JI: return '忌'
    if r in XI: return '喜'
    return '中'

import gzip
K = json.load(gzip.open(RAW / 'shunshi-kangxi-core' / 'data' / 'chars.json.gz'))['chars']
def strokes(c):
    a = IDX[c]['kangxi_stroke'] if c in IDX else None
    b = K.get(c, {}).get('kx')
    if a is not None and b is not None and a == b: return a, 'ok'
    if a is None and b is not None: return b, 'one-source'
    return (a or b), f'conflict {a}/{b}'
def rad(c):
    if c in IDX and IDX[c].get('radical'): return IDX[c]['radical']
    return K.get(c, {}).get('rad')
def zodiac(c):
    r = rad(c)
    if r in JI: return '忌'
    if r in XI: return '喜'
    return '中'
def wuxing(c):
    return (IDX[c]['wu_xing'] if c in IDX else None), K.get(c, {}).get('wx')
