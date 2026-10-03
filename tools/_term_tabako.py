# -*- coding: utf-8 -*-
"""2026-10-03 사용자: 시가렛 → 담배 통일(아이템 이름 sys:0081 = 담배). 받침이 없어지니 조사도 맞춘다."""
import glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import normalize_ko as N
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PART = {'은': '는', '을': '를', '이': '가', '과': '와', '으로': '로', '이라': '라', '이야': '야', '이다': '다'}
pat = re.compile(r'시가렛(으로|이라|이야|이다|은|을|이|과)?')
n = 0
for p in sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'darksavior_*.tsv'))):
    rows = N.rd(p); ch = False
    for r in rows:
        k = pat.sub(lambda m: '담배' + PART.get(m.group(1) or '', m.group(1) or ''), r['번역'])
        if k != r['번역']:
            r['번역'] = k; ch = True; n += 1
    if ch:
        N.wr(p, rows)
print('바뀐 줄', n)
