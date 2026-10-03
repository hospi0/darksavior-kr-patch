# -*- coding: utf-8 -*-
r"""번역문 기계적 정리 (2026-10-03, 사용자 결정 반영) — work/text/darksavior_*.tsv «번역» 열을 고친다

  python tools/normalize_ko.py            바뀔 곳 요약(쓰지 않음)
  python tools/normalize_ko.py --write    적용 + work/text/normalize_log.tsv

  ① 말줄임표 = 「…」 한 칸 (사용자 결정): 「・」 2개 이상 연속 → 3개마다 「…」(최소 1), 「‥」 → 「…」, 「...」 → 「…」
  ② 이름 뒤 조사 확정: {6:k}을(를)·이(가)·은(는)·과(와) … → sys 표 이름의 받침으로 하나만
     (보통 낱말 뒤에 붙은 경우도 그 앞 글자 받침으로)
  ③ 글꼴에 없는 문자: "…" → 「…」, ' → ’, ― → ー, 한자 덧붙임 「(刑囚)」 등 삭제
"""
import csv, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
PAIRS = [('을', '를'), ('이', '가'), ('은', '는'), ('과', '와'), ('으로', '로'), ('이라', '라'), ('이랑', '랑'),
         ('아', '야'), ('이여', '여')]
KANJI_GLOSS = re.compile(r'\([一-鿿]+\)')


def rd(p):
    with open(p, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='\\'))


def wr(p, rows):
    with open(p, 'w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), delimiter='\t',
                           quoting=csv.QUOTE_NONE, escapechar='\\', lineterminator='\n')
        w.writeheader(); w.writerows(rows)


def batchim(ch):
    """True=받침 있음, None=모름(한글 아님)."""
    if '가' <= ch <= '힣':
        return (ord(ch) - 0xAC00) % 28 != 0
    if ch.isdigit():
        return ch in '013678'                 # 영일삼육칠팔 = 받침
    if ch.upper() in 'LMNR':
        return True                            # 엘 엠 엔 알
    if ch.isalpha():
        return False
    return None


def last_hangul(s):
    for ch in reversed(s):
        b = batchim(ch)
        if b is not None:
            return b
    return None


def fix_ellipsis(t):
    t = t.replace('...', '…').replace('‥', '…')
    return re.sub(r'・{2,}', lambda m: '…' * max(1, round(len(m.group(0)) / 3)), t)


def fix_particles(t, names):
    def rep(m):
        before, a, b = m.group(1), m.group(2), m.group(3)
        if before.startswith('{6:'):
            nm = names.get(int(before[3:-1]), '')
            has = last_hangul(nm)
        else:
            has = batchim(before[-1])
        if has is None:
            return m.group(0)
        pair = next(p for p in PAIRS if {a, b} == set(p))
        if pair == ('으로', '로') and before and not before.startswith('{') and \
                '가' <= before[-1] <= '힣' and (ord(before[-1]) - 0xAC00) % 28 == 8:
            return before + '로'                # ㄹ 받침 + 로
        return before + (pair[0] if has else pair[1])
    alt = '|'.join(re.escape(x) for p in PAIRS for x in p)
    pat = re.compile(r'(\{6:\d+\}|[^\s{}()])(%s)\((%s)\)' % (alt, alt))
    return pat.sub(lambda m: rep(m) if {m.group(2), m.group(3)} in [set(p) for p in PAIRS] else m.group(0), t)


# ★{3:0}(아이템 이름) 뒤 「을(를)」은 그대로 둔다 — 괄호 「(」「)」 는 빌더가 글리프로 그려 넣는다


NAME_PART = re.compile(r'(\{6:(\d+)\})(이|가|을|를|은|는|과|와|으로|로)(?=[\s{}…・.,!?！？。、]|$)')


def fix_name_particles(t, names):
    """이름 삽입 {6:k} 뒤에 못박아 쓴 조사를 그 이름 받침에 맞춘다(번역자는 이름을 모르고 썼다)."""
    def rep(m):
        has = last_hangul(names.get(int(m.group(2)), ''))
        if has is None:
            return m.group(0)
        p = m.group(3)
        pair = next(x for x in PAIRS if p in x)
        nm = names.get(int(m.group(2)), '')
        if pair == ('으로', '로') and nm and '가' <= nm[-1] <= '힣' and (ord(nm[-1]) - 0xAC00) % 28 == 8:
            return m.group(1) + '로'
        return m.group(1) + (pair[0] if has else pair[1])
    return NAME_PART.sub(rep, t)


# ★이름 뒤 서술격 조사 — 번역자가 받침 없는 이름 기준으로 「{6:k}다」라 써서 「잭다」가 찍혔다(2026-10-03 실기).
#   받침 있는 이름이면 「이」를 넣는다: 다→이다, 야→이야, 라고→이라고, 예요→이에요, 지→이지, 나→이나, 와→과
COPULA = re.compile(r'(\{6:(\d+)\})(예요|다|야|라|지|나|와)')
COPULA_FIX = {'예요': '이에요', '와': '과'}


def fix_name_copula(t, names):
    def rep(m):
        if not last_hangul(names.get(int(m.group(2)), '')):
            return m.group(0)
        p = m.group(3)
        return m.group(1) + COPULA_FIX.get(p, '이' + p)
    return COPULA.sub(rep, t)


# ★이름 앞 띄어쓰기 — 원문 「なんか{6:3}が」처럼 일본어는 안 띄우니 번역도 「뭔가{6:3}이」로 붙었다(2026-10-03 실기 「뭔가비란이」).
#   한글 낱말 바로 뒤 {6:k} 에 공백을 넣는다. 예외: 「부{6:29}」(부소장) · 말 더듬기(「비{6:3}」= 비…비란, 앞 글자가 이름 첫 글자와 같거나 한 글자)
NAME_GLUE = re.compile(r'(?<![가-힣])([가-힣]+)(\{6:(\d+)\})')
NAME_GLUE_KEEP = {'부'}


def fix_name_space(t, names):
    def rep(m):
        w, code, nm = m.group(1), m.group(2), names.get(int(m.group(3)), '')
        if w in NAME_GLUE_KEEP or (len(w) == 1 and nm and w in (nm[0], '피')):
            return m.group(0)
        return w + ' ' + code
    t = NAME_GLUE.sub(rep, t)
    return t.replace('{6:4}{6:29}', '{6:4} {6:29}')          # 쿠르트리겐 소장(クルトリーゲン所長)


def fix_chars(t):
    t = KANJI_GLOSS.sub('', t)
    t = re.sub(r'"([^"]*)"', r'「\1」', t)
    return t.replace("'", '’').replace('―', 'ー')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    write = '--write' in sys.argv
    files = {p: rd(p) for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'darksavior_*.tsv')))}
    names = {}
    for rows in files.values():
        for r in rows:
            if r['ID'].startswith('sys:'):
                names[int(r['ID'][4:])] = r['번역'] or r['원문']
    log = []; stat = {'①': 0, '②': 0, '③': 0}
    for p, rows in files.items():
        for r in rows:
            k0 = r['번역']
            k1 = fix_ellipsis(k0); stat['①'] += k1 != k0
            k2 = fix_name_space(fix_name_copula(fix_name_particles(fix_particles(k1, names), names), names), names); stat['②'] += k2 != k1
            k3 = fix_chars(k2); stat['③'] += k3 != k2
            if k3 != k0:
                log.append((r['ID'], k0, k3)); r['번역'] = k3
    print('바뀌는 줄 %d — 말줄임 %d / 조사 %d / 문자 %d' % (len(log), stat['①'], stat['②'], stat['③']))
    left = [(i, b) for i, a, b in log if re.search(r'\((를|을|가|이|는|은|와|과)\)', b)]
    print('남은 「(조사)」 %d' % len(left), left[:5])
    for i, a, b in log[:6]:
        print('  %s\n    %s\n  → %s' % (i, a[:80], b[:80]))
    if not write:
        print('검사만 — 쓰지 않음 (--write)')
        return
    for p, rows in files.items():
        wr(p, rows)
    with open(os.path.join(ROOT, 'work', 'text', 'normalize_log.tsv'), 'w', encoding='utf-8') as fh:
        fh.write('ID\t전\t후\n')
        for i, a, b in log:
            fh.write('%s\t%s\t%s\n' % (i, a, b))
    print('적용 완료 → work/text/normalize_log.tsv')


if __name__ == '__main__':
    main()
