# -*- coding: utf-8 -*-
r"""이름·용어 표기 통일 (2026-10-03) — work/text/darksavior_*.tsv «번역» 열(sys 포함)

  python tools/unify_terms.py [--write]
기준: sys 표기 > 대사 다수결 > 가나에 충실한 쪽. 갈림 찾기는 tools/terms.py.
"""
import glob, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import normalize_ko as N

GLOSS = [                     # (틀린 표기, 통일 표기, 원문)
    ('빌라니움', '비라니움', 'ビラニウム'),
    ('비라늄', '비라니움', 'ビラニウム'),
    ('빌라노', '비라노', 'ビラーノ'),
    ('제일러즈', '제이라즈', 'ジェイラーズ'),
    ('자크', '잭', 'ジャク'),
    ('단크', '덩크', 'ダンク'),
    ('빌런', '비란', 'ビラン'),
    ('어린이', '아이', 'こども'),
    ('제이라즈섬', '제이라즈 섬', 'ジェイラーズ島'),     # sys 「제이라즈 항」 과 같은 띄어쓰기
]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    write = '--write' in sys.argv
    files = {p: N.rd(p) for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'darksavior_*.tsv')))}
    n = {}
    for rows in files.values():
        for r in rows:
            for a, b, _ in GLOSS:
                if a in r['번역']:
                    n[a] = n.get(a, 0) + r['번역'].count(a)
                    r['번역'] = r['번역'].replace(a, b)
    for a, b, jp in GLOSS:
        print('%s(%s) → %s : %d곳' % (a, jp, b, n.get(a, 0)))
    if write:
        for p, rows in files.items():
            N.wr(p, rows)
        print('적용 완료')


if __name__ == '__main__':
    main()
