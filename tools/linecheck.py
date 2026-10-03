# -*- coding: utf-8 -*-
r"""대사 줄 길이 분포 — 원문 «벼랑»으로 상자 폭을 읽고, 번역 줄을 그 폭과 비교한다 (2026-10-03)

  python tools/linecheck.py [--usr]   --usr: my files\ds_ko 를 직접 본다(병합 전)
줄 = 제어 코드로 끊긴 화면 한 줄. {n} 줄바꿈, {2}{7}·{1} 등 페이지/창 넘김도 줄 경계로 본다.
글자 수 = 제어 코드를 뺀 문자 수(공백 포함). 이름 삽입 {6:k} 은 그 이름 길이(sys 표)로 센다.
"""
import collections, csv, glob, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
TOK = re.compile(r'(\{[^}]*\})')


def rd(p):
    with open(p, encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh, delimiter='\t', quoting=csv.QUOTE_NONE, escapechar='\\'))


def rows(usr):
    pat = os.path.join(ROOT, 'my files', 'ds_ko', '*.tsv') if usr else os.path.join(ROOT, 'work', 'text', 'darksavior_*.tsv')
    out = {}
    for p in sorted(glob.glob(pat)):
        for r in rd(p):
            out[r['ID']] = r
    return out


def lines_of(s, names):
    """제어 코드로 쪼갠 화면 줄 → [글자 수]."""
    out, cur = [], 0
    for part in TOK.split(s):
        if not part:
            continue
        if part.startswith('{'):
            t = part[1:-1]
            if t.startswith('6:'):                       # 이름 삽입
                cur += len(names.get(int(t[2:]), '??????'))
            elif t in ('n', '2', '7', '1') or t.startswith('2') or t.startswith('7'):
                out.append(cur); cur = 0
            continue
        cur += len(part)
    out.append(cur)
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    R = rows('--usr' in sys.argv)
    jp_names = {int(i[4:]): r['원문'] for i, r in R.items() if i.startswith('sys:')}
    kr_names = {int(i[4:]): (r['번역'] or r['원문']) for i, r in R.items() if i.startswith('sys:')}
    for grp in ('507', '508', '509', '517'):
        jp = collections.Counter(); kr = collections.Counter()
        for i, r in R.items():
            if not i.startswith(grp):
                continue
            for n in lines_of(r['원문'], jp_names):
                jp[n] += 1
            if r['번역'].strip():
                for n in lines_of(r['번역'], kr_names):
                    kr[n] += 1
        tot = sum(jp.values())
        print('== %s  원문 줄 %d' % (grp, tot))
        print('   원문  ' + ' '.join('%d:%d' % (k, jp[k]) for k in range(14, 31) if jp[k]))
        print('   번역  ' + ' '.join('%d:%d' % (k, kr[k]) for k in range(14, 40) if kr[k]))


if __name__ == '__main__':
    main()
