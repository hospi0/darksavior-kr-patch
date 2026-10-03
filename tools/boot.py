# -*- coding: utf-8 -*-
r"""PROGRAM.506(타이틀·데이터 관리, 0x06030000 적재) 한글화 (2026-10-03)
  글꼴: 파일 0x227E4‥, 글자당 128 B = 16×16 4bpp «열 우선»(전치) 저장, 음영·외곽선을 미리 그림. 코드 = 번호 + 33. 221자:
    0‥119 = 본편과 같은 숫자·가나 / 120‥124 ー／：゛゜ / 125‥150 A‥Z / 151‥176 a‥z / 177‥181 Ⅰ‥Ⅴ /
    182‥ 한자(続消本面化体初画接期保存記録) 196 ？ 197‥218 한자 219 。 220 邸
  문자열 표: 0x29800‥0x29D22, 레코드 [u16 길이(바이트, &0xFFFE)][u16 코드 × 길이/2][u16 0] — 찾기 함수(0x06033C0E)가 길이로 건너뛴다.
  ★전면 한글화: 가나·한자 칸(10‥119, 182‥218 중 ？ 빼고, 220)을 전부 한글 자원으로. 숫자·영문·ー／：？。은 남긴다.
  한글 글리프 = 갈무리14 BDF, 채움 2 + 바깥 1px 외곽선 7 (기본 규칙).
"""
import os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'work', 'text'))
import dsfmt as D, gfx

FONT = 0x227E4; NGLYPH = 221
WIDTHS = 0x29664                 # 글자별 폭(u8 × 221, 가변폭) — 한글 칸은 글리프 실제 폭(외곽선 포함)으로 (2026-10-03 실기: 안 고치면 오른쪽이 잘림)
TABLE, TABLE_END = 0x29800, 0x29D22
T = list(D.FIXED[:120]) + list('ー／：゛゜') + list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + list('abcdefghijklmnopqrstuvwxyz') \
    + list('ⅠⅡⅢⅣⅤ') + list('続消本面化体初画接期保存記録？始号港城下水道地鉱山古代遺跡空容量必要管理他。邸')
REV = {c: i for i, c in enumerate(T)}
POOL = list(range(10, 120)) + [i for i in range(182, 219) if i != 196] + [220]


def strings(f, count=None):
    out = []; p = TABLE
    while (p < TABLE_END) if count is None else (len(out) < count):
        ln = struct.unpack_from('>H', f, p)[0] & 0xFFFE
        codes = list(struct.unpack_from('>%dH' % (ln // 2), f, p + 2))
        assert struct.unpack_from('>H', f, p + 2 + ln)[0] == 0
        out.append(codes); p += ln + 4
    assert count is not None or p == TABLE_END, hex(p)
    return out


def text(codes):
    return ''.join(T[c - 33] if 33 <= c < 33 + len(T) else ' ' if c == 32 else '{%d}' % c for c in codes)


def visual_len(codes):
    return sum(1 for c in codes if c not in (33 + REV['゛'], 33 + REV['゜']))



def glyph16(ch):
    a, ox, oy = gfx.bdf_glyph('Galmuri14', ch)
    ys = np.nonzero(a.any(1))[0]; xs = np.nonzero(a.any(0))[0]
    a = a[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]
    assert a.shape[0] <= 14 and a.shape[1] <= 14, (ch, a.shape)
    m = np.zeros((16, 16), np.uint8)
    y = 1 + (14 - a.shape[0]) // 2; x = 1 + (14 - a.shape[1]) // 2
    m[y:y + a.shape[0], x:x + a.shape[1]] = a
    g = np.zeros((16, 16), np.uint8)
    g[gfx.outline(m.astype(bool))] = 7; g[m == 1] = 2
    return g


def put_glyph(buf, k, g):
    t = g.T.reshape(-1)                       # 열 우선 저장
    buf[FONT + k * 128:FONT + k * 128 + 128] = bytes((int(t[i]) << 4) | int(t[i + 1]) for i in range(0, 256, 2))
    buf[WIDTHS + k] = int(np.nonzero(g.any(0))[0][-1]) + 1


def build(f, kr):
    S = strings(f)
    syl = sorted({c for v in kr.values() if v for c in v if '가' <= c <= '힣'})
    assert len(syl) <= len(POOL), ('506 한글 음절 %d > 칸 %d' % (len(syl), len(POOL)))
    assert len(syl) + 1 <= len(POOL)
    kmap = dict(zip(syl, POOL))
    blank = POOL[len(syl)]                     # ★한글 문자열의 공백 = 빈 글리프(폭 6) — 코드 32 는 오른쪽 맞춤 계산에서 빠져 끝 글자가 칸 밖으로 밀려 잘렸다(2026-10-03 실기 «제일러즈 항»)
    buf = bytearray(f)
    for ch, k in kmap.items():
        put_glyph(buf, k, glyph16(ch))
    buf[FONT + blank * 128:FONT + blank * 128 + 128] = bytes(128); buf[WIDTHS + blank] = 6
    table = bytearray(); log = []
    for i, codes in enumerate(S):
        s = kr.get(i)
        if s:
            new = []
            for ch in s:
                if ch == ' ':
                    new.append(blank + 33)
                elif ch in kmap:
                    new.append(kmap[ch] + 33)
                elif ch in REV and ch not in '゛゜' and REV[ch] not in POOL:
                    new.append(REV[ch] + 33)
                else:
                    raise SystemExit('⛔506 글꼴에 없는 글자 %r (%d: %s)' % (ch, i, s))   # 인코딩 누락 = 빌드 에러
            if visual_len(new) > visual_len(codes):
                log.append('⚠%d 원문 %d칸 → %d칸: %s' % (i, visual_len(codes), visual_len(new), s))
            codes = new
        table += struct.pack('>H', len(codes) * 2) + struct.pack('>%dH' % len(codes), *codes) + b'\0\0'
    room = TABLE_END - TABLE
    assert len(table) <= room, ('506 문자열 표 넘침', len(table), room)
    buf[TABLE:TABLE_END] = bytes(table) + bytes(room - len(table))
    # 되읽기
    back = strings(bytes(buf), len(S))
    for i, c in enumerate(back):
        if kr.get(i):
            assert text(c).replace('　', ' ') is not None and len(c) == len(kr[i]), ('되읽기 불일치', i)
    return bytes(buf), len(syl), len(table), room, log
