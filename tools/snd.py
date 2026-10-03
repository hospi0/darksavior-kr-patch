# -*- coding: utf-8 -*-
r"""PROGRAM.439(사운드 테스트 등, 0x060A0000 적재) — 글꼴·문자열 (2026-10-03)
  글꼴: 파일 0xC640‥, 글자당 128 B = 16×16 4bpp 행 우선, 음영 1‥7(가변폭은 코드가 잉크 폭으로 잴 것으로 추정), «화면에 처음 나오는 순서».
  문자열: 0x2FDA0‥0x30098, [1바이트 글자 번호…][FF], 다음 문자열 전 00 으로 정렬.
"""
G = ('ダークセイバサウンドテストBGMSETA'
     'Rボタで演奏終了0123456789プロ'
     'グCシディッツ号〜ビラ脱走H L戦闘ジェ'
     'ズ港黒い町狂気の支配者ルリゲ所長マ罠、ャ'
     'ゾJO囚人秘密組織緊迫糸奈落恐怖渦巻く陰'
     '謀拷問追詰められてキ監獄城古代ア流砂遺跡'
     '悪夢はぐる邸に激コNPKチナVilan破'
     '壊屍を超え踊ちゃん青子感何かが起きブフョ'
     '危険な前兆ュヤ友情剣抜看守絶対服従カパ巨'
     '大伝説胸騒ぎ時計塔ホム決唸ソ士休息涙贈り'
     '物銀ユIfもし違う生あった勝利オet’s'
     'o(ゴ)エ応援歌孤高・★レモノ'
     'だまD音楽読み込す')               # 235‥243 — 0x30098 문자열(「ただいまCDから音楽データを読み込んでいます」)만 쓴다
FONT = 0xC640; STR0, STR1 = 0x2FDA0, 0x300B0          # ★마지막 문자열이 0x30098‥0x300AE(포인터 0x301EC) — 끝 표지가 아니었다
NG = 244
assert len(G) == NG, len(G)


def strings(d):
    out = []; p = STR0
    while p < STR1:
        if d[p] == 0:
            p += 1; continue
        q = d.index(b'\xff', p); out.append((p, list(d[p:q]))); p = q + 1
    return out


def text(s):
    return ''.join(G[i] if i < len(G) else '{%d}' % i for i in s)


import struct
import numpy as np
B = 0x60A0000
PTRS = list(range(0x300B0, 0x301C0, 4)) + list(range(0x301D8, 0x301F0, 4))   # 74개
SPACE = G.index(' ')


def glyph_bytes(d, k):
    return d[FONT + k * 128:FONT + k * 128 + 128]


def hangul16(ch):
    """갈무리14 + «조건부 세로 덧대기»: 잉크 아래 칸이 비어 있고 그 아래도 비어 있을 때만 1px 덧댄다(1px 간격은 안 막음).
    ★이 화면은 글자를 정수가 아닌 배율로 늘려 그려 원본 행 일부를 건너뛴다 → 1px 가로획이 빠지거나 점으로 남았다(2026-10-03 실기).
    ⛔갈무리7 2배 확대는 투박해서 실패(사용자 «쓰레기가 됐음»). 채움 7만(테두리 2 는 이 팔레트에서 밝은 회색 줄무늬)."""
    import gfx
    a, ox, oy = gfx.bdf_glyph('Galmuri14', ch)
    ys = np.nonzero(a.any(1))[0]; xs = np.nonzero(a.any(0))[0]; a = a[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]
    # ★그리는 코드가 «글리프 시작 − 8 B»(한 행 앞)부터 16행을 읽는다 → 앞 글자의 15행이 이 글자 위에 찍히고 자기 15행은 안 그려진다(2026-10-03 FB 대조).
    #   그래서 잉크는 0‥14행에만, 15행은 항상 0.
    m = np.zeros((16, 16), np.uint8); y = (14 - a.shape[0]) // 2; x = 1 + (14 - a.shape[1]) // 2
    m[y:y + a.shape[0], x:x + a.shape[1]] = a
    add = np.zeros_like(m)
    for yy in range(14):
        add[yy + 1] = m[yy] & (1 - m[yy + 1]) & (1 - (m[yy + 2] if yy + 2 < 16 else 0))
    m = m | add
    m[15] = 0
    g = np.zeros((16, 16), np.uint8); g[m == 1] = 7
    t = g.reshape(-1)
    return bytes((int(t[i]) << 4) | int(t[i + 1]) for i in range(0, 256, 2))


def build(d, kr):
    addrs = [struct.unpack_from('>I', d, a)[0] - B for a in PTRS]
    order = sorted(set(addrs))                          # 번역 번호 = 저장 순서
    old = {a: list(d[a:d.index(b'\xff', a)]) for a in order}
    new_txt = {}
    for i, a in enumerate(order):
        t = kr.get(i)
        new_txt[a] = t if t else ''.join(G[x] for x in old[a])
    chars = ['']                                        # ★0번 = 빈 칸(안 씀) — 0번 글자의 «한 행 앞»은 글꼴 밖 변수라 찌꺼기가 찍혔다
    for a in order:
        for c in new_txt[a]:
            if c not in chars:
                chars.append(c)
    assert len(chars) <= NG, ('사운드 테스트 글자 %d > %d' % (len(chars), NG))
    idx = {c: i for i, c in enumerate(chars)}
    out = bytearray(d)
    for c, i in idx.items():
        if c == '':
            gb = bytes(128)
        elif '가' <= c <= '힣':
            gb = hangul16(c)
        else:
            assert c in G, ('사운드 테스트 글꼴에 없는 글자', c)   # 인코딩 누락 = 빌드 에러
            gb = glyph_bytes(d, G.index(c))[:120] + bytes(8)   # ★원본 글리프도 15행을 비운다 — 자기 15행은 안 그려지고 다음 글자 위에만 찍힌다(n·R 세리프 → 파·튼 위 점, 2026-10-03)
        out[FONT + i * 128:FONT + i * 128 + 128] = gb
    blob = bytearray(); newaddr = {}
    for a in order:
        if len(blob) % 2:
            blob.append(0)
        newaddr[a] = STR0 + len(blob)
        blob += bytes(idx[c] for c in new_txt[a]) + b'\xff'
    room = STR1 - STR0
    assert len(blob) <= room, ('사운드 테스트 문자열 넘침', len(blob), room)
    out[STR0:STR1] = bytes(blob) + bytes(room - len(blob))
    for p, a in zip(PTRS, addrs):
        struct.pack_into('>I', out, p, B + newaddr[a])
    return bytes(out), len(chars), len(blob), room
