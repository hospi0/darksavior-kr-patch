# -*- coding: utf-8 -*-
r"""빌드 전 번역 전수 검사 (2026-10-03) — 받은 번역도 똑같이 태운다

  python tools/kocheck.py            요약 + 문제 줄 목록(work/text/kocheck.txt)

검사
  ① 문장부호 뒤 공백 1칸(빌더가 지운다 — 몇 곳인지만)
  ② 한 줄 칸 수 > LIMIT (창 폭: 스샷 실측 글자 시작 x22·11px 고정 간격·창 x5‥335 → 26칸, 원문 벼랑 26/27)
  ③ 한 페이지 줄 수 > 원문 최대
  ④ 글꼴로 못 쓰는 문자(빌드 에러가 될 것)
  ⑤ 한글 음절 수 ≤ 693칸
"""
import collections, csv, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import extract as E
TOK = re.compile(r'(\{[^}]*\})')
FIRST = 19                         # ★페이지 첫 줄 = 화자 이름+「 가 앞에 붙는다({7}, 실행 중 결정) — 이름 4글자까지 안전(독쿠루 507:0273 잘림)
LIMIT = 24                         # ★2026-10-03 실기: 화자 대사 둘째 줄부터 1칸 들여쓰기 → 한글 24칸(25칸째 「다」 잘림, 카이저 507:0053)
PUNCT = ",.!?:;)]}'\"~、。，．！？：；）］｝」』】〉》”’…‥・·～〜♪♥"
SQ = re.compile('([' + re.escape(PUNCT) + '])[ 　](?![ 　])')
PAGE = ('2', '7', '1')            # 페이지/창 넘김 계열(줄 수 세기 초기화)


def squeeze(t):
    return SQ.sub(r'\1', t)


def rd(p):
    with open(p, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='\\'))


def load():
    R = {}
    for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'darksavior_*.tsv'))):
        for r in rd(p):
            R[r['ID']] = r
    return R


def cells(s, jp):
    return sum(2 if (jp and ch in E.UNDAK) else 1 for ch in s)


def layout(s, names, jp):
    """→ [(칸 수, 페이지 안 줄 번호)] , 페이지별 줄 수 목록"""
    lines, pages = [], []
    cur, ln = 0, 1
    for part in TOK.split(s):
        if not part:
            continue
        if part.startswith('{'):
            t = part[1:-1]
            if t.startswith('6:'):
                cur += cells(names.get(int(t[2:]), ''), jp)
            elif t == 'n':
                lines.append(cur); cur = 0; ln += 1
            elif t in PAGE:
                lines.append(cur); cur = 0; pages.append(ln); ln = 1
            continue
        cur += cells(part, jp)
    lines.append(cur); pages.append(ln)
    return lines, pages


def page_firsts(s, names):
    """페이지마다 첫 줄 칸 수"""
    return [layout(p, names, False)[0][0] for p in re.split(r'\{2\}\{7\}|\{2\}|\{7\}|\{1\}', s) if p]


def over(s, names):
    s = squeeze(s)
    return max(layout(s, names, False)[0]) > LIMIT or max(page_firsts(s, names) or [0]) > FIRST


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    import disc, dsfmt as D
    cmap = D.charmap(); rev = {v: k for k, v in cmap.items()}
    R = load()
    jpn = {int(i[4:]): r['원문'] for i, r in R.items() if i.startswith('sys:')}
    krn = {int(i[4:]): squeeze(r['번역'] or r['원문']) for i, r in R.items() if i.startswith('sys:')}
    BPUNCT = {'!': '！', '?': '？', ',': '、', '.': '。', '~': 'ー', '-': 'ー', '…': '…', '·': '・'}
    rep = []
    nsq = 0; over = []; pg = []; badch = collections.Counter(); badex = {}
    maxpage = 0
    for i, r in R.items():
        if i.startswith('sys'):
            continue
        _, pj = layout(r['원문'], jpn, True)
        maxpage = max(maxpage, max(pj))
    for i, r in sorted(R.items()):
        k = r['번역']
        if not k.strip():
            continue
        nsq += len(SQ.findall(k))
        k = squeeze(k)
        for ch in TOK.sub('', k):
            if ch == ' ' or '가' <= ch <= '힣':
                continue
            c2 = BPUNCT.get(ch, ch)
            if c2 in E.UNDAK or (c2 in rev and rev[c2] < D.KANJI0):
                continue
            badch[ch] += 1; badex.setdefault(ch, i)
        if i.startswith('sys'):
            continue
        L, P = layout(k, krn, False)
        m = max(L)
        if m > LIMIT or max(page_firsts(k, krn) or [0]) > FIRST:
            over.append((m, i, k))
        _, pj = layout(r['원문'], jpn, True)
        if max(P) > max(pj) and max(P) > 4:
            pg.append((max(P), max(pj), i, k))
    syl = {ch for r in R.values() for ch in squeeze(r['번역']) if '가' <= ch <= '힣'}
    print('① 문장부호 뒤 공백 %d곳 (빌더가 지운다)' % nsq)
    print('② 한 줄 %d칸(페이지 첫 줄 19) 초과 %d줄 (27칸 %d / 28+ %d)' % (LIMIT, len(over), sum(1 for o in over if o[0] == 27),
                                                 sum(1 for o in over if o[0] >= 28)))
    print('③ 한 페이지 줄 수가 원문보다 많고 5줄 이상 %d건 (원문 최대 %d줄)' % (len(pg), maxpage))
    print('④ 글꼴에 없는 문자 %s' % ', '.join('%r×%d(%s)' % (c, n, badex[c]) for c, n in badch.most_common()))
    print('⑤ 한글 음절 %d / 693' % len(syl))
    out = os.path.join(ROOT, 'work', 'text', 'kocheck.txt')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write('## 26칸 초과\n')
        for m, i, k in sorted(over, reverse=True):
            fh.write('%d\t%s\t%s\n' % (m, i, k))
        fh.write('\n## 페이지 줄 수\n')
        for a, b, i, k in pg:
            fh.write('%d>%d\t%s\t%s\n' % (a, b, i, k))
    print('→', out)


if __name__ == '__main__':
    main()
