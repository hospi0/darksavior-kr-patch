# -*- coding: utf-8 -*-
r"""원문 추출 → work/text/darksavior_*.tsv (2026-10-03)
  열: ID · 원문 · 번역 · 비고     ID = 507:0012 (대사 파일:문장번호) / sys:0003 (PROGRAM.004 시스템 문장)
  원문 표기(가역 — text_to_codes 로 코드열 그대로 복원):
    탁점·반탁점은 합친 글자(ジ = ゛シ), 코드 32 = 반각 공백 ' ', 코드 0 = {n}(줄바꿈), 그 밖 제어 = {숫자}
    ★인수 먹는 제어(3·4·5·6·8·9·19·20 — 글자 출력 0x294324 가 창+0x54 에 대기시키고 다음 코드를 인수로 씀)는 {코드:인수} 한 덩어리
      예) {6:12} = 시스템 문장 12번 이름(ジャク) 삽입, {3:0} = 문자열 변수 0, {9:2} = 숫자 변수 2
    글리프 칸 162‥744 = work/text/glyphs.tsv 판독 글자
  python tools/extract.py           → TSV 쓰기 + 왕복 검사
"""
import csv, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import dsfmt as D, disc

SYS_COUNT = 228                  # PROGRAM.004 0x2838C‥0x28EAF (그 뒤는 다른 자료)
TEXT = os.path.join(ROOT, 'work', 'text')
DAK = {'゛': dict(zip('かきくけこさしすせそたちつてとはひふへほカキクケコサシスセソタチツテトハヒフヘホウ',
                     'がぎぐげござじずぜぞだぢづでどばびぶべぼガギグゲゴザジズゼゾダヂヅデドバビブベボヴ')),
       '゜': dict(zip('はひふへほハヒフヘホ', 'ぱぴぷぺぽパピプペポ'))}
UNDAK = {v: (m, k) for m, t in DAK.items() for k, v in t.items()}
ARGC = {3, 4, 5, 6, 8, 9, 19, 20}


def codes_to_text(codes, cmap):
    out = []; i = 0
    while i < len(codes):
        c = codes[i]; g = c - D.FIRST
        if c in ARGC and i + 1 < len(codes):
            out.append('{%d:%d}' % (c, codes[i + 1])); i += 2; continue
        if c == 0:
            out.append('{n}')
        elif c == 32:
            out.append(' ')
        elif c < D.FIRST or g >= 745:
            out.append('{%d}' % c)
        else:
            ch = cmap[g]
            if ch in DAK and i + 1 < len(codes) and codes[i + 1] - D.FIRST in cmap \
                    and cmap[codes[i + 1] - D.FIRST] in DAK[ch]:
                out.append(DAK[ch][cmap[codes[i + 1] - D.FIRST]]); i += 2; continue
            out.append(ch)
        i += 1
    return ''.join(out)


def parse_token(tok):
    if tok == 'n':
        return [0]
    if ':' in tok:
        a, b = tok.split(':'); a = int(a)
        assert a in ARGC, ('인수 없는 코드에 인수', tok)
        return [a, int(b)]
    assert int(tok) not in ARGC, ('인수 먹는 코드인데 인수가 없다', tok)
    return [int(tok)]


def text_to_codes(s, rev):
    """원문 표기 → 코드열 (rev = 글자 → 글리프 번호)"""
    out = []; i = 0
    while i < len(s):
        if s[i] == '{':
            j = s.index('}', i); tok = s[i + 1:j]
            out += parse_token(tok); i = j + 1; continue
        ch = s[i]
        if ch == ' ':
            out.append(32)
        elif ch in UNDAK:
            m, base = UNDAK[ch]; out += [rev[m] + D.FIRST, rev[base] + D.FIRST]
        else:
            out.append(rev[ch] + D.FIRST)
        i += 1
    return out


def all_messages():
    """[(ID, 코드열)]"""
    P = disc.local('D_SAVIOR/PROGRAM.004'); out = []
    for i, (_, c) in enumerate(D.sys_records(P, count=SYS_COUNT)):
        out.append(('sys:%04d' % i, c))
    for fn, cnt in D.SCRIPTS.items():
        F = disc.local('D_SAVIOR/PROGRAM.' + fn)
        out += [('%s:%04d' % (fn, n), c) for n, _, c in D.script_messages(P, F, cnt)[0]]
    return out


def main():
    cmap = D.charmap(); rev = {v: k for k, v in cmap.items()}
    assert len(rev) == len(cmap), '판독표에 같은 글자가 두 칸 — 되돌리기가 모호하다'
    msgs = all_messages(); bad = 0
    groups = {'sys': [], '507': [], '508': [], '509': [], '517': []}
    for mid, c in msgs:
        t = codes_to_text(c, cmap)
        if text_to_codes(t, rev) != list(c):
            bad += 1; print('⛔왕복 불일치', mid, t)
        groups[mid.split(':')[0]].append((mid, t))
    for k, rows in groups.items():
        with open(os.path.join(TEXT, 'darksavior_%s.tsv' % k), 'w', encoding='utf-8', newline='') as o:
            w = csv.writer(o, delimiter='\t', lineterminator='\n', quoting=csv.QUOTE_NONE, escapechar='\\')
            w.writerow(['ID', '원문', '번역', '비고'])
            for mid, t in rows:
                w.writerow([mid, t, '', ''])
    n = sum(len(v) for v in groups.values())
    chars = sum(len(re.sub(r'\{[^}]*\}', '', t)) for v in groups.values() for _, t in v)
    print('문장 %d (sys %d · 대사 %d) · 글자 %d · 왕복 불일치 %d' % (n, len(groups['sys']), n - len(groups['sys']), chars, bad))


if __name__ == '__main__':
    main()
