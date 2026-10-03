# -*- coding: utf-8 -*-
r"""다크 세이비어 텍스트·글꼴 형식 (2026-10-03 역어셈블로 확정)

PROGRAM.004 (로우 워크램 0x00292000 에 통째 적재 — 파일 오프셋 = 주소 − 0x292000)
  · 글꼴 서술자 0x15908(A)·0x1591C(B)·0x15930(C), 각 20 B:
      u16 폭, u16 높이, u16 bpp, u16 첫코드(0x21), u32 비트맵, u32 폭표(글리프당 u8), u32 ?
    A = 11×13 1bpp 745자(대사창) · B = 11×11 같은 순서 앞 221자(작은 창) · C = 40×9 2bpp
    비트맵은 글리프 사이 패딩 없는 «연속 비트열»(MSB 우선, 글리프당 폭×높이 비트)
  · 문자 코드 = 글리프 번호 + 33, 10비트. 0‥32 는 제어(0 = 줄바꿈, 32 = 공백 …). 탁점·반탁점은 «앞에» 따로(゛シ = ジ).
    끝 코드 0x30A (RAM 변수 0x2BB4DA ← 파일 0x294DA).
  · 시스템 문장 0x2838C‥: [길이 u8][10비트 코드열 MSB 우선] (읽기 0x2A3E4C/52/88, 길이*8//10 글자)
  · 대사 허프만 트리 0x28EC4(RAM 0x2BAEC4): u16[이전 코드] = 트리 시작(표 기준 바이트 오프셋).
      트리 = 시작 바이트 MSB 부터 전위 순회 비트(0 = 가지, 1 = 잎).
      잎 기호 = 10비트, «트리 시작 바로 앞»에 거꾸로: k번째 잎(전위 순, 0부터) = 비트 [시작*8 − 10(k+1), +10)
      본문 비트: 가지에서 0 = 왼쪽(전위 다음), 1 = 왼쪽 서브트리를 건너뛰고 오른쪽. 해독기 0x2A5018.
      첫 문맥 = 끝 코드(0x30A), 끝 코드가 나오면 문장 끝.
PROGRAM.507/508/509/517 (0x002C0000 적재, 64 KB 고정)
  · 머리 u32[1] = 대사 표 주소. 표 = u16 블록 오프셋(블록당 256문장) → [길이 u8][허프만 비트열] 이어짐.
    문장 번호 n → 블록 n>>8, 블록 안 n&255 번째(길이로 건너뜀).
  · 대사 뒤에 다른 자료가 붙어 있다(머리 u32[11‥14]·내부 포인터 표가 가리킴) → 대사는 원래 구역 안에서만.
"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

BASE004 = 0x292000
FONT_DESC = {'A': 0x15908, 'B': 0x1591C, 'C': 0x15930}
SYS_TABLE = 0x2838C
TREE = 0x28EC4
TERM = 0x30A
FIRST = 33
NCTX = 779                       # 문맥 표 항목 = 이전 코드 0‥778(끝 코드 0x30A 까지). 바로 뒤 u16 = 끝 코드 변수
TREE_END = 0x42C2                # 원본 트리 구역 끝(TREE 기준) — 그 뒤는 다른 자료
SCRIPTS = {'507': 1000, '508': 1179, '509': 422, '517': 515}     # 파일별 문장 수(길이 바이트·비트 사용량 전수 대조로 확정)
SCRIPT_BASE = 0x2C0000

HIRA = 'あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんぁぃぅぇぉっゃゅょ'
KATA = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲンァィゥェォッャュョ'
SYMS = 'ー゛゜、。！？・…「」／＋：※’'          # 120‥135 (2026-10-03 비트맵으로 확인 — 공백 글리프는 없다, 공백 = 코드 32)
LATIN = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
FIXED = '0123456789' + HIRA + KATA + SYMS + LATIN          # 글리프 0‥161
KANJI0 = len(FIXED)                                      # 162‥744 = 한자(대본 첫 등장 순) → work/text/glyphs.tsv


# ── 글꼴 ───────────────────────────────────────────────
def font_desc(p004, which='A'):
    o = FONT_DESC[which]
    w, h, bpp, first = struct.unpack_from('>4H', p004, o)
    bm, wt, x = struct.unpack_from('>3I', p004, o + 8)
    return dict(w=w, h=h, bpp=bpp, first=first, bitmap=bm - BASE004, widths=wt - BASE004, extra=x)


def glyph_count(p004, which='A'):
    d = font_desc(p004, which)
    return (d['widths'] - d['bitmap']) * 8 // (d['w'] * d['h'] * d['bpp'])


def read_glyph(p004, i, which='A'):
    """→ h×w uint8 배열(1 = 잉크)"""
    d = font_desc(p004, which); W, H = d['w'], d['h']; G = W * H
    b = np.unpackbits(np.frombuffer(p004, np.uint8, count=(d['widths'] - d['bitmap']), offset=d['bitmap']))
    return b[i * G:(i + 1) * G].reshape(H, W)


def write_glyph(buf, i, rows, which='A', width=None):
    """buf(bytearray)의 글리프 i 를 rows(h×w 0/1)로, 폭표도(주면)"""
    d = font_desc(buf, which); W, H = d['w'], d['h']; G = W * H
    start = d['bitmap'] * 8 + i * G
    flat = np.asarray(rows, np.uint8).reshape(-1)
    assert flat.size == G
    for k, v in enumerate(flat):
        bp = start + k; byte = bp >> 3; m = 0x80 >> (bp & 7)
        buf[byte] = (buf[byte] | m) if v else (buf[byte] & ~m & 0xFF)
    if width is not None:
        buf[d['widths'] + i] = width


# ── 글리프 ↔ 글자 ──────────────────────────────────────
def charmap():
    """글리프 번호 → 글자(한자는 work/text/glyphs.tsv, 없으면 «〈번호〉»)"""
    m = {i: c for i, c in enumerate(FIXED)}
    p = os.path.join(ROOT, 'work', 'text', 'glyphs.tsv')
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8'):
            if ln.startswith('#') or not ln.strip():
                continue
            f = ln.rstrip('\n').split('\t')
            if len(f) >= 2 and f[1]:
                m[int(f[0])] = f[1]
    return m


CTRL_NAMES = {0: 'n'}           # 줄바꿈은 {n}, 나머지 제어는 {코드}


def codes_to_text(codes, cmap=None):
    cmap = cmap or charmap(); out = []
    for c in codes:
        g = c - FIRST
        if c == 32:
            out.append('{_}')                     # 게임 공백(코드 32 = 글리프 −1)
        elif c < FIRST or g >= 745:
            out.append('{%s}' % CTRL_NAMES.get(c, c))
        else:
            out.append(cmap.get(g, '〈%d〉' % g))
    return ''.join(out)


# ── 10비트 레코드 (시스템 문장) ─────────────────────────
def bits10(payload, n=None):
    b = np.unpackbits(np.frombuffer(payload, np.uint8))
    cnt = len(payload) * 8 // 10 if n is None else n
    w = 1 << np.arange(9, -1, -1)
    return [int(x) for x in (b[:cnt * 10].reshape(cnt, 10) * w).sum(1)] if cnt else []


def sys_records(p004, start=SYS_TABLE, count=None):
    """[(오프셋, 코드열)] — 길이 0 이 나오거나 count 개까지"""
    out = []; p = start
    while (count is None or len(out) < count):
        n = p004[p]
        if n == 0 and count is None:
            break
        out.append((p, bits10(p004[p + 1:p + 1 + n])))
        p += 1 + n
    return out


# ── 허프만 ──────────────────────────────────────────────
def _bit(d, bp):
    return (d[bp >> 3] >> (7 - (bp & 7))) & 1


def _val10(d, bp):
    v = 0
    for k in range(10):
        v = v * 2 + _bit(d, bp + k)
    return v


def parse_tree(d, tb, start):
    """트리 시작(tb 기준 바이트) → (코드표 {기호: 비트문자열}, 트리 비트 수, 잎 수)"""
    pos = (tb + start) * 8; codes = {}; leaves = [0]

    def rec(prefix):
        nonlocal pos
        bit = _bit(d, pos); pos += 1
        if bit:
            k = leaves[0]; leaves[0] += 1
            codes[_val10(d, (tb + start) * 8 - 10 * (k + 1))] = prefix
        else:
            rec(prefix + '0'); rec(prefix + '1')
    rec('')
    return codes, pos - (tb + start) * 8, leaves[0]


def parse_trees(p004, tb=TREE):
    """원본 트리 구역 → {이전 코드: 코드표}, 오프셋 표, 구역 끝(tb 기준 바이트)
    구역 = [u16 오프셋 × NCTX(779 = 코드 0‥778)][u16 끝 코드 0x030A (RAM 0x2BB4DA, 코드가 리터럴로 읽음)][잎+트리 …]"""
    offs = list(struct.unpack_from('>%dH' % NCTX, p004, tb))
    trees = {}; hi = 0
    for prev, o in enumerate(offs):
        if o:
            codes, nbits, nleaf = parse_tree(p004, tb, o)
            trees[prev] = codes; hi = max(hi, o + (nbits + 7) // 8)
    return trees, offs, hi


class BitReader:
    def __init__(s, d, p):
        s.d, s.p, s.m = d, p, 0x80

    def get(s):
        r = 1 if s.d[s.p] & s.m else 0
        s.m >>= 1
        if not s.m:
            s.m = 0x80; s.p += 1
        return r


def huff_getchar(p004, rd, prev, tb=TREE):
    """게임 해독기(0x2A5018) 그대로"""
    start = tb + struct.unpack_from('>H', p004, tb + 2 * prev)[0]
    tree = BitReader(p004, start); leaf = 0
    while not tree.get():
        if rd.get() == 0:
            continue
        cnt = 1
        while cnt > 0:
            if tree.get():
                cnt -= 1; leaf -= 1
            else:
                cnt += 1
    return _val10(p004, start * 8 + (leaf - 1) * 10)


def huff_decode(p004, d, p, tb=TREE):
    """레코드 [길이][비트] → (코드열, 다음 레코드, 쓴 비트 수)"""
    n = d[p]; rd = BitReader(d, p + 1); prev = TERM; out = []
    while True:
        c = huff_getchar(p004, rd, prev, tb)
        if c == TERM:
            break
        out.append(c); prev = c
        assert len(out) < 1000 and rd.p <= p + 1 + n, ('해독 폭주', hex(p))
    used = (rd.p - (p + 1)) * 8 + {0x80: 0, 0x40: 1, 0x20: 2, 0x10: 3, 8: 4, 4: 5, 2: 6, 1: 7}[rd.m]
    return out, p + 1 + n, used


def huff_encode(trees, codes):
    """코드열(끝 코드 제외) → 비트문자열"""
    bits = []; prev = TERM
    for c in list(codes) + [TERM]:
        t = trees[prev]
        if c not in t:
            raise KeyError('문맥 %d 뒤에 %d 가 트리에 없다' % (prev, c))
        bits.append(t[c]); prev = c
    return ''.join(bits)


def pack_bits(s):
    s = s + '0' * (-len(s) % 8)
    return bytes(int(s[i:i + 8], 2) for i in range(0, len(s), 8))


def build_trees(corpus):
    """코드열 목록 → 문맥별 허프만 {prev: {기호: 비트}} (트리 모양은 직렬화와 같은 전위 순서)"""
    import heapq, collections, itertools
    freq = collections.defaultdict(collections.Counter)
    for codes in corpus:
        prev = TERM
        for c in list(codes) + [TERM]:
            freq[prev][c] += 1; prev = c
    shapes = {}
    for prev, cnt in freq.items():
        tie = itertools.count()
        h = [(n, next(tie), ('L', s)) for s, n in sorted(cnt.items())]
        heapq.heapify(h)
        while len(h) > 1:
            a = heapq.heappop(h); b = heapq.heappop(h)
            heapq.heappush(h, (a[0] + b[0], next(tie), ('N', a[2], b[2])))
        shapes[prev] = h[0][2]
    return shapes


def shape_codes(shape):
    out = {}

    def rec(n, pre):
        if n[0] == 'L':
            out[n[1]] = pre
        else:
            rec(n[1], pre + '0'); rec(n[2], pre + '1')
    rec(shape, '')
    return out


def serialize_trees(shapes, nctx=NCTX):
    """→ 표(nctx 항목) + 트리 구역 bytes, {prev: 코드표}. 트리 i 의 잎은 시작 바이트 바로 앞에 거꾸로."""
    head = 2 * nctx + 2                          # 표 + 끝 코드 u16
    bits = []                                   # 표 뒤 구역 비트 (0/1 문자)
    offs = [0] * nctx; codes = {}
    for prev in sorted(shapes):
        shape = shapes[prev]
        leaves = []; tbits = []

        def rec(n):
            if n[0] == 'L':
                tbits.append('1'); leaves.append(n[1])
            else:
                tbits.append('0'); rec(n[1]); rec(n[2])
        rec(shape)
        leafbits = ''.join(format(s, '010b') for s in reversed(leaves))
        cur = len(bits)
        startbit = cur + len(leafbits); startbit += -startbit % 8          # 시작은 바이트 경계
        pad = startbit - len(leafbits) - cur
        bits.extend('0' * pad); bits.extend(leafbits); bits.extend(tbits)
        o = head + startbit // 8
        assert o < 0x10000, '트리 표 오프셋이 u16 을 넘는다'
        assert prev < nctx, ('문맥 표 밖 코드', prev)
        offs[prev] = o; codes[prev] = shape_codes(shape)
    body = pack_bits(''.join(bits))
    return struct.pack('>%dH' % nctx, *offs) + struct.pack('>H', TERM) + body, codes


# ── 대사 파일 ───────────────────────────────────────────
def script_table(f):
    """→ (표 파일 오프셋, 블록 오프셋 목록)"""
    base = struct.unpack_from('>I', f, 4)[0] - SCRIPT_BASE
    nb = struct.unpack_from('>H', f, base)[0] // 2
    return base, list(struct.unpack_from('>%dH' % nb, f, base))


def script_messages(p004, f, count):
    """→ [(번호, 오프셋, 코드열)], 대사 구역 끝"""
    base, blocks = script_table(f); out = []
    for b, o in enumerate(blocks):
        p = base + o
        for k in range(256):
            n = b * 256 + k
            if n >= count:
                break
            codes, nxt, used = huff_decode(p004, f, p)
            assert (f[p] - 1) * 8 < used <= f[p] * 8, ('길이 바이트 불일치', n)
            out.append((n, p, codes)); p = nxt
        if b + 1 < len(blocks):
            assert p == base + blocks[b + 1], ('블록 경계 불일치', b)
    return out, p
