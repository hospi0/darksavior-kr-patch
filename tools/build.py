# -*- coding: utf-8 -*-
r"""다크 세이버 한글 빌더 (2026-10-03 전량 번역 + 글꼴 칸 확장 판)
  work/text/darksavior_*.tsv 의 «번역» 열 → 코드열
    ① 글꼴 A 재배치: 옛 글꼴 B 자리(0x15944)부터 933칸 비트맵 + 폭 표(‥0x19E1E), 서술자 A·B ← 새 A
       숫자·부호·영문은 원래 번호 그대로, 한자 구역 기호 ↗↖↘💢💧♪ 보호, 한글·괄호는 나머지 칸(갈무리11)
    ② 시스템 문장(PROGRAM.004 0x2838C‥0x28EAF) 10비트 레코드 다시 쓰기
    ③ 문맥별 허프만 트리: 끝 코드 TERM = 글리프 수 + 33, 문맥 표 TERM+1 항목, 끝 코드 변수 = 표 바로 뒤
       (변수 주소를 담은 리터럴 4곳 0x1A44·0x2BB4·0x2C18·0x2C88 갱신)
       트리 본문 = 원래 구역 [표, 0x42C2) + 런타임 빈 곳 0x2D36C‥0x2DC06 두 토막(표 오프셋은 표 기준 u16)
    ④ 대사 파일 507·508·509·517 다시 부호화(원래 구역 안)
  ★번역문은 쓰는 순간 kr_rules 와 같은 squeeze(문장부호 뒤 공백 1칸 삭제)를 거친다.
  python tools/build.py              → 검사·요약만
  python tools/build.py --write      → work/out/ 트랙 1 (+cue·트랙 2 복사)
  python tools/build.py --install    → + F: 설치
"""
import csv, glob, hashlib, os, re, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.append(r'C:\claude\project\anearth-kr-patch\tools')
import numpy as np
import bdf, boot, disc, snd, dsfmt as D, extract as E, gfx, iso
sys.path.insert(0, os.path.join(ROOT, 'work', 'text'))

sys.stdout.reconfigure(encoding='utf-8')
OUT = os.path.join(ROOT, 'work', 'out')
F_DIR = r'F:\hospi\roms\ss roms\Dark Savior (Japan)'
TRACK1 = 'Dark Savior (Japan) (Track 1).bin'
FONT = 'Galmuri11'
CHOICE = 0x28EB0                # 예/아니오 선택지 u16 코드(はい·いいえ)
CHOICE_KR = ('예', '아니오')
SYS_END = 0x28EAF                # 원본 228번째 레코드 끝(그 뒤 0x28EAF‥ = 다른 자료: u32 0x002CFFFF 등)
PUNCT = {'!': '！', '?': '？', ',': '、', '.': '。', '~': 'ー', '-': 'ー', '…': '…', '·': '・'}
_PUNCT_ALL = ",.!?:;)]}'\"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥"
# ★이름 코드 {6:k} 의 「}」 뒤 공백은 띄어쓰기다 — 지우면 「류 본인」이 「류본인」(2026-10-03 실기)
_SQ = re.compile('([' + re.escape(_PUNCT_ALL) + '])(?<!\\{6:\\d\\})(?<!\\{6:\\d\\d\\})[ 　](?![ 　])')

# ── 글꼴 칸 확장(2026-10-03) ─────────────────────────
FONT_START = 0x15944             # 옛 글꼴 B 비트맵 자리(B 는 서술자를 A 로 돌려 써서 빈다)
FONT_END = 0x19E1E               # 글꼴 C 시작 — 여기까지 비트맵 + 폭 표
NGLYPH = 933                     # ceil(N·143/8) + N ≤ FONT_END − FONT_START (17,626 B)
PROT = {641: '↗', 642: '↖', 644: '↘', 734: '💢', 735: '💧', 736: '♪'}   # 한자 구역 안 기호(번역이 쓴다)
RECLAIM = set()                  # ⛔゛゜(121·122)는 돌려 쓰지 말 것 — 렌더러가 탁점 코드를 «폭 없이 다음 글자에 겹쳐» 특별 취급한다
                                 #   (2026-10-03 실기: 121번에 배정된 「남」 때문에 「남아서」가 「이남서」처럼 찍힘)
KEEP = [g for g in range(D.KANJI0) if not (10 <= g < 120) and g not in RECLAIM]
SLOT_POOL = [g for g in list(range(10, 120)) + sorted(RECLAIM) + list(range(D.KANJI0, NGLYPH)) if g not in PROT]
TERM = NGLYPH + D.FIRST          # 966 — 모든 글리프 코드(≤ 965) 다음
NCTX = TERM + 1                  # 문맥 표 = 이전 코드 0‥TERM
TERM_LITS = [0x1A44, 0x2BB4, 0x2C18, 0x2C88]   # 끝 코드 변수 주소 리터럴(각각 바로 뒤 +4 = 트리 표 주소 리터럴)
SEG2 = (0x2D370, 0x2DC00)        # 트리 둘째 토막(RAM 0x2BF370‥0x2BFC00) — 파일·스테이트 15개 모두 0
                                 # ⛔0x2BF36C 는 4바이트 변수(VDP2 설정 루틴 0x2A6CA8‥ 이 쓴다), 0x2BFC00‥ 은 변수들 — 그 사이엔 리터럴 0개
TREE_END_OLD = 0x42C2


def ink_width(rows_):
    """부호 글리프 폭 = 잉크 오른쪽 끝 + 2"""
    cols = [x for r in rows_ for x, v in enumerate(r) if v]
    return min(11, (max(cols) + 2) if cols else 4)


def squeeze(t):
    return _SQ.sub(r'\1', t)


def load_rows():
    rows = []
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'darksavior_*.tsv'))):
        with open(p, encoding='utf-8', newline='') as fh:
            for r in csv.DictReader(fh, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='\\'):
                rows.append(r)
    return rows


def is_hangul(ch):
    return '가' <= ch <= '힣'


def assign_slots(rows):
    """번역문 한글 음절 + 글꼴에 없는 괄호 → 칸"""
    need = sorted({ch for r in rows for ch in squeeze(r['번역']) if is_hangul(ch)})
    need += [c for c in '()' if any(c in r['번역'] for r in rows)]
    if len(need) > len(SLOT_POOL):
        raise SystemExit('⛔한글 음절+괄호 %d > 칸 %d' % (len(need), len(SLOT_POOL)))
    return dict(zip(need, SLOT_POOL))


def kr_to_codes(s, kmap, rev):
    s = squeeze(s)
    out = []; i = 0
    while i < len(s):
        ch = s[i]
        if ch == '{':
            j = s.index('}', i); tok = s[i + 1:j]
            out += E.parse_token(tok); i = j + 1; continue
        if ch == ' ':
            out.append(32)
        elif ch in kmap:
            out.append(kmap[ch] + D.FIRST)
        else:
            ch2 = PUNCT.get(ch, ch)
            g = rev.get(ch2)
            if g is not None and (g in KEEP or g in PROT):
                out.append(g + D.FIRST)
            else:
                raise SystemExit('⛔글꼴에 없는 글자 %r in %r' % (ch, s))      # 인코딩 누락 = 빌드 에러
        i += 1
    return out


def serialize_split(shapes):
    """트리 → (첫 토막 bytes[표 기준 0‥], 둘째 토막 bytes, {prev: 코드표}).  트리 하나는 한 토막 안에만."""
    head = 2 * NCTX + 2
    segs = [(head, TREE_END_OLD), (SEG2[0] - D.TREE, SEG2[1] - D.TREE)]
    buf = {0: ['0'] * (TREE_END_OLD * 8), 1: ['0'] * ((segs[1][1] - segs[1][0]) * 8)}
    offs = [0] * NCTX; codes = {}
    si = 0; cur = head * 8                       # 표 기준 비트 커서
    for prev in sorted(shapes):
        shape = shapes[prev]; leaves = []; tbits = []

        def rec(n):
            if n[0] == 'L':
                tbits.append('1'); leaves.append(n[1])
            else:
                tbits.append('0'); rec(n[1]); rec(n[2])
        rec(shape)
        leafbits = ''.join(format(s, '010b') for s in reversed(leaves))
        while True:
            startbit = cur + len(leafbits); startbit += -startbit % 8
            if startbit + len(tbits) <= segs[si][1] * 8:
                break
            if si == 1:
                raise SystemExit('⛔트리 두 토막 모두 넘침')
            si = 1; cur = segs[1][0] * 8
        base = 0 if si == 0 else segs[1][0] * 8
        b = buf[si]
        for k, x in enumerate(leafbits):
            b[startbit - len(leafbits) + k - base] = x
        for k, x in enumerate(tbits):
            b[startbit + k - base] = x
        cur = startbit + len(tbits)
        assert prev < NCTX
        offs[prev] = startbit // 8; codes[prev] = D.shape_codes(shape)
    used = (cur - (segs[si][0] * 8 if si else 0) + 7) // 8
    body0 = D.pack_bits(''.join(buf[0]))
    body1 = D.pack_bits(''.join(buf[1]))
    table = struct.pack('>%dH' % NCTX, *offs) + struct.pack('>H', TERM)
    seg0 = table + body0[head:]
    print('③ 트리: 첫 토막 %d B / %d, 둘째 토막 %s' % (len(seg0) if si == 0 else TREE_END_OLD, TREE_END_OLD,
          ('%d B / %d' % (used, segs[1][1] - segs[1][0])) if si else '안 씀'))
    return seg0, body1, codes


def build():
    P0 = disc.local('D_SAVIOR/PROGRAM.004')
    P = bytearray(P0)
    cmap = D.charmap(); rev = {v: k for k, v in cmap.items()}
    rows = load_rows()
    if any(not r['번역'].strip() for r in rows):
        raise SystemExit('⛔번역 빈칸 %d줄' % sum(1 for r in rows if not r['번역'].strip()))
    kmap = assign_slots(rows)
    codes = {r['ID']: kr_to_codes(r['번역'], kmap, rev) for r in rows}
    print('번역 %d줄 · 한글+괄호 %d → 칸 %d개 중 · 글리프 %d · 끝 코드 %d' % (len(rows), len(kmap), len(SLOT_POOL), NGLYPH, TERM))
    # ① 글꼴 A 재배치
    dA = D.font_desc(P0, 'A')
    bm_len = (NGLYPH * 143 + 7) // 8
    assert FONT_START + bm_len + NGLYPH <= FONT_END, '글꼴 자리 넘침'
    P[FONT_START:FONT_END] = bytes(FONT_END - FONT_START)
    oA = D.FONT_DESC['A']
    struct.pack_into('>II', P, oA + 8, D.BASE004 + FONT_START, D.BASE004 + FONT_START + bm_len)
    P[D.FONT_DESC['B']:D.FONT_DESC['B'] + 20] = P[oA:oA + 20]          # 작은 창도 글꼴 A
    for g in KEEP + sorted(PROT):
        rows_ = D.read_glyph(P0, g, 'A').tolist()
        D.write_glyph(P, g, rows_, 'A', width=P0[dA['widths'] + g])
    for ch, g in kmap.items():
        bm = bdf.bitmap(FONT, ch, 11, 13, top=1)
        assert bm is not None, ch
        rows_ = [[(v >> (10 - x)) & 1 for x in range(11)] for v in bm]
        D.write_glyph(P, g, rows_, 'A', width=11 if is_hangul(ch) else ink_width(rows_))
    print('① 글꼴 A %d칸 → 0x%X‥0x%X (비트맵 %d B + 폭 %d B / %d)' % (NGLYPH, FONT_START, FONT_START + bm_len + NGLYPH, bm_len, NGLYPH, FONT_END - FONT_START))
    # ② 시스템 문장
    blob = bytearray()
    for i in range(E.SYS_COUNT):
        c = codes['sys:%04d' % i]
        bits = ''.join(format(x, '010b') for x in c)
        b = D.pack_bits(bits)
        assert len(b) * 8 // 10 == len(c), ('10비트 레코드 길이로 글자 수가 안 맞는다', i)
        assert len(b) <= 255
        blob += bytes([len(b)]) + b
    room = SYS_END - D.SYS_TABLE
    assert len(blob) <= room, ('시스템 문장 구역 넘침', len(blob), room)
    P[D.SYS_TABLE:SYS_END] = bytes(blob) + bytes(room - len(blob))
    print('② 시스템 문장 %d B / %d' % (len(blob), room))
    # ②' 예/아니오 선택지 — 시스템 표 바로 뒤 0x28EB0 에 u16 글리프 코드(FFFF 끝)로 박혀 있다(はい·いいえ).
    #    가나 칸이 한글로 바뀌어 「거각/각각갈」로 찍혔다(2026-10-03 실기). 자리 그대로: [2코드+FFFF][3코드+FFFF]
    assert P0[CHOICE:CHOICE + 14] == struct.pack('>7H', 0x44, 0x2C, 0xFFFF, 0x2C, 0x2C, 0x2E, 0xFFFF), '선택지 자리 아님'
    c_yes = kr_to_codes(CHOICE_KR[0], kmap, rev); c_no = kr_to_codes(CHOICE_KR[1], kmap, rev)
    assert len(c_yes) <= 2 and len(c_no) <= 3
    struct.pack_into('>3H', P, CHOICE, *(c_yes + [0xFFFF] * (3 - len(c_yes))))
    struct.pack_into('>4H', P, CHOICE + 6, *(c_no + [0xFFFF] * (4 - len(c_no))))
    # ③ 트리(새 끝 코드)
    D.TERM = TERM
    dialog_ids = [k for k in codes if not k.startswith('sys:')]
    shapes = D.build_trees([codes[k] for k in dialog_ids])
    seg0, seg1, tcodes = serialize_split(shapes)
    P[D.TREE:D.TREE + TREE_END_OLD] = seg0 + bytes(TREE_END_OLD - len(seg0))
    P[SEG2[0]:SEG2[1]] = seg1
    term_ram = D.BASE004 + D.TREE + 2 * NCTX
    for lit in TERM_LITS:
        assert struct.unpack_from('>II', P0, lit) == (0x2BB4DA, D.BASE004 + D.TREE), ('끝 코드 리터럴 자리 아님', hex(lit))
        struct.pack_into('>I', P, lit, term_ram)
    print('③ 끝 코드 %d · 문맥 표 %d항목 · 변수 0x%X(리터럴 %d곳)' % (TERM, NCTX, term_ram, len(TERM_LITS)))
    # ⑤ 그림 글자: 메뉴 세로 탭(PROGRAM.004 LZSS 블록 0x2629C)
    P_, (tc, tr) = gfx.patch_tabs(bytes(P)); P[:] = P_
    print('⑤ 메뉴 탭 압축 %d B / %d' % (tc, tr))
    P_, olog = gfx.patch_options(bytes(P)); P[:] = P_
    print('⑤ 옵션 버튼 %d장 (압축 최소 여유 %d B)' % (len(olog), min(r - c for _, c, r, _ in olog)))
    files = {'D_SAVIOR/PROGRAM.004': bytes(P)}
    # ④ 대사 파일
    for fn, cnt in D.SCRIPTS.items():
        F = bytearray(disc.local('D_SAVIOR/PROGRAM.' + fn))
        base, blocks = D.script_table(F)
        D.TERM = 0x30A
        _, end = D.script_messages(P0, bytes(F), cnt)       # 원래 구역 끝 = 원본 트리·원본 끝 코드로
        D.TERM = TERM
        body = bytearray(); offs = []
        for n in range(cnt):
            if n % 256 == 0:
                offs.append(2 * len(blocks) + len(body))
            b = D.pack_bits(D.huff_encode(tcodes, codes['%s:%04d' % (fn, n)]))
            assert len(b) <= 255, ('대사 한 줄 255 B 초과', fn, n)
            body += bytes([len(b)]) + b
        new = struct.pack('>%dH' % len(offs), *offs) + bytes(body)
        room = end - base
        assert len(new) <= room, ('대사 구역 넘침', fn, len(new), room)
        F[base:end] = new + bytes(room - len(new))
        F2, clog = gfx.patch_captions(bytes(F))                # ⑥ 지역 자막(대사 뒤 자료 — 대사 구역과 겹치지 않음)
        assert F2[base:end] == bytes(F[base:end]), '자막 패치가 대사 구역을 건드렸다'
        files['D_SAVIOR/PROGRAM.' + fn] = F2
        for c in clog:
            print('⑥ %s 자막 %s %s  %d B / %d' % (fn, c[0], c[1], c[2], c[3]))
        print('④ %s 대사 %d B / %d' % (fn, len(new), room))
    # 검산: 게임 해독기 재현으로 전 문장 되읽기(새 끝 코드)
    P2 = files['D_SAVIOR/PROGRAM.004']
    D.TERM = TERM
    for fn, cnt in D.SCRIPTS.items():
        got = D.script_messages(P2, files['D_SAVIOR/PROGRAM.' + fn], cnt)[0]
        for n, _, c in got:
            assert c == codes['%s:%04d' % (fn, n)], ('되읽기 불일치', fn, n)
    assert struct.unpack_from('>H', P2, D.TREE + 2 * NCTX)[0] == TERM, '끝 코드 변수'
    for i, (_, c) in enumerate(D.sys_records(P2, count=E.SYS_COUNT)):
        assert c == codes['sys:%04d' % i], ('시스템 되읽기 불일치', i)
    d2 = D.font_desc(P2, 'A')
    assert D.glyph_count(P2, 'A') == NGLYPH, ('글리프 수', D.glyph_count(P2, 'A'))
    for g in KEEP + sorted(PROT):
        assert (D.read_glyph(P2, g, 'A') == D.read_glyph(P0, g, 'A')).all() and P2[d2['widths'] + g] == P0[dA['widths'] + g], ('남김 칸 그림 다름', g)
    # 변경 범위 검산
    allowed = [(D.FONT_DESC['A'] + 8, D.FONT_DESC['A'] + 16), (D.FONT_DESC['B'], D.FONT_DESC['B'] + 20), (FONT_START, FONT_END),
               (D.SYS_TABLE, SYS_END), (D.TREE, D.TREE + TREE_END_OLD), SEG2, (gfx.TAB_BLOCK, 0x27C98), (CHOICE, CHOICE + 14)]
    allowed += [(l, l + 4) for l in TERM_LITS]
    allowed += [(b, e) for b, _, _, e in olog]                         # 옵션 버튼 LZSS 블록(원래 길이 안)
    for i in range(len(P0)):
        if P0[i] != P2[i] and not any(a <= i < b for a, b in allowed):
            raise SystemExit('⛔허용 범위 밖 변경 PROGRAM.004 0x%X' % i)
    print('검산: 전 문장 되읽기 일치 · 남김 칸 그림 그대로 · 범위 밖 변경 0')
    # ⑦ PROGRAM.506 (타이틀·데이터 관리 — 자체 글꼴·문자열)
    import importlib, boot_kr; importlib.reload(boot_kr)
    f506 = disc.local('D_SAVIOR/PROGRAM.506')
    b506, ns, nt, room, blog = boot.build(f506, boot_kr.KR)
    for i in range(len(f506)):
        if f506[i] != b506[i] and not (boot.FONT <= i < boot.FONT + boot.NGLYPH * 128 or boot.WIDTHS <= i < boot.WIDTHS + boot.NGLYPH or boot.TABLE <= i < boot.TABLE_END):
            raise SystemExit('⛔허용 범위 밖 변경 PROGRAM.506 0x%X' % i)
    files['D_SAVIOR/PROGRAM.506'] = b506
    print('⑦ 506 한글 %d음절 · 문자열 표 %d B / %d' % (ns, nt, room))
    for l in blog:
        print('   ', l)
    # ⑧ PROGRAM.439 사운드 테스트(자체 글꼴·1바이트 문자열·포인터 표)
    import snd_kr; importlib.reload(snd_kr)
    f439 = disc.local('D_SAVIOR/PROGRAM.439')
    b439, ng, nb, room = snd.build(f439, snd_kr.KR)
    for i in range(len(f439)):
        if f439[i] != b439[i] and not (snd.FONT <= i < snd.FONT + snd.NG * 128 or snd.STR0 <= i < snd.STR1 or 0x300B0 <= i < 0x301F0):
            raise SystemExit('⛔허용 범위 밖 변경 PROGRAM.439 0x%X' % i)
    files['D_SAVIOR/PROGRAM.439'] = b439
    print('⑧ 439 사운드 테스트 글꼴 %d자 · 문자열 %d B / %d' % (ng, nb, room))
    return files


def write(files, install):
    os.makedirs(OUT, exist_ok=True)
    dst = os.path.join(OUT, TRACK1)
    shutil.copyfile(disc.TRACK1, dst)
    iso.patch_sub(dst, files)
    for nm in ('Dark Savior (Japan).cue', 'Dark Savior (Japan) (Track 2).bin'):
        t = os.path.join(OUT, nm)
        if not os.path.exists(t):
            shutil.copyfile(os.path.join(disc.SRC_DIR, nm), t)
    md5 = hashlib.md5(open(dst, 'rb').read()).hexdigest()
    print('트랙 1', dst, md5)
    if install:
        shutil.copyfile(dst, os.path.join(F_DIR, TRACK1)); print('F: 설치', F_DIR)


if __name__ == '__main__':
    a = sys.argv[1:]
    files = build()
    if '--write' in a or '--install' in a:
        write(files, '--install' in a)
