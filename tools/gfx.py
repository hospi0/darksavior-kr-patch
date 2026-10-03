# -*- coding: utf-8 -*-
r"""그림 글자 한글화 (2026-10-03)
  ① 메뉴(NOTE) 세로 탭 — PROGRAM.004 LZSS 블록 0x2629C, 셀 274‥337 = 탭 8장(16×32, 셀 2×4 열 우선):
     ジャク·アイテム·そうび·ステータス × (왼쪽판, 오른쪽판). 안쪽 x3‥12 · y3‥28 을 바탕 e 로 지우고 갈무리7 세로쓰기, 잉크 2.
  ② 지역 자막 — 대사 파일 507/508/509/517 자막 표(*(머리+0x38) 의 +0x14‥) → [4 B: ?,?,열,행][u16 길이][LZSS], 셀 열 우선.
     일본어 4종만 다시 그림(투명 0 바탕, 채움 c, 바깥 1px 테두리 f — 기본 규칙). 영문 크레딧·Parallel 제목은 둔다.
  다시 압축한 길이가 원래 길이보다 크면 빌드 실패(블록이 빈틈없이 이어져 있다).
"""
import hashlib, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import bdf, disc, lzss

TAB_BLOCK = 0x2629C
TAB_FIRST = 274
TAB_KR = ['잭', '아이템', '장비', '상태']          # ジャク·アイテム·そうび·ステータス
# 자막: 원본 풀린 내용 md5 앞 12자리 → 한글 두 줄
CAPTION_KR = {}                                   # caption_table() 첫 실행 때 채운다(아래 JP_CAPTIONS 순서로)
JP_CAPTIONS = [('ジェイラーズ島', 'ビラン上陸 数時間前', '제이라즈 섬', '비란 상륙 몇 시간 전'),
               ('デクスキャリバー監獄城内', 'クルトリーゲン研究所', '덱스캘리버 감옥성 내부', '쿠르트리겐 연구소'),
               ('ジェイラーズ島', 'リュー・ヤー上陸 数時間前', '제이라즈 섬', '류 야 상륙 몇 시간 전'),
               ('デボス', '', '데보스', '')]


def cells_to_img(raw, cols, rows, colmajor=True):
    n = len(raw) // 32; img = np.zeros((rows * 8, cols * 8), np.uint8)
    for k in range(n):
        c = np.frombuffer(raw[k * 32:k * 32 + 32], np.uint8); px = np.stack([c >> 4, c & 15], 1).reshape(8, 8)
        x, y = (k // rows, k % rows) if colmajor else (k % cols, k // cols)
        if y < rows and x < cols:
            img[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = px
    return img


def img_to_cells(img, n, rows, colmajor=True):
    cols = img.shape[1] // 8; out = bytearray()
    for k in range(n):
        x, y = (k // rows, k % rows) if colmajor else (k % cols, k // cols)
        px = img[y * 8:y * 8 + 8, x * 8:x * 8 + 8].reshape(-1)
        out += bytes((int(px[i]) << 4) | int(px[i + 1]) for i in range(0, 64, 2))
    return bytes(out)


def bdf_glyph(font, ch):
    """→ 잉크만 잘라 낸 0/1 배열"""
    g = bdf.load(font).get(ord(ch))
    assert g is not None, (font, ch)
    w, h, ox, oy, rows = g
    a = np.zeros((h, w), np.uint8)
    for i, r in enumerate(rows):
        v = int(r, 16); nb = len(r) * 4
        for x in range(w):
            a[i, x] = (v >> (nb - 1 - x)) & 1
    return a, ox, oy


def text_line(font, s, space=4, gap=1):
    """가로 한 줄 → 0/1 배열(베이스라인 맞춤)"""
    parts = []; top = 0; bot = 0
    for ch in s:
        if ch == ' ':
            parts.append(None); continue
        a, ox, oy = bdf_glyph(font, ch)
        parts.append((a, ox, oy)); top = max(top, a.shape[0] + oy); bot = min(bot, oy)
    H = top - bot; W = sum(space if p is None else p[0].shape[1] + max(p[1], 0) + gap for p in parts)
    img = np.zeros((H, max(W, 1)), np.uint8); x = 0
    for p in parts:
        if p is None:
            x += space; continue
        a, ox, oy = p; y = top - (a.shape[0] + oy); x += max(ox, 0)
        img[y:y + a.shape[0], x:x + a.shape[1]] |= a; x += a.shape[1] + gap
    return img


def make_tab(orig, label):
    # ★오른쪽판 탭은 안쪽이 1px 왼쪽(x1‥13) — 고정 사각형으로 지우면 x2 잉크가 «점 찌꺼기»로 남는다(2026-10-03 실기).
    #   잉크(2·9)를 색으로 전부 지우고, 원래 잉크 중심 열에 글자 칸(7px)을 «같은 x»로 세운다(글자마다 가운데 맞추면 비뚤비뚤).
    img = orig.copy(); body = img[2:30]
    iy, ix = np.nonzero(np.isin(body, (2, 9)))
    cx = (ix.min() + ix.max() + 1) / 2
    body[np.isin(body, (2, 9))] = 0xE
    gs = []
    for ch in label:
        a, ox, _ = bdf_glyph('Galmuri7', ch)
        ys = np.nonzero(a.any(1))[0]
        gs.append((a[ys[0]:ys[-1] + 1], ox))
    tot = sum(g.shape[0] for g, _ in gs); gap = (26 - tot) // (len(gs) + 1) if len(gs) > 1 else 0
    y = 3 + (26 - tot - gap * (len(gs) - 1)) // 2
    xc = int(round(cx - 3.5))
    for g, ox in gs:
        x0 = xc + ox
        reg = img[y:y + g.shape[0], x0:x0 + g.shape[1]]; reg[g == 1] = 2
        y += g.shape[0] + gap
    return img


def patch_tabs(p004):
    raw, end = lzss.decompress_block(p004, TAB_BLOCK)
    room = end - TAB_BLOCK - 2
    raw = bytearray(raw)
    for t in range(8):
        base = (TAB_FIRST + t * 8) * 32
        img = cells_to_img(bytes(raw[base:base + 256]), 2, 4)
        new = make_tab(img, TAB_KR[t % 4])
        raw[base:base + 256] = img_to_cells(new, 8, 4)
    comp = lzss.compress(bytes(raw))
    assert lzss.decompress(comp)[:len(raw)] == bytes(raw)
    assert len(comp) <= room, ('메뉴 블록 압축 넘침', len(comp), room)
    out = bytearray(p004)
    out[TAB_BLOCK:TAB_BLOCK + 2] = struct.pack('>H', len(comp))
    out[TAB_BLOCK + 2:TAB_BLOCK + 2 + len(comp)] = comp
    out[TAB_BLOCK + 2 + len(comp):end] = bytes(end - TAB_BLOCK - 2 - len(comp))   # 남는 곳 0 (다음 블록 시작은 그대로)
    return bytes(out), (len(comp), room)


def caption_entries(f):
    """[(레코드 오프셋, 머리 4 B, 풀린 내용, 블록 끝)]"""
    B = 0x2C0000; t = struct.unpack_from('>I', f, 0x38)[0] - B; out = []
    for v in struct.unpack_from('>16I', f, t)[5:]:
        if v == 0:
            continue
        if not (B < v < B + 0x10000):
            break
        p = v - B; raw, end = lzss.decompress_block(f, p + 4)
        out.append((p, f[p:p + 4], raw, end))
    return out


def outline(mask):
    m = np.pad(mask, 1); o = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            o |= np.roll(np.roll(m, dy, 0), dx, 1)
    return (o & ~m)[1:-1, 1:-1]


def draw_caption(cols, rows, l1, l2, font='Galmuri11-Bold'):
    W, H = cols * 8, rows * 8; img = np.zeros((H, W), np.uint8)
    lines = [l for l in (l1, l2) if l]
    band = H // max(1, len(lines))
    for i, s in enumerate(lines):
        t = text_line(font, s)
        assert t.shape[1] + 2 <= W, ('자막 줄이 칸보다 넓다', s, t.shape[1], W)
        y = i * band + (band - t.shape[0]) // 2; x = (W - t.shape[1]) // 2
        m = np.zeros((H, W), np.uint8); m[y:y + t.shape[0], x:x + t.shape[1]] = t
        img[outline(m.astype(bool))] = 0xF; img[m == 1] = 0xC
    return img


def jp_caption_hashes():
    """원본 일본어 자막 4종의 풀린 내용 md5 — 507·508·509·517 에서 그림 비교로 고정(2026-10-03 눈 확인 순서)"""
    return CAPTION_MD5


# 자막 원본 md5(앞 12) → JP_CAPTIONS 번호. tools/gfx.py --list 로 확인하고 적는다.
CAPTION_MD5 = {'bf24ec16ef8a': 0, '361a5bb8f5a6': 1, '2ab4cd3b609a': 2, '792b7d677fac': 3}   # 2026-10-03 그림 대조


# ③ 옵션 버튼(2026-10-03 스테이트로 찾음) — PROGRAM.004 블록 표 0x1B6B0 의 LZSS 블록, 풀면 768 B = 셀 12×2 «행 우선»(96×16).
#   눌림 상태마다 한 장씩: 메시지 3장(はやい·ふつう·おそい) · 사운드 2장(モノラル·ステレオ) · 윈도우 3장(明るい·暗い, 가운데는 밝기 막대).
#   버튼 안쪽 = 바탕 e · 글자 잉크 2. 안쪽 열(5‥13행이 전부 e/2)을 찾아 잉크를 지우고 갈무리7 로 가운데에 다시 쓴다.
OPT_BLOCKS = {0x1F170: ['빠름', '보통', '느림'], 0x1F2EE: ['빠름', '보통', '느림'], 0x1F474: ['빠름', '보통', '느림'],
              0x1F706: ['모노', '스테레오'], 0x1F85A: ['모노', '스테레오'],
              0x1FAE2: ['밝게', '어둡게'], 0x1FBF4: ['밝게', '어둡게'], 0x1FD04: ['밝게', '어둡게']}


def option_button(raw, labels, dx=0, dy=0):
    img = cells_to_img(raw, 12, 2, False)
    inner = np.isin(img[5:14], (0xE, 2)).all(0)
    runs = []; x = 0
    while x < 96:
        if inner[x]:
            x0 = x
            while x < 96 and inner[x]:
                x += 1
            if x - x0 >= 12:
                runs.append((x0, x))
        x += 1
    assert len(runs) == len(labels), ('옵션 버튼 수', runs, labels)
    for (x0, x1), lab in zip(runs, labels):
        reg = img[3:15, x0:x1]
        iy, ix = np.nonzero(reg == 2)                     # 원래 글자 중심(눌린 버튼은 1px 아래) 에 맞춘다
        cy = 3 + (iy.min() + iy.max() + 1) / 2; cx = x0 + (ix.min() + ix.max() + 1) / 2
        reg[reg == 2] = 0xE
        t = text_line('Galmuri7', lab)
        ys = np.nonzero(t.any(1))[0]; xs = np.nonzero(t.any(0))[0]; t = t[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]
        assert t.shape[1] <= x1 - x0 - 2, ('옵션 버튼 폭 넘침', lab, t.shape, x1 - x0)
        tx = x0 + (x1 - x0 - t.shape[1] + 1) // 2 + dx; ty = int(round(cy - t.shape[0] / 2)) + dy
        tx = min(max(tx, x0 + 1), x1 - 1 - t.shape[1]); ty = min(max(ty, 5), 13 - t.shape[0])   # 안쪽 위아래 여백 1px 이상
        sub = img[ty:ty + t.shape[0], tx:tx + t.shape[1]]; sub[t == 1] = 2
    return img_to_cells(img, 24, 2, False)


def patch_options(p004):
    out = bytearray(p004); log = []
    for blk, labels in OPT_BLOCKS.items():
        raw, end = lzss.decompress_block(p004, blk)
        assert len(raw) == 768, ('옵션 블록 아님', hex(blk), len(raw))
        room = end - blk - 2
        for dx, dy in ((0, 0), (0, -1), (1, 0), (-1, 0), (1, -1), (-1, -1)):   # 압축이 넘치면 1px 옮긴 배치
            new = option_button(raw, labels, dx, dy)
            comp = lzss.compress(new)
            if len(comp) <= room:
                break
        assert lzss.decompress(comp)[:768] == new
        assert len(comp) <= room, ('옵션 블록 압축 넘침', hex(blk), len(comp), room)
        out[blk:blk + 2] = struct.pack('>H', len(comp))
        out[blk + 2:blk + 2 + len(comp)] = comp
        out[blk + 2 + len(comp):end] = bytes(end - blk - 2 - len(comp))
        log.append((blk, len(comp), room, end))
    return bytes(out), log


def patch_captions(f):
    out = bytearray(f); log = []
    for p, h, raw, end in caption_entries(f):
        key = hashlib.md5(raw).hexdigest()[:12]
        if key not in CAPTION_MD5:
            continue
        j = CAPTION_MD5[key]; cols, rows = h[2] & 0x7F, h[3]
        img = draw_caption(cols, rows, JP_CAPTIONS[j][2], JP_CAPTIONS[j][3])
        new = img_to_cells(img, len(raw) // 32, rows)
        comp = lzss.compress(new); room = end - (p + 6)
        assert lzss.decompress(comp)[:len(new)] == new
        assert len(comp) <= room, ('자막 압축 넘침', hex(p), len(comp), room)
        out[p + 4:p + 6] = struct.pack('>H', len(comp))
        out[p + 6:p + 6 + len(comp)] = comp
        out[p + 6 + len(comp):end] = bytes(end - p - 6 - len(comp))
        log.append((hex(p), JP_CAPTIONS[j][2], len(comp), room))
    return bytes(out), log


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if '--list' in sys.argv:
        for fn in ('507', '508', '509', '517'):
            for p, h, raw, end in caption_entries(disc.local('D_SAVIOR/PROGRAM.' + fn)):
                print(fn, hex(p), h.hex(), len(raw), hashlib.md5(raw).hexdigest()[:12])
