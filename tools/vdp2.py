# -*- coding: utf-8 -*-
r"""VDP2 NBG0/NBG1 셀 면 렌더(이 게임 설정: 1워드 이름, CNSM=1, 보충 +0x3000, 면 64×64, 지도 0x7C000/0x7E000) — 회색조(값×17 / 256색은 값 그대로)"""
import struct, numpy as np


def plane(V, mapaddr, bpp, base=0x3000, cols=64, rows=64):
    img = np.zeros((rows * 8, cols * 8), np.uint8); cells = {}
    for cy in range(rows):
        for cx in range(cols):
            pn = struct.unpack_from('>H', V, mapaddr + (cy * 64 + cx) * 2)[0]
            ch = (pn & 0xfff) + base
            if bpp == 4:
                c = np.frombuffer(V[ch * 32:ch * 32 + 32], np.uint8); px = np.stack([c >> 4, c & 15], 1).reshape(8, 8) * 17
                cells[(cx, cy)] = V[ch * 32:ch * 32 + 32]
            else:
                c = np.frombuffer(V[ch * 32:ch * 32 + 64], np.uint8); px = c.reshape(8, 8)
                cells[(cx, cy)] = V[ch * 32:ch * 32 + 64]
            img[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8] = px
    return img, cells
