# -*- coding: utf-8 -*-
r"""글꼴 A 한자 칸(162‥744) 판독 — 대사 줄을 크게 그려 Windows 일본어 OCR(winocr.ps1)로 읽고 칸마다 다수결 (2026-10-03)
  가나·부호는 일본어 폰트로, 한자 칸만 게임 글리프(4배)로 그린다. 글자 칸 간격 고정(PITCH) → OCR 글자 x 중심으로 칸 짚기.
  python tools/glyphid.py render     → work/ocr/img_*.png + slots.json
  powershell -ExecutionPolicy Bypass -File tools\winocr.ps1 -Dir work\ocr
  python tools/glyphid.py vote       → work/ocr/vote.tsv (글리프 \t 1위 \t 득표 \t 2위…)
  python tools/glyphid.py sheet      → work/ocr/sheet_*.png (글리프 3배 + 판정 글자, 눈 검토용)
"""
import collections, glob, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import dsfmt as D, disc

OUT = os.path.join(ROOT, 'work', 'ocr')
JFONT = r'C:\Windows\Fonts\BIZ-UDGothicB.ttc'
SC = 4; PITCH = 64; H = 80; PER_IMG = 60
DAK = {'゛': dict(zip('かきくけこさしすせそたちつてとはひふへほカキクケコサシスセソタチツテトハヒフヘホウ',
                     'がぎぐげござじずぜぞだぢづでどばびぶべぼガギグゲゴザジズゼゾダヂヅデドバビブベボヴ')),
       '゜': dict(zip('はひふへほハヒフヘホ', 'ぱぴぷぺぽパピプペポ'))}


def corpus():
    P = disc.local('D_SAVIOR/PROGRAM.004'); out = []
    for fn, cnt in D.SCRIPTS.items():
        F = disc.local('D_SAVIOR/PROGRAM.' + fn)
        out += [c for _, _, c in D.script_messages(P, F, cnt)[0]]
    out += [c for _, c in D.sys_records(P, count=228)]
    return P, out


def lines(codes):
    """코드열 → 줄 목록, 각 줄 = [(글자 또는 글리프번호)] (탁점은 다음 가나와 합침)"""
    res = []; cur = []; pend = None
    for c in codes:
        g = c - D.FIRST
        if c == 0:
            if cur: res.append(cur)
            cur = []; continue
        if c < D.FIRST or g >= 745:
            if c == 32: cur.append('　')
            continue
        if g < D.KANJI0:
            ch = D.FIXED[g]
            if ch in DAK:
                pend = ch; continue
            if pend:
                ch = DAK[pend].get(ch, ch); pend = None
            cur.append(ch)
        else:
            cur.append(g)
    if cur: res.append(cur)
    return res


def render():
    P, C = corpus(); os.makedirs(OUT, exist_ok=True)
    for f in glob.glob(os.path.join(OUT, 'img_*')): os.remove(f)
    font = ImageFont.truetype(JFONT, 44)
    L = [ln for c in C for ln in lines(c) if any(isinstance(x, int) for x in ln)]
    seen = set(); uniq = []
    for ln in L:
        k = tuple(ln)
        if k not in seen: seen.add(k); uniq.append(ln)
    slots = {}
    for i in range(0, len(uniq), PER_IMG):
        chunk = uniq[i:i + PER_IMG]; wmax = max(len(x) for x in chunk)
        im = Image.new('L', (40 + PITCH * wmax, 20 + H * len(chunk)), 255); dr = ImageDraw.Draw(im)
        name = 'img_%04d' % (i // PER_IMG); sl = []
        for r, ln in enumerate(chunk):
            y = 10 + r * H; row = []
            for k, x in enumerate(ln):
                x0 = 20 + k * PITCH
                if isinstance(x, int):
                    g = D.read_glyph(P, x)
                    big = Image.fromarray(((1 - g) * 255).astype(np.uint8)).resize((11 * SC, 13 * SC), Image.NEAREST)
                    im.paste(big, (x0 + 8, y + 8))
                    row.append(x)
                else:
                    dr.text((x0 + 8, y + 10), x, font=font, fill=0); row.append(None)
            sl.append(row)
        im.save(os.path.join(OUT, name + '.png')); slots[name] = sl
    json.dump(slots, open(os.path.join(OUT, 'slots.json'), 'w'))
    print('줄', len(uniq), '그림', len(slots))


def vote():
    slots = json.load(open(os.path.join(OUT, 'slots.json')))
    V = collections.defaultdict(collections.Counter)
    for name, sl in slots.items():
        p = os.path.join(OUT, name + '.txt')
        if not os.path.exists(p): continue
        for ln in open(p, encoding='utf-8'):
            f = ln.rstrip('\n').split('\t')
            if len(f) < 5: continue
            word, x, y, w, h = f[0], *map(float, f[1:])
            r = int((y + h / 2 - 10) // H)
            if not (0 <= r < len(sl)): continue
            n = len(word)
            for j, ch in enumerate(word):                 # 단어 상자를 글자 수로 나눠 칸 짚기(대략)
                cx = x + w * (j + 0.5) / n
                k = int((cx - 20) // PITCH)
                if 0 <= k < len(sl[r]) and sl[r][k] is not None and '\u4e00' <= ch <= '\u9fff' or ch in '々':
                    if 0 <= k < len(sl[r]) and sl[r][k] is not None:
                        V[sl[r][k]][ch] += 1
    with open(os.path.join(OUT, 'vote.tsv'), 'w', encoding='utf-8') as o:
        for g in range(D.KANJI0, 745):
            c = V.get(g, collections.Counter())
            tot = sum(c.values()); top = c.most_common(3)
            o.write('%d\t%s\t%d\t%d\t%s\n' % (g, top[0][0] if top else '', top[0][1] if top else 0, tot,
                                              ' '.join('%s%d' % t for t in top[1:])))
    print('판정', sum(1 for g in range(D.KANJI0, 745) if V.get(g)), '/', 745 - D.KANJI0)


def sheet(src='vote.tsv'):
    P = disc.local('D_SAVIOR/PROGRAM.004')
    rows = [ln.rstrip('\n').split('\t') for ln in open(os.path.join(OUT, src), encoding='utf-8')]
    font = ImageFont.truetype(JFONT, 30); sm = ImageFont.truetype(JFONT, 12)
    per = 120; cols = 12
    for s in range(0, len(rows), per):
        part = rows[s:s + per]
        im = Image.new('L', (cols * 80, ((len(part) + cols - 1) // cols) * 64), 255); dr = ImageDraw.Draw(im)
        for i, r in enumerate(part):
            g = int(r[0]); x = (i % cols) * 80; y = (i // cols) * 64
            gl = D.read_glyph(P, g)
            im.paste(Image.fromarray(((1 - gl) * 255).astype(np.uint8)).resize((33, 39), Image.NEAREST), (x + 2, y + 14))
            dr.text((x + 38, y + 16), r[1] or '?', font=font, fill=0)
            dr.text((x + 2, y + 1), str(g), font=sm, fill=0)
        im.save(os.path.join(OUT, 'sheet_%d.png' % (s // per)))


if __name__ == '__main__':
    {'render': render, 'vote': vote, 'sheet': sheet}[sys.argv[1]]()
